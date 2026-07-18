/**
 * HOOKCUT-Analyse-Dialog (Etappe 3 des Umbaus).
 *
 * Der "Zauber"-Flow von HOOKCUT im Editor: Performance-Video + Song aus der
 * Media-Library waehlen -> die lokale Python-Analyse (Port 8000) berechnet
 * Sync-Versatz + Hook-Fenster -> ein Klick legt beides fertig synchronisiert
 * und auf den Hook getrimmt auf zwei frische Spuren (Video stumm, Song an).
 *
 * Die Analyse liefert NUR Zahlen - Schnitt, Vorschau und Export macht der
 * Editor selbst. Deutsche Strings bewusst hartkodiert (i18n-Ausbau ueber die
 * 9 Sprachen ist als TODO in HOOKCUT-FORK.md notiert).
 */
import { useMemo, useState } from 'react'
import { Loader2, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { createLogger } from '@/shared/logging/logger'
import type { MediaMetadata } from '@/types/storage'
import type { AudioItem, TimelineItem, VideoItem } from '@/types/timeline'
import {
  importMediaLibraryService,
  resolveMediaUrl,
  useMediaLibraryStore,
} from '../deps/media-library-contract'
import {
  addItems,
  buildMediaTimelineItems,
  createClassicTrack,
  useItemsStore,
  useTimelineSettingsStore,
} from '../deps/timeline-contract'

const log = createLogger('HookcutDialog')

/** Lokale HOOKCUT-Analyse (FastAPI). Muss laufen: start-editor.bat startet sie mit. */
const HOOKCUT_API_BASE = 'http://127.0.0.1:8000'

/** Ragt ein Hook-Kandidat maximal so viele Sekunden uebers Video hinaus,
 * wird er ans Video-Ende "geclampt" statt verworfen (Realfall: Top-Hook
 * endete 0,46s nach Video-Ende). */
const CLAMP_TOLERANCE_SEC = 1.0

interface HookCandidate {
  start_sec: number
  end_sec: number
  viral_score: number
}

interface AnalysisResult {
  offset_ms: number
  confidence: number
  video_duration_sec: number
  song_duration_sec: number
  hook: { best: HookCandidate; alternatives: HookCandidate[] }
}

type Phase = 'form' | 'running' | 'result' | 'applied' | 'error'

interface HookcutDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Projekt-Metadaten aus der Toolbar (Canvas-Maße + FPS-Fallback). */
  project: { width: number; height: number; fps: number }
}

/** Waehlt den Hook: erster Kandidat, der (mit Clamp-Toleranz) ins Video passt. */
export function chooseHookWindow(
  result: AnalysisResult,
): { startSec: number; endSec: number; clamped: boolean; viralScore: number } | null {
  const offsetSec = result.offset_ms / 1000
  for (const c of [result.hook.best, ...result.hook.alternatives]) {
    const videoStart = c.start_sec - offsetSec
    const videoEnd = c.end_sec - offsetSec
    if (videoStart < 0) continue
    if (videoEnd <= result.video_duration_sec) {
      return { startSec: c.start_sec, endSec: c.end_sec, clamped: false, viralScore: c.viral_score }
    }
    if (videoEnd - result.video_duration_sec <= CLAMP_TOLERANCE_SEC) {
      const clampedEnd = c.end_sec - (videoEnd - result.video_duration_sec)
      if (clampedEnd > c.start_sec + 3) {
        return { startSec: c.start_sec, endSec: clampedEnd, clamped: true, viralScore: c.viral_score }
      }
    }
  }
  return null
}

async function pollAnalysis(jobId: string): Promise<AnalysisResult> {
  const started = Date.now()
  for (;;) {
    const res = await fetch(`${HOOKCUT_API_BASE}/editor/analyze/${jobId}`)
    if (!res.ok) throw new Error(`Analyse-Status ${res.status}`)
    const body = (await res.json()) as {
      status: string
      error: string | null
      result: AnalysisResult | null
    }
    if (body.status === 'done' && body.result) return body.result
    if (body.status === 'error') throw new Error(body.error ?? 'Analyse fehlgeschlagen.')
    if (Date.now() - started > 10 * 60 * 1000) throw new Error('Zeitueberschreitung bei der Analyse.')
    await new Promise((r) => setTimeout(r, 2000))
  }
}

