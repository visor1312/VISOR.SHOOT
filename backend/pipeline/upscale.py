"""Schritt 09 (Phase 3, optional): Real-ESRGAN-Upscaling.

Nutzt die PyTorch-Referenzimplementierung (PyPI-Pakete `realesrgan`/`basicsr`)
statt eines ncnn-Vulkan-Builds, damit es auf jeder Maschine laeuft (mit oder
ohne dedizierte GPU) - reine pip-Installation, kein plattformspezifischer
Vulkan-Binary-Download noetig. Nutzt automatisch CUDA, falls verfuegbar,
sonst CPU.

WICHTIG (siehe README): Auf reiner CPU-Rechenleistung ist das SEHR langsam
(pro Frame ggf. mehrere Sekunden bis in den zweistelligen Sekundenbereich,
je nach Aufloesung/Hardware) - bei einem 20-30-Sekunden-Clip mit 30fps
koennen das leicht mehrere zehn Minuten bis Stunden werden, nicht nur "ein
paar Minuten". Erfindet keine neuen Bilddetails, sondern skaliert nur
glaetter hoch als einfache Interpolation.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Callable, Optional

MODEL_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
MODEL_NAME = "RealESRGAN_x4plus"
NATIVE_MODEL_SCALE = 4


def _patch_torchvision_compat() -> None:
    """basicsr<=1.4.2 importiert `torchvision.transforms.functional_tensor`,
    das in neueren torchvision-Versionen entfernt wurde (die Funktion liegt
    jetzt in `functional`). Bekannter Kompatibilitaetsbruch - wird hier per
    Shim-Modul behoben, ohne das installierte Package zu patchen."""
    if "torchvision.transforms.functional_tensor" in sys.modules:
        return
    import torchvision.transforms.functional as F

    shim = types.ModuleType("torchvision.transforms.functional_tensor")
    shim.rgb_to_grayscale = F.rgb_to_grayscale
    sys.modules["torchvision.transforms.functional_tensor"] = shim


def _get_upsampler(tile: int = 0):
    _patch_torchvision_compat()
    import torch
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    device_is_cuda = torch.cuda.is_available()
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=NATIVE_MODEL_SCALE)
    return RealESRGANer(
        scale=NATIVE_MODEL_SCALE,
        model_path=MODEL_URL,
        model=model,
        tile=tile,
        tile_pad=10,
        pre_pad=0,
        half=device_is_cuda,  # half precision nur sinnvoll/unterstuetzt auf CUDA
    )


def _probe_fps(video_path: str | Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        check=True, capture_output=True, text=True,
    )
    num, den = result.stdout.strip().split("/")
    return float(num) / float(den)


def upscale_video(
    video_path: str | Path,
    out_path: str | Path,
    scale: int = 2,
    tile: int = 0,
    crf: int = 18,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Skaliert ein Video mit Real-ESRGAN hoch (Bild fuer Bild) und fuegt den
    Original-Ton wieder hinzu. `scale` ist die gewuenschte Ausgabe-Vergroesserung
    (z.B. 2 fuer 2x) - das Netz selbst arbeitet intern mit 4x und wird bei
    Bedarf auf `scale` heruntergerechnet (Standardverhalten von RealESRGANer)."""
    import cv2

    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fps = _probe_fps(video_path)
    upsampler = _get_upsampler(tile=tile)

    with tempfile.TemporaryDirectory(prefix="upscale_") as tmp:
        tmp_path = Path(tmp)
        frames_in = tmp_path / "in"
        frames_out = tmp_path / "out"
        frames_in.mkdir()
        frames_out.mkdir()

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-vsync", "0", str(frames_in / "frame_%06d.png")],
            check=True, capture_output=True, text=True,
        )

        frame_files = sorted(frames_in.glob("frame_*.png"))
        total = len(frame_files)
        if total == 0:
            raise ValueError("Keine Frames extrahiert - ist die Videodatei gueltig?")

        for i, frame_file in enumerate(frame_files):
            img = cv2.imread(str(frame_file), cv2.IMREAD_COLOR)
            output, _ = upsampler.enhance(img, outscale=scale)
            cv2.imwrite(str(frames_out / frame_file.name), output)
            if progress_cb:
                progress_cb(i + 1, total)

        audio_only = tmp_path / "audio_source.mp4"
        shutil.copy(video_path, audio_only)

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps), "-i", str(frames_out / "frame_%06d.png"),
            "-i", str(audio_only),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-shortest",
            "-movflags", "+faststart",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    return out_path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Real-ESRGAN-Upscaling (langsam auf reiner CPU!)")
    parser.add_argument("video_path")
    parser.add_argument("out_path")
    parser.add_argument("--scale", type=int, default=2, choices=[2, 3, 4])
    parser.add_argument("--tile", type=int, default=0, help="Kachelgroesse gegen Speicherprobleme (0 = aus)")
    args = parser.parse_args()

    def _progress(done: int, total: int) -> None:
        print(f"\rFrame {done}/{total}", end="", flush=True)

    try:
        out = upscale_video(args.video_path, args.out_path, args.scale, args.tile, progress_cb=_progress)
    except subprocess.CalledProcessError as e:
        print(f"\nffmpeg fehlgeschlagen:\n{e.stderr}")
        raise SystemExit(1)
    print(f"\nExport fertig: {out}")


if __name__ == "__main__":
    _main()
