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
from typing import Iterable

import pandas as pd

from config import (
    FIXED_COSTS_MONTHLY,
    GESCHAEFTSFUEHRUNG,
    PERSONALKOSTENQUOTE_WARNUNG,
    WARENEINSATZQUOTE_WARNUNG,
)

DB_PATH = Path(__file__).parent / "gastro_pilot.db"

_TABELLEN = {
    "umsatz": ["umsatz"],
    "personal": ["personalkosten_variabel", "stunden"],
    "wareneinsatz": ["wareneinsatz"],
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


def _to_sql_value(value):
    return None if pd.isna(value) else float(value)


def _upsert(conn: sqlite3.Connection, table: str, df: pd.DataFrame, value_cols: Iterable[str]) -> None:
    value_cols = list(value_cols)
    cols_sql = ", ".join(["datum"] + value_cols)
    placeholders = ", ".join(["?"] * (1 + len(value_cols)))
    update_sql = ", ".join(f"{c}=excluded.{c}" for c in value_cols)
    for _, row in df.iterrows():
        datum = row["datum"].strftime("%Y-%m-%d")
        values = [datum] + [_to_sql_value(row[c]) for c in value_cols]
        conn.execute(
            f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders}) "
            f"ON CONFLICT(datum) DO UPDATE SET {update_sql}",
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
    """Löscht alle gespeicherten Rohdaten (Umsatz/Personal/Wareneinsatz) unwiderruflich.
    Gespeicherte Einstellungen (Fixkosten, Gehälter, Warnschwellen) bleiben davon unberührt."""
    with _connect() as conn:
        for table in _TABELLEN:
            conn.execute(f"DELETE FROM {table}")
