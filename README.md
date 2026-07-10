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

## Automatischer E-Mail-Import (Umsatz ohne manuellen Upload)

Statt den Orderbird-Export jedes Mal manuell herunterzuladen und hochzuladen, kann
Gastro Pilot ein E-Mail-Postfach automatisch auf neue Berichte prüfen und sie selbst
einlesen. Das funktioniert, weil Orderbird unter "MY orderbird" → Einstellungen →
DATEV-Details bereits heute einen automatischen monatlichen Report-Versand an eine
frei wählbare E-Mail-Adresse anbietet (ursprünglich für den Steuerberater gedacht,
funktioniert aber mit jeder Adresse). Trägt man dort eine eigene Gastro-Pilot-Adresse
ein, kommen die Daten von selbst an.

**⚠️ Bevor du das aktivierst:** Dieses Repository ist aktuell öffentlich einsehbar.
Der automatische Import schreibt echte Umsatzdaten in `gastro_pilot.db` und committet
sie zurück ins Repo, damit sie den Streamlit-Cloud-Neustart überleben. Öffentlich
einsehbare echte Umsatzzahlen willst du wahrscheinlich nicht. Stelle das Repository
deshalb zuerst auf privat (GitHub → Repository → Settings → ganz unten "Danger Zone" →
"Change visibility" → "Make private"). Streamlit Community Cloud kann auch private
Repos deployen, das funktioniert weiterhin ohne Änderung an der App selbst.

### Einrichtung

1. **Repo auf privat stellen** (siehe Warnung oben) – einmalig, betrifft auch alle
   künftigen echten Daten in diesem Repo, nicht nur den E-Mail-Import.
2. **Eigenes E-Mail-Postfach anlegen**, z. B. ein neues, kostenloses Gmail-Konto nur für
   diesen Zweck (nicht dein privates Postfach verwenden).
3. In diesem Gmail-Konto **2-Faktor-Authentifizierung aktivieren** und darüber ein
   **App-Passwort** erzeugen (Google-Kontoeinstellungen → Sicherheit → App-Passwörter).
   Das ist ein separates Passwort nur für diesen automatisierten Zugriff, nicht dein
   normales Login-Passwort.
4. In GitHub im Repository unter **Settings → Secrets and variables → Actions → New
   repository secret** drei Secrets anlegen:
   - `EMAIL_ADDRESS` – die neue Gmail-Adresse
   - `EMAIL_APP_PASSWORD` – das eben erzeugte App-Passwort
   - `EMAIL_IMAP_SERVER` – `imap.gmail.com`
5. In **MY orderbird** → Einstellungen → DATEV-Details die neue Gmail-Adresse als
   Empfänger eintragen.
6. Fertig – der Zeitplan-Job (`.github/workflows/fetch_orderbird_email.yml`) läuft ab
   jetzt täglich automatisch. Zum sofortigen Testen: im GitHub-Repo oben auf "Actions" →
   "Orderbird E-Mail automatisch abholen" → "Run workflow".

### Wichtige Einschränkung (Stand jetzt)

Bisher ist nur der **monatliche DATEV-Bericht** nachweislich automatisch per E-Mail
verschickbar – ein Buchhaltungsformat, das primär für den Steuerberater gedacht ist und
möglicherweise nicht exakt dieselben Spalten liefert wie der bisherige manuelle
Umsatzanalyse-Export. Ob "MY orderbird" auch für die normale, tagesgenaue Umsatzanalyse
einen automatischen Versand anbietet, ist noch nicht geprüft – das lohnt sich in den
eigenen Kontoeinstellungen nachzuschauen. `email_import.py` versucht jede ankommende
CSV-Datei mit dem bestehenden Orderbird-Loader einzulesen; gelingt das nicht (z. B. weil
das Format abweicht), bleibt die Datei unverändert im Ordner `incoming/` liegen und wird
nicht verworfen – der Loader kann dann anhand der echten Datei gezielt angepasst werden.
Für Warenverlust/Verkaufsmengen und den Aplano-Personalimport ist der E-Mail-Weg noch
nicht eingerichtet, dafür bleibt der manuelle Upload vorerst bestehen.

## Warenwirtschaft & Warenverlust

Unten im Dashboard gibt es einen eigenen Bereich, der zeigt, ob und wo Ware verloren
geht (Schwund, großzügige Portionen, Fehlbuchungen o. Ä.) – auf Zutatenebene, nicht nur
als grobe Wareneinsatzquote:

1. **Zutaten verwalten**: Rohstoffe anlegen (Name, Einheit wie kg/l/Stück, Einkaufspreis
   pro Einheit) – entweder einzeln über das Formular, oder als Massen-Import: eine CSV
   mit den Spalten Name, Einheit, Einkaufspreis hochladen (z. B. deine eigene Preisliste
   oder eine Lieferanten-Warenliste). Beispiel dafür: `sample_data/zutatenliste_sample.csv`.
2. **Rezepturen verwalten**: pro verkauftem Produkt hinterlegen, welche Zutaten in
   welcher Menge hineingehen (z. B. Cappuccino = 0,018 kg Kaffeebohnen + 0,15 l Milch).
   Der Produktname muss zu den Produktnamen aus dem Verkaufsmengen-Export passen.
3. **Wareneingang hochladen**: CSV mit deinen Lieferungen (Spalten Datum, Zutat, Menge,
   Gesamtpreis) – trage sie aus deinen Lieferantenrechnungen ein, ähnlich wie beim
   Wareneinsatz-Import.
4. **Verkaufsmengen hochladen**: CSV mit verkaufter Stückzahl je Produkt und Tag. Kommt
   aus Orderbird: MY orderbird → Berichte → Umsatzanalyse → "Detaillierte
   Umsatzaufteilung" als CSV exportieren.
5. **Inventur eintragen**: an einem Stichtag den Bestand jeder Zutat eintippen (z. B.
   einmal am Monatsanfang, einmal am Monatsende). Wichtig: **ohne mindestens zwei
   Zähltermine kann kein Warenverlust berechnet werden** – das ist keine
   Programm-Einschränkung, sondern folgt zwangsläufig aus der Rechnung selbst.

Der Warenverlust wird für den Zeitraum zwischen den beiden letzten Inventur-Stichtagen
berechnet: tatsächlicher Verbrauch (Anfangsbestand + Wareneingang − Endbestand) minus
theoretischer Verbrauch (verkaufte Menge je Produkt × Rezeptur). Die Differenz ist der
Warenverlust je Zutat, in Menge und (mit hinterlegtem Einkaufspreis) in Euro.

Zum Ausprobieren mit Beispieldaten: einmalig `python3 seed_demo_warenwirtschaft.py`
ausführen (legt Beispiel-Zutaten, -Rezepturen und zwei Inventur-Stichtage an), dann im
Dashboard `sample_data/wareneingang_sample.csv` und `sample_data/verkaufsmengen_sample.csv`
hochladen.

## Dateien

| Datei | Zweck |
|---|---|
| `data_loader.py` | Lädt und normalisiert die CSV-Exporte |
| `metrics.py` | Berechnet Kennzahlen und Empfehlungen |
| `exports.py` | Baut den Excel- und PDF-Export |
| `storage.py` | Speichert/lädt alle Daten aus `gastro_pilot.db` (SQLite) |
| `warenverlust.py` | Berechnet den Warenverlust je Zutat |
| `email_import.py` | Holt Orderbird-Berichte automatisch aus einem E-Mail-Postfach ab |
| `app.py` | Streamlit-Dashboard (Oberfläche) |
| `config.py` | Fixkosten, Schwellenwerte, Spalten-Overrides |
| `test_run.py` | Prüft Loader + Metriken ohne Streamlit (`python3 test_run.py`) |
| `seed_demo_warenwirtschaft.py` | Befüllt die Warenwirtschaft mit Beispieldaten (nur zum Testen) |
| `sample_data/` | Beispieldaten zum Ausprobieren |

## Nächste Ausbauschritte

Sobald sich im eigenen Café zeigt, dass die Kennzahlen echten Mehrwert bringen:

1. Chat-Funktion mit KI-Anbindung (z. B. Anthropic API), die Fragen zu den eigenen Zahlen
   beantwortet – Kernidee aus dem Konzeptdokument, Abschnitt 4.3
2. Aplano Pro-Tarif (API-Schnittstelle) statt manuellem CSV-Export anbinden; für Orderbird
   den automatischen E-Mail-Import (siehe oben) auf die tagesgenaue Umsatzanalyse und
   perspektivisch auf Verkaufsmengen ausweiten, statt nur auf den DATEV-Bericht
3. Prüfen, ob Orderbirds eigenes Warenwirtschafts-Modul ("SimpleOrder") noch existiert –
   könnte Wareneingang/Rezepturen/Inventur ggf. direkt mitliefern statt manueller Pflege
