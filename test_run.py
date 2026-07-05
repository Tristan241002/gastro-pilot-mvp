"""Schneller Funktionstest ohne Streamlit-Server: prüft, ob Loader und Metriken
(inkl. Wareneinsatz und Vorwochenvergleich) mit den Beispieldaten in sample_data/
korrekt durchlaufen."""

from data_loader import load_orderbird, load_aplano, load_wareneinsatz
from metrics import build_daily_report, monthly_summary, weekly_summary

umsatz = load_orderbird("sample_data/orderbird_sample.csv")
personal = load_aplano("sample_data/aplano_sample.csv")
wareneinsatz = load_wareneinsatz("sample_data/wareneinsatz_sample.csv")

print("== Umsatz (erste 3 Tage) ==")
print(umsatz.head(3))
print("\n== Personalkosten (erste 3 Tage) ==")
print(personal.head(3))
print("\n== Wareneinsatz (erste 3 Tage) ==")
print(wareneinsatz.head(3))

daily = build_daily_report(umsatz, personal, wareneinsatz)
print("\n== Tagesreport (erste 5 Tage) ==")
print(
    daily[
        [
            "datum",
            "umsatz",
            "personalkosten",
            "personalkosten_geschaeftsfuehrung",
            "wareneinsatz",
            "personalkostenquote",
            "wareneinsatzquote",
            "empfehlung",
        ]
    ]
    .head(5)
    .to_string(index=False)
)

print("\n== Monatsübersicht ==")
print(monthly_summary(daily).to_string(index=False))

print("\n== Vorwochenvergleich ==")
print(weekly_summary(daily).to_string(index=False))
