"""Lädt und normalisiert Exporte aus Orderbird (Kassensystem), Aplano (Personalplanung)
und einem Wareneinsatz-Export (z. B. manuell gepflegte Tabelle oder Wareneinkaufssystem).

Da die Anbieter kein öffentlich fixiertes Export-Format garantieren, versucht dieses
Modul gängige Spaltennamen automatisch zu erkennen. Falls die Erkennung fehlschlägt,
trage in config.py unter COLUMN_OVERRIDES die exakten Spaltennamen deines Exports ein.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import pandas as pd

from config import COLUMN_OVERRIDES

# Kandidaten für gängige Spaltennamen (Groß-/Kleinschreibung und Leerzeichen egal)
DATE_CANDIDATES = ["datum", "belegdatum", "buchungsdatum", "date", "tag"]
AMOUNT_CANDIDATES = ["umsatz", "betrag", "brutto", "einnahmen", "gesamtbetrag", "summe"]
HOURS_CANDIDATES = ["stunden", "ist-stunden", "iststunden", "arbeitsstunden", "hours"]
COST_CANDIDATES = ["personalkosten", "lohnkosten", "kosten", "cost"]
WAGE_CANDIDATES = ["stundenlohn", "lohn", "wage", "hourly rate", "hourlyrate"]
WARENEINSATZ_CANDIDATES = ["wareneinsatz", "wareneinkauf", "warenkosten", "einkauf", "cogs"]
ZUTAT_CANDIDATES = ["zutat", "rohstoff", "ingredient", "artikel", "wareneingang artikel"]
PRODUKT_CANDIDATES = ["produkt", "artikel", "artikelname", "produktname", "item", "menuepunkt"]
MENGE_CANDIDATES = [
    "menge", "anzahl", "stückzahl", "stueckzahl", "verkaufte menge", "verkauft", "quantity",
]
PREIS_CANDIDATES = ["preis", "gesamtpreis", "betrag", "kosten", "summe"]


def _find_column(columns: list[str], candidates: list[str]) -> Optional[str]:
    normalized = {c.strip().lower().replace(" ", ""): c for c in columns}
    for cand in candidates:
        key = cand.replace(" ", "")
        if key in normalized:
            return normalized[key]
    # Teilstring-Suche als Fallback (z. B. "Umsatz brutto (EUR)")
    for col in columns:
        col_norm = col.strip().lower()
        for cand in candidates:
            if cand in col_norm:
                return col
    return None


def _resolve_column(df: pd.DataFrame, source: str, field: str, candidates: list[str]) -> str:
    override = COLUMN_OVERRIDES.get(source, {}).get(field)
    if override:
        if override not in df.columns:
            raise ValueError(
                f"Spalte '{override}' (Override für '{field}') nicht im {source}-Export gefunden. "
                f"Vorhandene Spalten: {list(df.columns)}"
            )
        return override
    found = _find_column(list(df.columns), candidates)
    if not found:
        raise ValueError(
            f"Konnte Spalte für '{field}' im {source}-Export nicht automatisch erkennen. "
            f"Vorhandene Spalten: {list(df.columns)}. "
            f"Trage den exakten Spaltennamen in config.py unter "
            f"COLUMN_OVERRIDES['{source}']['{field}'] ein."
        )
    return found


def _read_csv_flexible(path) -> pd.DataFrame:
    # sep=None + engine="python" erkennt automatisch ',' oder ';' als Trennzeichen
    return pd.read_csv(path, sep=None, engine="python")


def _to_number(series: pd.Series) -> pd.Series:
    """Wandelt deutsch formatierte Zahlen (1.234,56) in float um."""
    cleaned = series.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def load_orderbird(path) -> pd.DataFrame:
    """Lädt den Orderbird Kassenbuch-CSV-Export.

    Rückgabe: DataFrame mit Spalten ['datum', 'umsatz'], ein Wert pro Tag
    (mehrere Buchungen desselben Tages werden aufsummiert).
    """
    df = _read_csv_flexible(path)
    date_col = _resolve_column(df, "orderbird", "datum", DATE_CANDIDATES)
    amount_col = _resolve_column(df, "orderbird", "umsatz", AMOUNT_CANDIDATES)

    out = df[[date_col, amount_col]].copy()
    out.columns = ["datum", "umsatz"]
    out["datum"] = pd.to_datetime(out["datum"], dayfirst=True, errors="coerce")
    out["umsatz"] = _to_number(out["umsatz"])
    out = out.dropna(subset=["datum"])
    out = out.groupby("datum", as_index=False)["umsatz"].sum()
    return out.sort_values("datum").reset_index(drop=True)


def load_aplano(path) -> pd.DataFrame:
    """Lädt den Aplano Auswertungs-Export (CSV).

    Rückgabe: DataFrame mit Spalten ['datum', 'personalkosten', 'stunden'],
    pro Tag aufsummiert über alle (stundenbasiert bezahlten) Mitarbeiter.
    Fixgehälter der Geschäftsführung stehen nicht in Aplano, sondern in config.py
    (siehe GESCHAEFTSFUEHRUNG) und werden erst in metrics.py hinzugerechnet.

    Enthält der Export keine direkte Kostenspalte, aber Stunden + Stundenlohn,
    werden die Personalkosten daraus berechnet (Stunden * Stundenlohn).
    """
    df = _read_csv_flexible(path)

    date_col = _resolve_column(df, "aplano", "datum", DATE_CANDIDATES)
    hours_col = _find_column(list(df.columns), HOURS_CANDIDATES)
    cost_col = _find_column(list(df.columns), COST_CANDIDATES)
    wage_col = _find_column(list(df.columns), WAGE_CANDIDATES)

    out = df.copy()
    out["datum"] = pd.to_datetime(out[date_col], dayfirst=True, errors="coerce")

    if cost_col:
        out["personalkosten"] = _to_number(out[cost_col])
    elif hours_col and wage_col:
        out["personalkosten"] = _to_number(out[hours_col]) * _to_number(out[wage_col])
    else:
        raise ValueError(
            "Konnte weder eine Kostenspalte noch Stunden+Stundenlohn im Aplano-Export finden. "
            f"Vorhandene Spalten: {list(df.columns)}. Trage die passenden Spaltennamen in "
            "config.py unter COLUMN_OVERRIDES['aplano'] ein (z. B. 'kosten' oder 'stunden'/'stundenlohn')."
        )

    out["stunden"] = _to_number(out[hours_col]) if hours_col else pd.NA

    out = out.dropna(subset=["datum"])
    grouped = out.groupby("datum", as_index=False).agg(
        personalkosten=("personalkosten", "sum"),
        stunden=("stunden", "sum"),
    )
    grouped = grouped.rename(columns={"personalkosten": "personalkosten_variabel"})
    return grouped.sort_values("datum").reset_index(drop=True)


def load_wareneinsatz(path) -> pd.DataFrame:
    """Lädt einen Wareneinsatz-Export (z. B. manuell gepflegte Tabelle mit Wareneinkauf
    pro Tag/Lieferung).

    Rückgabe: DataFrame mit Spalten ['datum', 'wareneinsatz'], pro Tag aufsummiert.
    """
    df = _read_csv_flexible(path)
    date_col = _resolve_column(df, "wareneinsatz", "datum", DATE_CANDIDATES)
    amount_col = _resolve_column(df, "wareneinsatz", "wareneinsatz", WARENEINSATZ_CANDIDATES)

    out = df[[date_col, amount_col]].copy()
    out.columns = ["datum", "wareneinsatz"]
    out["datum"] = pd.to_datetime(out["datum"], dayfirst=True, errors="coerce")
    out["wareneinsatz"] = _to_number(out["wareneinsatz"])
    out = out.dropna(subset=["datum"])
    out = out.groupby("datum", as_index=False)["wareneinsatz"].sum()
    return out.sort_values("datum").reset_index(drop=True)


def load_wareneingang(path) -> pd.DataFrame:
    """Lädt einen Wareneingang-Export/Manuell gepflegte CSV mit Lieferungen je Zutat
    (z. B. abgetippt aus Lieferantenrechnungen).

    Erwartete Spalten (Namen werden automatisch erkannt): Datum, Zutat, Menge, Preis
    (Preis = Gesamtpreis der jeweiligen Lieferposition, nicht Einzelpreis).

    Rückgabe: DataFrame mit Spalten ['datum', 'zutat', 'menge', 'preis'], je Tag und
    Zutat aufsummiert (falls mehrere Lieferungen derselben Zutat am selben Tag erfasst wurden).
    """
    df = _read_csv_flexible(path)
    date_col = _resolve_column(df, "wareneingang", "datum", DATE_CANDIDATES)
    zutat_col = _resolve_column(df, "wareneingang", "zutat", ZUTAT_CANDIDATES)
    menge_col = _resolve_column(df, "wareneingang", "menge", MENGE_CANDIDATES)
    preis_col = _resolve_column(df, "wareneingang", "preis", PREIS_CANDIDATES)

    out = df[[date_col, zutat_col, menge_col, preis_col]].copy()
    out.columns = ["datum", "zutat", "menge", "preis"]
    out["datum"] = pd.to_datetime(out["datum"], dayfirst=True, errors="coerce")
    out["zutat"] = out["zutat"].astype(str).str.strip()
    out["menge"] = _to_number(out["menge"])
    out["preis"] = _to_number(out["preis"])
    out = out.dropna(subset=["datum"])
    out = out.groupby(["datum", "zutat"], as_index=False).agg(
        menge=("menge", "sum"), preis=("preis", "sum")
    )
    return out.sort_values(["datum", "zutat"]).reset_index(drop=True)


def load_verkaufsmengen(path) -> pd.DataFrame:
    """Lädt die verkauften Stückzahlen je Produkt und Tag, z. B. aus Orderbirds
    "Detaillierte Umsatzaufteilung" (MY orderbird → Berichte → Umsatzanalyse → Export als CSV).

    Erwartete Spalten (Namen werden automatisch erkannt): Datum, Produkt, Menge.

    Rückgabe: DataFrame mit Spalten ['datum', 'produkt', 'menge'], je Tag und Produkt
    aufsummiert.
    """
    df = _read_csv_flexible(path)
    date_col = _resolve_column(df, "verkaufsmengen", "datum", DATE_CANDIDATES)
    produkt_col = _resolve_column(df, "verkaufsmengen", "produkt", PRODUKT_CANDIDATES)
    menge_col = _resolve_column(df, "verkaufsmengen", "menge", MENGE_CANDIDATES)

    out = df[[date_col, produkt_col, menge_col]].copy()
    out.columns = ["datum", "produkt", "menge"]
    out["datum"] = pd.to_datetime(out["datum"], dayfirst=True, errors="coerce")
    out["produkt"] = out["produkt"].astype(str).str.strip()
    out["menge"] = _to_number(out["menge"])
    out = out.dropna(subset=["datum"])
    out = out.groupby(["datum", "produkt"], as_index=False)["menge"].sum()
    return out.sort_values(["datum", "produkt"]).reset_index(drop=True)
