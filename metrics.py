"""Berechnet die Kernkennzahlen aus Umsatz-, Personal- und Wareneinsatzdaten und erzeugt
regelbasierte Handlungsempfehlungen.

Bewusst noch ohne Machine Learning / LLM (siehe Konzept, Abschnitt 4.3 und Roadmap-
Schritt "Nächste Schritte"): erst wenn die einfache, regelbasierte Version im Alltag
echten Mehrwert zeigt, lohnt sich der nächste Ausbauschritt.
"""

from __future__ import annotations
import calendar
from typing import Optional

import pandas as pd

from config import (
    FIXED_COSTS_MONTHLY,
    GESCHAEFTSFUEHRUNG,
    PERSONALKOSTENQUOTE_WARNUNG,
    WARENEINSATZQUOTE_WARNUNG,
)


def _tage_im_monat(datum: pd.Timestamp) -> int:
    return calendar.monthrange(datum.year, datum.month)[1]


def _fixkosten_pro_tag(datum: pd.Timestamp, fixkosten_monatlich: float) -> float:
    """Verteilt die monatlichen Fixkosten (ohne Personal) gleichmäßig auf die Tage
    des jeweiligen Monats."""
    return fixkosten_monatlich / _tage_im_monat(datum)


def _geschaeftsfuehrung_pro_tag(datum: pd.Timestamp, gf_summe_monatlich: float) -> float:
    """Verteilt die Fixgehälter der Geschäftsführung gleichmäßig auf die Tage
    des jeweiligen Monats (steht nicht im Aplano-Export)."""
    return gf_summe_monatlich / _tage_im_monat(datum)


def _empfehlung_personalkosten(quote: Optional[float], schwelle: float) -> str:
    if quote is None or pd.isna(quote):
        return "Kein Umsatz erfasst – Tag prüfen."
    if quote > schwelle:
        return (
            f"Personalkostenquote {quote:.0%} liegt über der Schwelle von "
            f"{schwelle:.0%} – Personaleinsatz an diesem Tag prüfen."
        )
    return "Im grünen Bereich."


def _empfehlung_wareneinsatz(quote: Optional[float], schwelle: float) -> str:
    if quote is None or pd.isna(quote):
        return ""
    if quote > schwelle:
        return (
            f"Wareneinsatzquote {quote:.0%} liegt über der Schwelle von "
            f"{schwelle:.0%} – Einkauf/Rezepturen/Preise prüfen."
        )
    return "Im grünen Bereich."


def build_daily_report(
    umsatz_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    wareneinsatz_df: Optional[pd.DataFrame] = None,
    fixkosten_monatlich: float = sum(FIXED_COSTS_MONTHLY.values()),
    gf_summe_monatlich: float = GESCHAEFTSFUEHRUNG["Anzahl"] * GESCHAEFTSFUEHRUNG["Fixgehalt_pro_Person_Monat"],
    personalkostenquote_warnung: float = PERSONALKOSTENQUOTE_WARNUNG,
    wareneinsatzquote_warnung: float = WARENEINSATZQUOTE_WARNUNG,
) -> pd.DataFrame:
    """Führt Umsatz-, Personal- und (optional) Wareneinsatzdaten pro Tag zusammen und
    berechnet Kennzahlen. Die Fixgehälter der Geschäftsführung werden hier zu den
    variablen Aplano-Personalkosten addiert, damit die Personalkostenquote die
    tatsächlichen gesamten Personalkosten abbildet. Fixkosten, Geschäftsführer-Gehälter
    und Warnschwellen kommen standardmäßig aus config.py, können aber (z. B. über den
    Einstellungsbereich im Dashboard) überschrieben werden."""
    merged = pd.merge(umsatz_df, personal_df, on="datum", how="outer").sort_values("datum")
    merged["umsatz"] = merged["umsatz"].fillna(0.0)
    merged["personalkosten_variabel"] = merged["personalkosten_variabel"].fillna(0.0)

    merged["personalkosten_geschaeftsfuehrung"] = merged["datum"].apply(
        lambda d: _geschaeftsfuehrung_pro_tag(d, gf_summe_monatlich)
    )
    merged["personalkosten"] = (
        merged["personalkosten_variabel"] + merged["personalkosten_geschaeftsfuehrung"]
    )
    merged["fixkosten"] = merged["datum"].apply(
        lambda d: _fixkosten_pro_tag(d, fixkosten_monatlich)
    )

    if wareneinsatz_df is not None:
        merged = pd.merge(merged, wareneinsatz_df, on="datum", how="left")
        merged["wareneinsatz"] = merged["wareneinsatz"].fillna(0.0)
    else:
        merged["wareneinsatz"] = 0.0

    merged["personalkostenquote"] = merged.apply(
        lambda r: (r["personalkosten"] / r["umsatz"]) if r["umsatz"] else None, axis=1
    )
    merged["wareneinsatzquote"] = merged.apply(
        lambda r: (r["wareneinsatz"] / r["umsatz"]) if r["umsatz"] else None, axis=1
    )
    merged["ergebnis_vor_weiteren_kosten"] = (
        merged["umsatz"] - merged["personalkosten"] - merged["fixkosten"] - merged["wareneinsatz"]
    )
    merged["empfehlung"] = merged["personalkostenquote"].apply(
        lambda q: _empfehlung_personalkosten(q, personalkostenquote_warnung)
    )
    merged["empfehlung_wareneinsatz"] = merged["wareneinsatzquote"].apply(
        lambda q: _empfehlung_wareneinsatz(q, wareneinsatzquote_warnung)
    )
    return merged.reset_index(drop=True)


