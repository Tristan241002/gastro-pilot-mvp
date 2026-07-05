"""Persistiert hochgeladene Rohdaten (Umsatz, Personalkosten, Wareneinsatz) in einer
lokalen SQLite-Datenbank (`gastro_pilot.db`, liegt neben dieser Datei), damit du nicht bei
jedem Start alle Exporte neu hochladen musst. Neue Uploads ergänzen/überschreiben nur die
betroffenen Tage, ältere Tage bleiben erhalten.

Wichtiger Hinweis: Auf Streamlit Community Cloud ist das Dateisystem nicht dauerhaft – die
Datenbank-Datei geht bei jedem Neustart/Redeploy der App verloren. Für echte Persistenz über
Wochen hinweg die App lokal ausführen (`streamlit run app.py` auf dem eigenen Rechner).
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from config import (
    FIXED_COSTS_MONTHLY,
    GESCHAEFTSFUEHRUNG,
    PERSONALKOSTENQUOTE_WARNUNG,
    WARENEINSATZQUOTE_WARNUNG,
)

DB_PATH = Path(__file__).parent / "gastro_pilot.db"

# Tabellen mit "datum" als alleinigem Schlüssel (Bewegungsdaten, ein Wert pro Tag)
_TABELLEN = {
    "umsatz": ["umsatz"],
    "personal": ["personalkosten_variabel", "stunden"],
    "wareneinsatz": ["wareneinsatz"],
}

# Tabellen mit zusammengesetztem Schlüssel (datum + Zutat/Produkt) für die Warenwirtschaft
_TABELLEN_ZUSAMMENGESETZT = {
    "wareneingang": (["datum", "zutat"], ["menge", "preis"]),
    "verkaufsmengen": (["datum", "produkt"], ["menge"]),
    "inventur": (["datum", "zutat"], ["bestand"]),
}

# Startwerte für den Einstellungsbereich im Dashboard – nur relevant, solange noch keine
# eigenen Werte gespeichert wurden. Kommen als sinnvolle Vorbelegung aus config.py.
DEFAULT_SETTINGS = {
    "miete": FIXED_COSTS_MONTHLY.get("Miete", 0.0),
    "energie": FIXED_COSTS_MONTHLY.get("Energie", 0.0),
    "versicherungen": FIXED_COSTS_MONTHLY.get("Versicherungen", 0.0),
    "software_abos": FIXED_COSTS_MONTHLY.get("Software/Abos", 0.0),
    "gf_anzahl": float(GESCHAEFTSFUEHRUNG["Anzahl"]),
    "gf_fixgehalt": GESCHAEFTSFUEHRUNG["Fixgehalt_pro_Person_Monat"],
    "personalkostenquote_warnung": PERSONALKOSTENQUOTE_WARNUNG,
    "wareneinsatzquote_warnung": WARENEINSATZQUOTE_WARNUNG,
}


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS umsatz (datum TEXT PRIMARY KEY, umsatz REAL)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS personal ("
            "datum TEXT PRIMARY KEY, personalkosten_variabel REAL, stunden REAL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS wareneinsatz (datum TEXT PRIMARY KEY, wareneinsatz REAL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL)"
        )
        # Warenwirtschaft: Stammdaten (Zutaten, Rezepturen) + Bewegungsdaten
        conn.execute(
            "CREATE TABLE IF NOT EXISTS zutaten ("
            "name TEXT PRIMARY KEY, einheit TEXT, einkaufspreis_pro_einheit REAL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS rezepturen ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, produkt TEXT, zutat TEXT, "
            "menge_pro_einheit REAL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS wareneingang ("
            "datum TEXT, zutat TEXT, menge REAL, preis REAL, PRIMARY KEY(datum, zutat))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS verkaufsmengen ("
            "datum TEXT, produkt TEXT, menge REAL, PRIMARY KEY(datum, produkt))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS inventur ("
            "datum TEXT, zutat TEXT, bestand REAL, PRIMARY KEY(datum, zutat))"
        )


def _to_sql_value(value):
    return None if pd.isna(value) else float(value)


def _key_sql_value(value):
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _upsert(
    conn: sqlite3.Connection,
    table: str,
    df: pd.DataFrame,
    value_cols: Iterable[str],
    key_cols: Iterable[str] = ("datum",),
) -> None:
    key_cols = list(key_cols)
    value_cols = list(value_cols)
    cols_sql = ", ".join(key_cols + value_cols)
    placeholders = ", ".join(["?"] * (len(key_cols) + len(value_cols)))
    conflict_sql = ", ".join(key_cols)
    update_sql = ", ".join(f"{c}=excluded.{c}" for c in value_cols)
    for _, row in df.iterrows():
        values = [_key_sql_value(row[k]) for k in key_cols] + [
            _to_sql_value(row[c]) for c in value_cols
        ]
        conn.execute(
            f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict_sql}) DO UPDATE SET {update_sql}",
            values,
        )


def save_umsatz(df: pd.DataFrame) -> None:
    if df.empty:
        return
    with _connect() as conn:
        _upsert(conn, "umsatz", df, _TABELLEN["umsatz"])


def save_personal(df: pd.DataFrame) -> None:
    if df.empty:
        return
    with _connect() as conn:
        _upsert(conn, "personal", df, _TABELLEN["personal"])


def save_wareneinsatz(df: pd.DataFrame) -> None:
    if df.empty:
        return
    with _connect() as conn:
        _upsert(conn, "wareneinsatz", df, _TABELLEN["wareneinsatz"])


def _load(table: str) -> pd.DataFrame:
    with _connect() as conn:
        df = pd.read_sql(f"SELECT * FROM {table} ORDER BY datum", conn)
    if not df.empty:
        df["datum"] = pd.to_datetime(df["datum"])
    return df


def load_umsatz() -> pd.DataFrame:
    return _load("umsatz")


def load_personal() -> pd.DataFrame:
    return _load("personal")


def load_wareneinsatz() -> pd.DataFrame:
    return _load("wareneinsatz")


def _load_zusammengesetzt(table: str) -> pd.DataFrame:
    with _connect() as conn:
        df = pd.read_sql(f"SELECT * FROM {table} ORDER BY datum", conn)
    if not df.empty:
        df["datum"] = pd.to_datetime(df["datum"])
    return df


def save_wareneingang(df: pd.DataFrame) -> None:
    if df.empty:
        return
    key_cols, value_cols = _TABELLEN_ZUSAMMENGESETZT["wareneingang"]
    with _connect() as conn:
        _upsert(conn, "wareneingang", df, value_cols, key_cols)


def load_wareneingang() -> pd.DataFrame:
    return _load_zusammengesetzt("wareneingang")


def save_verkaufsmengen(df: pd.DataFrame) -> None:
    if df.empty:
        return
    key_cols, value_cols = _TABELLEN_ZUSAMMENGESETZT["verkaufsmengen"]
    with _connect() as conn:
        _upsert(conn, "verkaufsmengen", df, value_cols, key_cols)


def load_verkaufsmengen() -> pd.DataFrame:
    return _load_zusammengesetzt("verkaufsmengen")


def save_inventur_zeile(datum, zutat: str, bestand: float) -> None:
    """Speichert/überschreibt die Zählung einer einzelnen Zutat zu einem Stichtag
    (für das Inventur-Eingabeformular im Dashboard)."""
    datum_str = datum.strftime("%Y-%m-%d") if hasattr(datum, "strftime") else str(datum)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO inventur (datum, zutat, bestand) VALUES (?, ?, ?) "
            "ON CONFLICT(datum, zutat) DO UPDATE SET bestand=excluded.bestand",
            (datum_str, zutat, float(bestand)),
        )


def load_inventur() -> pd.DataFrame:
    return _load_zusammengesetzt("inventur")


def list_inventur_stichtage() -> list:
    """Alle Stichtage, an denen mindestens eine Zutat gezählt wurde, aufsteigend sortiert."""
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT datum FROM inventur ORDER BY datum").fetchall()
    return [r[0] for r in rows]


def add_zutat(name: str, einheit: str, einkaufspreis_pro_einheit: float) -> None:
    """Legt eine neue Zutat an oder aktualisiert Einheit/Preis einer bestehenden."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO zutaten (name, einheit, einkaufspreis_pro_einheit) VALUES (?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET einheit=excluded.einheit, "
            "einkaufspreis_pro_einheit=excluded.einkaufspreis_pro_einheit",
            (name.strip(), einheit.strip(), float(einkaufspreis_pro_einheit)),
        )


