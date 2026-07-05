# Gastro Pilot – MVP-Dashboard

Erster Code-Baustein für Gastro Pilot (siehe `Gastro_Pilot_Konzept.docx`). Führt einen
Orderbird-Kassenbuch-Export (Umsatz), einen Aplano-Auswertungs-Export (Personalkosten)
und optional einen Wareneinsatz-Export pro Tag zusammen, berechnet Personalkostenquote
und Wareneinsatzquote, verteilt Fixkosten und Geschäftsführer-Fixgehälter anteilig auf
jeden Tag und zeigt einen Vorwochenvergleich. Warnschwellen sind bewusst regelbasiert
(kein ML), um zuerst zu prüfen, ob die Kennzahlen-Zusammenführung im Alltag überhaupt hilft.

## Wichtiger Hinweis zur Personalkosten-Berechnung

Aplano trackt nur stundenbasiert bezahlte Mitarbeiter. Fixgehälter (z. B. für
Geschäftsführung) tauchen dort nicht auf. Deshalb werden sie separat hinterlegt (siehe
"Fixkosten, Gehälter & Warnschwellen anpassen") und in `metrics.py` zu den
Aplano-Personalkosten addiert – nur so bildet die Personalkostenquote die tatsächlichen
Gesamt-Personalkosten ab.

## Installation

```bash
pip install -r requirements.txt
```

## Start

```bash
streamlit run app.py
```

Im Browser öffnet sich das Dashboard. Zum Testen kannst du erstmal die Dateien aus
`sample_data/` hochladen (`orderbird_sample.csv`, `aplano_sample.csv`,
`wareneinsatz_sample.csv` – decken 4 Kalenderwochen ab, damit auch der
Vorwochenvergleich etwas zum Vergleichen hat).

## Eigene Daten verwenden

1. In Orderbird (MY orderbird → Kassenbuch) den Export für den gewünschten Zeitraum als
   CSV herunterladen.
2. In Aplano (Auswertung) den Export als CSV herunterladen.
3. Wareneinsatz gibt es aktuell bei den wenigsten Kassen-/Personalsystemen als fertigen
   Export – trage ihn notfalls manuell in eine CSV mit den Spalten `Datum;Wareneinsatz`
   ein (z. B. aus Lieferantenrechnungen).
4. Alle Dateien im Dashboard hochladen (Wareneinsatz ist optional).

**Wichtig:** Lade deine echten Exporte nur lokal hoch (`streamlit run app.py` auf
deinem eigenen Rechner), nicht in eine öffentlich erreichbare Cloud-Version – der
Aplano-Export enthält personenbezogene Daten (Namen, Löhne).

Die Spalten-Erkennung ist automatisch (erkennt z. B. "Datum", "Umsatz", "Stunden",
"Stundenlohn" in gängigen Schreibweisen). Falls deine Export-Datei andere Spaltennamen
verwendet und die Erkennung fehlschlägt, meldet die App genau das und du trägst den
exakten Spaltennamen in `config.py` unter `COLUMN_OVERRIDES` ein.

## Fixkosten, Gehälter & Warnschwellen anpassen

Im Dashboard oben unter "Einstellungen (Fixkosten, Gehälter, Warnschwellen)" ausklappen,
Werte anpassen und auf "Einstellungen speichern" klicken. Kein Code-Ändern mehr nötig:

- Monatliche Fixkosten ohne Personal (Miete, Energie, Versicherungen, Software/Abos)
- Anzahl und Fixgehalt pro Geschäftsführer/in
- Warnschwellen für Personalkostenquote und Wareneinsatzquote (in %)

Die Werte landen in `gastro_pilot.db` und gelten ab dem nächsten Neuladen der Seite.
`config.py` liefert nur noch die Vorbelegung beim allerersten Start (bevor eigene Werte
gespeichert wurden) sowie die Fallback-Werte für `test_run.py`.

## Export (PDF / Excel)

Unten im Dashboard gibt es zwei Download-Buttons:

- **Excel** (.xlsx): drei Tabellenblätter – Tagesübersicht, Vorwochenvergleich, Monatsübersicht
- **PDF**: kompakter Bericht mit Monatsübersicht und Vorwochenvergleich, z. B. zum
  Weiterleiten an den Steuerberater

Beide werden erst erzeugt, wenn Daten vorhanden sind (aktuell hochgeladen oder aus
`gastro_pilot.db` geladen).

## Datenpersistenz (SQLite)

Jeder hochgeladene Export wird automatisch in einer lokalen Datei `gastro_pilot.db`
(liegt neben `app.py`) gespeichert. Beim nächsten Start musst du nicht alles neu
hochladen – nur neue Tage ergänzen. Neue Uploads überschreiben nur die betroffenen
Tage, ältere Tage bleiben erhalten.

- Zum Löschen aller gespeicherten Rohdaten (Umsatz/Personal/Wareneinsatz): im Dashboard
  unter "Einstellungen" die Checkbox bestätigen und auf "Gespeicherte Daten löschen"
  klicken. Gespeicherte Einstellungen (Fixkosten, Gehälter, Warnschwellen) bleiben dabei
  erhalten.
- **Wichtig für Streamlit Cloud:** Dort ist das Dateisystem nicht dauerhaft – bei jedem
  Neustart/Redeploy der App geht `gastro_pilot.db` verloren. Echte Persistenz über
  Wochen hinweg funktioniert nur, wenn du die App lokal ausführst
  (`streamlit run app.py` auf deinem eigenen Rechner).
- Falls dein `Gastro Pilot`-Ordner über iCloud Drive/Dropbox synchronisiert wird und
  beim Start ein "disk I/O error" auftaucht: das liegt an der Cloud-Synchronisation
  des Ordners, nicht am Code. Lege den Ordner in diesem Fall lokal (nicht
  cloud-synchronisiert) ab, oder schließe ihn von der Synchronisation aus.

## Dateien

| Datei | Zweck |
|---|---|
| `data_loader.py` | Lädt und normalisiert die CSV-Exporte |
| `metrics.py` | Berechnet Kennzahlen und Empfehlungen |
| `exports.py` | Baut den Excel- und PDF-Export |
| `storage.py` | Speichert/lädt Rohdaten aus `gastro_pilot.db` (SQLite) |
| `app.py` | Streamlit-Dashboard (Oberfläche) |
| `config.py` | Fixkosten, Schwellenwerte, Spalten-Overrides |
| `test_run.py` | Prüft Loader + Metriken ohne Streamlit (`python3 test_run.py`) |
| `sample_data/` | Beispieldaten zum Ausprobieren |

## Nächste Ausbauschritte

Sobald sich im eigenen Café zeigt, dass die Kennzahlen echten Mehrwert bringen:

1. Chat-Funktion mit KI-Anbindung (z. B. Anthropic API), die Fragen zu den eigenen Zahlen
   beantwortet – Kernidee aus dem Konzeptdokument, Abschnitt 4.3
2. Aplano Pro-Tarif (API-Schnittstelle) statt manuellem CSV-Export anbinden, danach bei
   orderbird wegen einer Partner-API anfragen (siehe Konzeptdokument, Abschnitt 5 und 9)