def monthly_summary(daily: pd.DataFrame) -> pd.DataFrame:
    df = daily.copy()
    df["monat"] = df["datum"].dt.to_period("M").astype(str)
    summary = df.groupby("monat").agg(
        umsatz=("umsatz", "sum"),
        personalkosten=("personalkosten", "sum"),
        fixkosten=("fixkosten", "sum"),
        wareneinsatz=("wareneinsatz", "sum"),
        ergebnis_vor_weiteren_kosten=("ergebnis_vor_weiteren_kosten", "sum"),
    )
    summary["personalkostenquote"] = summary["personalkosten"] / summary["umsatz"]
    summary["wareneinsatzquote"] = summary["wareneinsatz"] / summary["umsatz"]
    return summary.reset_index()


def weekly_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """Fasst die Kennzahlen pro ISO-Kalenderwoche zusammen und berechnet den
    Vorwochenvergleich (prozentuale Veränderung zur direkt vorherigen Woche)."""
    df = daily.copy()
    iso = df["datum"].dt.isocalendar()
    df["woche"] = iso["year"].astype(str) + "-KW" + iso["week"].astype(str).str.zfill(2)
    df["woche_start"] = df["datum"] - pd.to_timedelta(iso["day"] - 1, unit="D")

    summary = (
        df.groupby(["woche", "woche_start"])
        .agg(
            umsatz=("umsatz", "sum"),
            personalkosten=("personalkosten", "sum"),
            wareneinsatz=("wareneinsatz", "sum"),
        )
        .reset_index()
        .sort_values("woche_start")
    )
    summary["personalkostenquote"] = summary["personalkosten"] / summary["umsatz"]
    summary["wareneinsatzquote"] = summary["wareneinsatz"] / summary["umsatz"]

    # Umsatz/Personalkosten: relative Veränderung zur Vorwoche (in %).
    for spalte in ["umsatz", "personalkosten"]:
        vorwoche = summary[spalte].shift(1)
        summary[f"{spalte}_delta_vorwoche"] = (summary[spalte] - vorwoche) / vorwoche.replace(0, pd.NA)

    # Quoten sind selbst schon Prozentwerte: hier lieber die Differenz in Prozentpunkten
    # als eine "relative Veränderung einer Quote", die leicht missverständlich wäre.
    for spalte in ["personalkostenquote", "wareneinsatzquote"]:
        vorwoche = summary[spalte].shift(1)
        summary[f"{spalte}_delta_vorwoche"] = summary[spalte] - vorwoche

    return summary.drop(columns=["woche_start"]).reset_index(drop=True)
