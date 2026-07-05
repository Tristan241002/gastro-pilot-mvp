"""Einmalig ausführen, um die Warenwirtschaft mit Beispiel-Zutaten, -Rezepturen und
zwei Inventur-Stichtagen zu befüllen, passend zu `sample_data/wareneingang_sample.csv`
und `sample_data/verkaufsmengen_sample.csv`. Danach im Dashboard nur noch die beiden
CSVs unter "Wareneingang & Verkaufsmengen hochladen" hochladen, um den Warenverlust
zu sehen.

Start:
    python3 seed_demo_warenwirtschaft.py

Achtung: Legt die Zutaten/Rezepturen/Inventur in deiner echten `gastro_pilot.db` an.
Nur zu Demo-/Testzwecken verwenden, nicht mit echten Café-Daten mischen.
"""

import pandas as pd
import storage

storage.init_db()

storage.add_zutat("Kaffeebohnen", "kg", 28.0)
storage.add_zutat("Milch", "l", 1.10)
storage.add_zutat("Croissant", "Stück", 0.80)

storage.add_rezeptur_zeile("Cappuccino", "Kaffeebohnen", 0.018)
storage.add_rezeptur_zeile("Cappuccino", "Milch", 0.15)
storage.add_rezeptur_zeile("Latte Macchiato", "Kaffeebohnen", 0.018)
storage.add_rezeptur_zeile("Latte Macchiato", "Milch", 0.20)
storage.add_rezeptur_zeile("Filterkaffee", "Kaffeebohnen", 0.012)
storage.add_rezeptur_zeile("Croissant", "Croissant", 1.0)

# Inventur-Stichtag vor Monatsbeginn (Anfangsbestand) und am letzten Tag des Beispielzeitraums
storage.save_inventur_zeile(pd.Timestamp("2026-05-31"), "Kaffeebohnen", 8.0)
storage.save_inventur_zeile(pd.Timestamp("2026-05-31"), "Milch", 25.0)
storage.save_inventur_zeile(pd.Timestamp("2026-05-31"), "Croissant", 50)

storage.save_inventur_zeile(pd.Timestamp("2026-06-28"), "Kaffeebohnen", 5.0)
storage.save_inventur_zeile(pd.Timestamp("2026-06-28"), "Milch", 15.0)
storage.save_inventur_zeile(pd.Timestamp("2026-06-28"), "Croissant", 20)

print(
    "Fertig. Jetzt im Dashboard unter 'Wareneingang & Verkaufsmengen hochladen' "
    "die Dateien wareneingang_sample.csv und verkaufsmengen_sample.csv hochladen, "
    "dann erscheint unten der Warenverlust."
)
