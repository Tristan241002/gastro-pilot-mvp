"""Zentrale Einstellungen für das Gastro-Pilot-MVP-Dashboard.

Fixkosten, Löhne, Warnschwellen und (falls nötig) manuelle Spaltennamen-Zuordnungen
für die Orderbird-, Aplano- und Wareneinsatz-Exporte trägst du hier ein.
"""

# Monatliche Fixkosten deines Cafés OHNE Personalkosten (Miete, Energie, Versicherungen,
# Software/Abos, ...). Summe: 3.000 €. Passe die Aufteilung gern an deine echten Posten an.
FIXED_COSTS_MONTHLY = {
    "Miete": 2000.0,
    "Energie": 600.0,
    "Versicherungen": 200.0,
    "Software/Abos": 200.0,
}

# Fixgehälter der Geschäftsführung – bezahlt unabhängig von Stunden, taucht deshalb NICHT
# im Aplano-Stundenexport auf, sondern wird hier separat hinterlegt und wie die anderen
# Personalkosten anteilig auf die Tage verteilt.
GESCHAEFTSFUEHRUNG = {
    "Anzahl": 3,
    "Fixgehalt_pro_Person_Monat": 2500.0,
}

# Ab welcher Personalkostenquote (alle Personalkosten inkl. Geschäftsführung / Umsatz)
# soll gewarnt werden?
PERSONALKOSTENQUOTE_WARNUNG = 0.35  # 35 %

# Ab welcher Wareneinsatzquote (Wareneinsatz / Umsatz) soll gewarnt werden?
WARENEINSATZQUOTE_WARNUNG = 0.30  # 30 %

# Falls die automatische Spalten-Erkennung in data_loader.py fehlschlägt,
# trage hier die exakten Spaltennamen deines Exports ein, z. B.:
# COLUMN_OVERRIDES = {
#     "orderbird": {"datum": "Belegdatum", "umsatz": "Brutto"},
#     "aplano": {"datum": "Datum", "stunden": "Ist-Stunden", "kosten": "Lohnkosten"},
#     "wareneinsatz": {"datum": "Datum", "wareneinsatz": "Warenkosten"},
# }
COLUMN_OVERRIDES = {
    "orderbird": {},
    "aplano": {},
    "wareneinsatz": {},
    "wareneingang": {},
    "verkaufsmengen": {},
}
