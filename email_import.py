"""Holt automatisch neue Berichte aus einem E-Mail-Postfach ab und übernimmt sie in die
Datenbank – gedacht für den in "MY orderbird" hinterlegbaren automatischen Report-Versand
(aktuell bestätigt für den monatlichen DATEV-Bericht unter Einstellungen > DATEV-Details;
falls Orderbird auch für die normale Umsatzanalyse einen Auto-Versand anbietet, funktioniert
das genauso, indem dieselbe Adresse dort hinterlegt wird).

Läuft nicht im Dashboard selbst, sondern wird zeitgesteuert über GitHub Actions gestartet
(siehe .github/workflows/fetch_orderbird_email.yml), da Streamlit Community Cloud nur aktiv
ist, wenn jemand die Seite öffnet.

Benötigte Umgebungsvariablen (als GitHub Secrets hinterlegt, siehe README):
    EMAIL_ADDRESS       – die Postfach-Adresse, die bei Orderbird als Empfänger hinterlegt ist
    EMAIL_APP_PASSWORD  – App-Passwort für dieses Postfach (kein normales Passwort!)
    EMAIL_IMAP_SERVER   – IMAP-Server, Standard: imap.gmail.com

Wichtig: Für dieses Postfach sollte eine eigens angelegte Adresse verwendet werden (nicht
das private Postfach), da hier automatisiert Anhänge gelesen und als "gelesen" markiert
werden.
"""

from __future__ import annotations

import email
import imaplib
import os
from datetime import datetime
from email.message import Message
from pathlib import Path

import data_loader
import storage

INCOMING_DIR = Path(__file__).parent / "incoming"
ALLOWED_EXTENSIONS = {".csv", ".xml", ".pdf"}


def _connect() -> imaplib.IMAP4_SSL:
    server = os.environ.get("EMAIL_IMAP_SERVER", "imap.gmail.com")
    address = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_APP_PASSWORD"]
    conn = imaplib.IMAP4_SSL(server)
    conn.login(address, password)
    return conn


def _save_attachments(msg: Message, save_dir: Path) -> list[Path]:
    saved: list[Path] = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if not filename:
            continue
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = save_dir / f"{timestamp}_{filename}"
        target.write_bytes(payload)
        saved.append(target)
    return saved


def fetch_neue_anhaenge() -> list[Path]:
    """Holt alle ungelesenen E-Mails ab, speichert unterstützte Anhänge (CSV/XML/PDF) in
    incoming/ und markiert die Mails danach als gelesen, damit sie beim nächsten Lauf nicht
    doppelt verarbeitet werden. Gibt die Pfade der neu gespeicherten Dateien zurück."""
    INCOMING_DIR.mkdir(exist_ok=True)
    conn = _connect()
    try:
        conn.select("INBOX")
        status, data = conn.search(None, "UNSEEN")
        saved_files: list[Path] = []
        if status == "OK":
            for msg_id in data[0].split():
                status, msg_data = conn.fetch(msg_id, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                saved_files.extend(_save_attachments(msg, INCOMING_DIR))
                conn.store(msg_id, "+FLAGS", "\\Seen")
        return saved_files
    finally:
        conn.logout()


def verarbeite_neue_dateien(dateien: list[Path]) -> None:
    """Versucht, neu abgeholte CSV-Dateien mit dem bestehenden Orderbird-Loader
    (data_loader.load_orderbird) einzulesen und in gastro_pilot.db zu speichern.

    Dateien, die nicht automatisch verarbeitet werden können (z. B. eine andere
    Formatvariante wie der DATEV-XML-Export oder ein PDF), bleiben unverändert in
    incoming/ liegen statt verworfen zu werden – so geht nichts verloren, und die
    Datei kann später manuell geprüft und der Loader bei Bedarf angepasst werden."""
    storage.init_db()
    for pfad in dateien:
        if pfad.suffix.lower() != ".csv":
            print(f"Übersprungen (kein CSV, manuelle Prüfung nötig): {pfad.name}")
            continue
        try:
            df = data_loader.load_orderbird(pfad)
            storage.save_umsatz(df)
            print(f"Verarbeitet: {pfad.name} ({len(df)} Tage Umsatz gespeichert)")
        except Exception as exc:
            print(
                f"Konnte {pfad.name} nicht automatisch einlesen ({exc}). "
                "Datei bleibt in incoming/ liegen zur manuellen Prüfung."
            )


def main() -> None:
    neue_dateien = fetch_neue_anhaenge()
    if not neue_dateien:
        print("Keine neuen Anhänge gefunden.")
        return
    print(f"{len(neue_dateien)} neue Anhänge gefunden: {[p.name for p in neue_dateien]}")
    verarbeite_neue_dateien(neue_dateien)


if __name__ == "__main__":
    main()