export function HookcutDialog({ open, onOpenChange, project }: HookcutDialogProps) {
  const mediaItems = useMediaLibraryStore((s) => s.mediaItems)
  const [videoId, setVideoId] = useState<string>('')
  const [songId, setSongId] = useState<string>('')
  const [phase, setPhase] = useState<Phase>('form')
  const [statusText, setStatusText] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [applyNote, setApplyNote] = useState('')

  const videoChoices = useMemo(
    () => mediaItems.filter((m) => m.mimeType?.startsWith('video/')),
    [mediaItems],
  )
  // Songs kommen oft als Screen-Recording-Video daher -> beides anbieten.
  const songChoices = useMemo(
    () =>
      mediaItems.filter(
        (m) => m.mimeType?.startsWith('audio/') || m.mimeType?.startsWith('video/'),
      ),
    [mediaItems],
  )

  function resetAndClose(next: boolean) {
    if (!next) {
      setPhase('form')
      setErrorMsg('')
      setAnalysis(null)
      setApplyNote('')
    }
    onOpenChange(next)
  }

  async function runAnalysis() {
    const videoMedia = mediaItems.find((m) => m.id === videoId)
    const songMedia = mediaItems.find((m) => m.id === songId)
    if (!videoMedia || !songMedia) return
    setPhase('running')
    setErrorMsg('')
    try {
      setStatusText('Dateien werden an die Analyse uebergeben…')
      const { mediaLibraryService } = await importMediaLibraryService()
      const [videoBlob, songBlob] = await Promise.all([
        mediaLibraryService.getMediaFile(videoMedia),
        mediaLibraryService.getMediaFile(songMedia),
      ])
      if (!videoBlob || !songBlob) {
        throw new Error(
          'Dateizugriff fehlgeschlagen - bitte Berechtigung fuer die Mediendateien erneut erteilen.',
        )
      }

      const form = new FormData()
      form.append('video', videoBlob, videoMedia.fileName)
      form.append('song', songBlob, songMedia.fileName)
      const res = await fetch(`${HOOKCUT_API_BASE}/editor/analyze`, {
        method: 'POST',
        body: form,
      })
      if (!res.ok) throw new Error(`Analyse-Start fehlgeschlagen (${res.status}).`)
      const { job_id } = (await res.json()) as { job_id: string }

      setStatusText('Ton wird synchronisiert & Hook gesucht…')
      const result = await pollAnalysis(job_id)
      setAnalysis(result)
      setPhase('result')
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setErrorMsg(
        msg === 'Failed to fetch'
          ? 'HOOKCUT-Analyse nicht erreichbar. Laeuft das Fenster "HOOKCUT Analyse" (start-editor.bat)?'
          : msg,
      )
      setPhase('error')
    }
  }

  async function applyToTimeline() {
    const videoMedia = mediaItems.find((m) => m.id === videoId)
    const songMedia = mediaItems.find((m) => m.id === songId)
    if (!videoMedia || !songMedia || !analysis) return
    try {
      const projectFps = useTimelineSettingsStore.getState().fps || project.fps || 30
      const chosen = chooseHookWindow(analysis)
      const offsetSec = analysis.offset_ms / 1000

      // Fenster im Song: gewaehlter Hook, sonst der komplette im Video
      // gefilmte Bereich (synchron, ohne Hook-Trim).
      const windowStart = chosen ? chosen.startSec : Math.max(0, offsetSec)
      const windowEnd = chosen
        ? chosen.endSec
        : Math.min(analysis.song_duration_sec, offsetSec + analysis.video_duration_sec)
      const windowLenSec = windowEnd - windowStart
      if (windowLenSec <= 0.5) {
        throw new Error('Analyse ergab kein nutzbares Zeitfenster.')
      }
      const durationInFrames = Math.max(1, Math.round(windowLenSec * projectFps))

      const [videoUrl, songUrl] = await Promise.all([
        resolveMediaUrl(videoMedia.id),
        resolveMediaUrl(songMedia.id),
      ])

      const itemsStore = useItemsStore.getState()
      const canvasWidth = project.width || 1080
      const canvasHeight = project.height || 1920

      // Zwei frische Spuren oben drauf (kollisionsfrei): V fuer das stumme
      // Video, A fuer den Song.
      const minOrder = itemsStore.tracks.reduce((min, t) => Math.min(min, t.order), 0)
      const videoTrack = createClassicTrack({
        tracks: itemsStore.tracks,
        kind: 'video',
        order: minOrder - 2,
      })
      const audioTrack = createClassicTrack({
        tracks: [...itemsStore.tracks, videoTrack],
        kind: 'audio',
        order: minOrder - 1,
      })

      // sourceStart/End sind in QUELL-FPS-Frames (siehe CLAUDE.md-Gotcha).
      const videoFps = videoMedia.fps || projectFps
      const videoStartSec = Math.max(0, windowStart - offsetSec)
      const videoItems = buildMediaTimelineItems({
        media: videoMedia,
        mediaId: videoMedia.id,
        mediaType: 'video',
        label: videoMedia.fileName,
        projectFps,
        blobUrl: videoUrl,
        canvasWidth,
        canvasHeight,
        placements: {
          primary: { trackId: videoTrack.id, from: 0, durationInFrames },
        },
        sourceStart: Math.round(videoStartSec * videoFps),
        sourceEnd: Math.round((videoStartSec + windowLenSec) * videoFps),
      })

      const songFps = songMedia.fps || projectFps
      const songItems = buildMediaTimelineItems({
        media: songMedia,
        mediaId: songMedia.id,
        mediaType: 'audio',
        label: songMedia.fileName,
        projectFps,
        blobUrl: songUrl,
        canvasWidth,
        canvasHeight,
        placements: {
          primary: { trackId: audioTrack.id, from: 0, durationInFrames },
        },
        sourceStart: Math.round(windowStart * songFps),
        sourceEnd: Math.round((windowStart + windowLenSec) * songFps),
      })

      const mutedVideoItems = videoItems.map((item) =>
        item.type === 'video'
          ? ({ ...item, volume: -60, embeddedAudioMuted: true } as VideoItem)
          : item,
      )
      const finalItems: TimelineItem[] = [
        ...mutedVideoItems,
        ...(songItems as AudioItem[]),
      ]

      itemsStore.setTracks([...itemsStore.tracks, videoTrack, audioTrack])
      addItems(finalItems)

      setApplyNote(
        chosen
          ? chosen.clamped
            ? `Hook uebernommen (leicht ans Video-Ende angepasst) - Viral-Score ${Math.round(chosen.viralScore)}/100.`
            : `Hook uebernommen - Viral-Score ${Math.round(chosen.viralScore)}/100.`
          : 'Kein Hook-Fenster lag komplett im gefilmten Material - ganzes Video synchron uebernommen.',
      )
      setPhase('applied')
    } catch (e) {
      log.error('Timeline-Uebernahme fehlgeschlagen', e)
      setErrorMsg(e instanceof Error ? e.message : String(e))
      setPhase('error')
    }
  }

  const confidencePct = analysis ? Math.round(analysis.confidence * 100) : 0
  const chosenPreview = analysis ? chooseHookWindow(analysis) : null

  return (
    <Dialog open={open} onOpenChange={resetAndClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            HOOKCUT Auto-Sync
          </DialogTitle>
          <DialogDescription>
            Performance-Video + Song waehlen. HOOKCUT legt den Song automatisch
            lippensynchron unter dein Video und schneidet auf die beste Hook-Stelle zu.
          </DialogDescription>
        </DialogHeader>

        {phase === 'form' && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <span className="text-sm text-muted-foreground">Performance-Video</span>
              <Select value={videoId} onValueChange={setVideoId}>
                <SelectTrigger>
                  <SelectValue placeholder="Video aus der Media-Library waehlen…" />
                </SelectTrigger>
                <SelectContent>
                  {videoChoices.map((m: MediaMetadata) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.fileName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <span className="text-sm text-muted-foreground">Song (Audio oder Screen-Recording)</span>
              <Select value={songId} onValueChange={setSongId}>
                <SelectTrigger>
                  <SelectValue placeholder="Song aus der Media-Library waehlen…" />
                </SelectTrigger>
                <SelectContent>
                  {songChoices.map((m: MediaMetadata) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.fileName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {mediaItems.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Importiere zuerst dein Video und deinen Song in die Media-Library.
              </p>
            )}
            <Button
              className="w-full"
              disabled={!videoId || !songId || videoId === songId}
              onClick={runAnalysis}
            >
              Analysieren
            </Button>
          </div>
        )}

        {phase === 'running' && (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm">{statusText}</p>
            <p className="text-xs text-muted-foreground">Dauert je nach Songlaenge ~10-60 Sekunden.</p>
          </div>
        )}

        {phase === 'result' && analysis && (
          <div className="space-y-4">
            <div className="rounded-md border border-border p-3 text-sm space-y-1">
              <p>
                Sync-Versatz: <span className="font-medium">{Math.round(analysis.offset_ms)} ms</span>{' '}
                <span className="text-muted-foreground">(Konfidenz {confidencePct}%)</span>
              </p>
              {chosenPreview ? (
                <p>
                  Hook: {chosenPreview.startSec.toFixed(1)}s – {chosenPreview.endSec.toFixed(1)}s
                  {' '}· Viral-Score{' '}
                  <span className="font-medium">{Math.round(chosenPreview.viralScore)}/100</span>
                  {chosenPreview.clamped && (
                    <span className="text-muted-foreground"> (ans Video-Ende angepasst)</span>
                  )}
                </p>
              ) : (
                <p className="text-muted-foreground">
                  Kein Hook-Fenster liegt komplett im gefilmten Material – es wird das ganze
                  Video synchron uebernommen.
                </p>
              )}
            </div>
            <Button className="w-full" onClick={applyToTimeline}>
              In Timeline uebernehmen
            </Button>
          </div>
        )}

        {phase === 'applied' && (
          <div className="space-y-4">
            <p className="text-sm">
              Fertig! Video (stumm) + Song liegen synchron auf zwei neuen Spuren.{' '}
              <span className="text-muted-foreground">{applyNote}</span>
            </p>
            <Button className="w-full" onClick={() => resetAndClose(false)}>
              Schliessen
            </Button>
          </div>
        )}

        {phase === 'error' && (
          <div className="space-y-4">
            <p className="text-sm text-destructive break-words">{errorMsg}</p>
            <Button variant="outline" className="w-full" onClick={() => setPhase('form')}>
              Nochmal versuchen
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
