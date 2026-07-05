"""Berechnet den Warenverlust je Zutat zwischen zwei Inventur-Stichtagen.

Grundidee: Der tatsächliche Verbrauch einer Zutat (Anfangsbestand + Wareneingang -
Endbestand) wird mit dem theoretischen Verbrauch verglichen, der sich aus den
verkauften Produktmengen und den hinterlegten Rezepturen ergibt. Die Differenz ist
der Warenverlust (Schwund, Diebstahl, großzügige Portionen, Fehlbuchungen o. Ä.).

Voraussetzung: mindestens zwei Inventur-Stichtage müssen erfasst sein. Es wird
immer der Zeitraum zwischen den beiden jüngsten Stichtagen ausgewertet.
"""

from __future__ import annotations
from typing import Optional

import pandas as pd


def berechne_warenverlust(
    zutaten_df: pd.DataFrame,
    rezepturen_df: pd.DataFrame,
    wareneingang_df: pd.DataFrame,
    inventur_df: pd.DataFrame,
    verkaufsmengen_df: pd.DataFrame,
) -> dict:
    """Gibt ein Dict zurück:
    - {"ok": False, "grund": "..."}, falls weniger als zwei Inventur-Stichtage vorliegen.
    - {"ok": True, "datum_von": ..., "datum_bis": ..., "tabelle": DataFrame}, sonst.

    Die Ergebnistabelle hat je Zutat: anfangsbestand, wareneingang, endbestand,
    tatsaechlicher_verbrauch, theoretischer_verbrauch, warenverlust_menge, einheit,
    warenverlust_euro (nur befüllt, wenn ein Einkaufspreis für die Zutat hinterlegt ist).
    """
    if inventur_df.empty:
        return {"ok": False, "grund": "Noch keine Inventur erfasst."}

    stichtage = sorted(inventur_df["datum"].unique())
    if len(stichtage) < 2:
        return {
            "ok": False,
            "grund": (
                "Es liegt erst ein Inventur-Stichtag vor. Für einen Warenverlust "
                "wird mindestens ein zweiter Zähltermin benötigt."
            ),
        }

    datum_von, datum_bis = stichtage[-2], stichtage[-1]

    anfangsbestand = (
        inventur_df[inventur_df["datum"] == datum_von].set_index("zutat")["bestand"]
    )
    endbestand = (
        inventur_df[inventur_df["datum"] == datum_bis].set_index("zutat")["bestand"]
    )

    if not wareneingang_df.empty:
        wareneingang_zeitraum = wareneingang_df[
            (wareneingang_df["datum"] > datum_von) & (wareneingang_df["datum"] <= datum_bis)
        ]
        wareneingang_je_zutat = wareneingang_zeitraum.groupby("zutat")["menge"].sum()
    else:
        wareneingang_je_zutat = pd.Series(dtype=float)

    theoretischer_verbrauch = pd.Series(dtype=float)
    if not verkaufsmengen_df.empty and not rezepturen_df.empty:
        verkaufsmengen_zeitraum = verkaufsmengen_df[
            (verkaufsmengen_df["datum"] > datum_von) & (verkaufsmengen_df["datum"] <= datum_bis)
        ]
        merged = verkaufsmengen_zeitraum.merge(rezepturen_df, on="produkt", how="inner")
        if not merged.empty:
            merged["verbrauch"] = merged["menge"] * merged["menge_pro_einheit"]
            theoretischer_verbrauch = merged.groupby("zutat")["verbrauch"].sum()

    zutaten_namen = set(zutaten_df["name"]) if not zutaten_df.empty else set()
    alle_zutaten = sorted(
        set(anfangsbestand.index)
        | set(endbestand.index)
        | set(wareneingang_je_zutat.index)
        | set(theoretischer_verbrauch.index)
        | zutaten_namen
    )

    tabelle = pd.DataFrame({"zutat": alle_zutaten}).set_index("zutat")
    tabelle["anfangsbestand"] = anfangsbestand.reindex(alle_zutaten)
    tabelle["wareneingang"] = wareneingang_je_zutat.reindex(alle_zutaten).fillna(0.0)
    tabelle["endbestand"] = endbestand.reindex(alle_zutaten)
    tabelle["tatsaechlicher_verbrauch"] = (
        tabelle["anfangsbestand"] + tabelle["wareneingang"] - tabelle["endbestand"]
    )
    tabelle["theoretischer_verbrauch"] = theoretischer_verbrauch.reindex(alle_zutaten).fillna(0.0)
    tabelle["warenverlust_menge"] = (
        tabelle["tatsaechlicher_verbrauch"] - tabelle["theoretischer_verbrauch"]
    )

    if not zutaten_df.empty:
        zutaten_info = zutaten_df.set_index("name")
        tabelle["einheit"] = zutaten_info["einheit"].reindex(alle_zutaten)
        tabelle["warenverlust_euro"] = tabelle["warenverlust_menge"] * zutaten_info[
            "einkaufspreis_pro_einheit"
        ].reindex(alle_zutaten)
    else:
        tabelle["einheit"] = None
        tabelle["warenverlust_euro"] = None

    tabelle = tabelle.reset_index().sort_values("warenverlust_euro", ascending=False, na_position="last")

    return {"ok": True, "datum_von": datum_von, "datum_bis": datum_bis, "tabelle": tabelle}