def save_zutatenliste(df: pd.DataFrame) -> None:
    """Legt mehrere Zutaten auf einmal an/aktualisiert sie (Massen-Import per CSV),
    statt sie einzeln über das Formular einzutragen. Bestehende Zutaten mit gleichem
    Namen werden überschrieben (Einheit + Preis)."""
    if df.empty:
        return
    with _connect() as conn:
        for _, row in df.iterrows():
            conn.execute(
                "INSERT INTO zutaten (name, einheit, einkaufspreis_pro_einheit) "
                "VALUES (?, ?, ?) ON CONFLICT(name) DO UPDATE SET "
                "einheit=excluded.einheit, "
                "einkaufspreis_pro_einheit=excluded.einkaufspreis_pro_einheit",
                (row["name"], row["einheit"], _to_sql_value(row["einkaufspreis_pro_einheit"])),
            )


def list_zutaten() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM zutaten ORDER BY name", conn)


def delete_zutat(name: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM zutaten WHERE name = ?", (name,))


def add_rezeptur_zeile(produkt: str, zutat: str, menge_pro_einheit: float) -> None:
    """Fügt der Rezeptur eines Produkts eine Zutat mit Menge pro verkaufter Einheit hinzu."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO rezepturen (produkt, zutat, menge_pro_einheit) VALUES (?, ?, ?)",
            (produkt.strip(), zutat.strip(), float(menge_pro_einheit)),
        )


def list_rezepturen(produkt: Optional[str] = None) -> pd.DataFrame:
    with _connect() as conn:
        if produkt:
            return pd.read_sql(
                "SELECT * FROM rezepturen WHERE produkt = ? ORDER BY zutat", conn, params=(produkt,)
            )
        return pd.read_sql("SELECT * FROM rezepturen ORDER BY produkt, zutat", conn)


def list_produkte_mit_rezeptur() -> list:
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT produkt FROM rezepturen ORDER BY produkt").fetchall()
    return [r[0] for r in rows]


def delete_rezeptur_zeile(zeile_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM rezepturen WHERE id = ?", (zeile_id,))


def save_settings(settings: dict) -> None:
    """Speichert Fixkosten/Gehälter/Warnschwellen aus dem Einstellungsbereich im Dashboard."""
    with _connect() as conn:
        for key, value in settings.items():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, float(value)),
            )


def load_settings() -> dict:
    """Lädt gespeicherte Einstellungen, ergänzt fehlende Werte mit den Vorgaben aus config.py."""
    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    gespeichert = {key: value for key, value in rows}
    return {**DEFAULT_SETTINGS, **gespeichert}


def reset_all() -> None:
    """Löscht alle gespeicherten Bewegungsdaten (Umsatz/Personal/Wareneinsatz/Wareneingang/
    Verkaufsmengen/Inventur) unwiderruflich. Einstellungen sowie die Warenwirtschafts-
    Stammdaten (Zutatenliste, Rezepturen) bleiben davon unberührt."""
    with _connect() as conn:
        for table in list(_TABELLEN) + list(_TABELLEN_ZUSAMMENGESETZT):
            conn.execute(f"DELETE FROM {table}")
