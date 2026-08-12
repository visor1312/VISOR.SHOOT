"""E-Mail-Versand - mit einer austauschbaren Zustellart.

WARUM DAS SO GEBAUT IST: Echte E-Mails von der eigenen Domain zu
verschicken, braucht eine Domain mit SPF- und DKIM-Eintraegen. Die gibt es
noch nicht. Ohne einen Zwischenschritt haetten wir also Code, der sich
ueberhaupt nicht ausprobieren laesst - und Code, den nie jemand laufen
sieht, funktioniert erfahrungsgemaess nicht.

Deshalb drei Zustellarten (HOOKCUT_MAIL_BACKEND):

  "log"    Standard. Die Mail wird ins Serverfenster geschrieben, samt
           Bestaetigungslink. Zum Ausprobieren auf dem eigenen Rechner
           voellig ausreichend: Link herauskopieren, aufrufen, fertig.
  "resend" Echter Versand ueber resend.com (3.000 Mails/Monat gratis).
           Braucht RESEND_API_KEY und eine verifizierte Absender-Domain.
  "aus"    Es wird gar nichts verschickt (und auch nichts protokolliert).

Der Rest der Anwendung sieht davon nichts: sie ruft send() auf und
bekommt True oder False zurueck.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from backend import betreiber, config


class MailFehler(Exception):
    """Zustellung fehlgeschlagen - der Aufrufer entscheidet, wie schlimm das ist."""


def _zustellen_log(empfaenger: str, betreff: str, text: str) -> bool:
    """Ins Serverfenster schreiben statt zu verschicken."""
    rahmen = "=" * 68
    print(f"\n{rahmen}\nE-MAIL (nicht wirklich verschickt - HOOKCUT_MAIL_BACKEND=log)"
          f"\nAn:      {empfaenger}\nBetreff: {betreff}\n{rahmen}\n{text}\n{rahmen}\n",
          flush=True)
    return True


def _zustellen_resend(empfaenger: str, betreff: str, text: str) -> bool:
    if not config.RESEND_API_KEY:
        raise MailFehler("RESEND_API_KEY ist nicht gesetzt.")
    daten = json.dumps({
        "from": config.MAIL_FROM,
        "to": [empfaenger],
        "subject": betreff,
        "text": text,
    }).encode("utf-8")
    anfrage = urllib.request.Request(
        "https://api.resend.com/emails", data=daten, method="POST",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(anfrage, timeout=10) as antwort:
            return 200 <= antwort.status < 300
    except urllib.error.HTTPError as e:
        # Die Fehlermeldung von Resend ist hilfreich (z.B. "domain not
        # verified") - sie gehoert ins Log, aber NICHT zum Nutzer.
        raise MailFehler(f"Resend antwortete {e.code}: {e.read()[:300]!r}") from e
    except OSError as e:
        raise MailFehler(f"Resend nicht erreichbar: {e}") from e


_ZUSTELLARTEN = {
    "log": _zustellen_log,
    "resend": _zustellen_resend,
    "aus": lambda *_: True,
}


def send(empfaenger: str, betreff: str, text: str) -> bool:
    """Verschickt eine Mail. Wirft MailFehler, wenn die Zustellung scheitert."""
    zustellen = _ZUSTELLARTEN.get(config.MAIL_BACKEND)
    if zustellen is None:
        raise MailFehler(
            f"Unbekannte Zustellart {config.MAIL_BACKEND!r} - erlaubt sind: "
            f"{', '.join(sorted(_ZUSTELLARTEN))}")
    return zustellen(empfaenger, betreff, text)


def bestaetigungs_mail(empfaenger: str, anzeigename: str, link: str) -> str:
    """Der Text der Bestaetigungsmail. Bewusst kurz, ohne Bilder und ohne
    Marketing - so landet sie seltener im Spam und ist auf dem Handy lesbar."""
    return (
        f"Hallo {anzeigename},\n\n"
        f"bitte bestaetige deine E-Mail-Adresse fuer {betreiber.PLATTFORM_NAME}:\n\n"
        f"{link}\n\n"
        f"Der Link gilt 24 Stunden. Wenn du dich nicht angemeldet hast, "
        f"ignorier diese Mail einfach - dann passiert nichts.\n"
    )
