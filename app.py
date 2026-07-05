"""Gastro Pilot – MVP-Dashboard (Schritt 1: eigenes Café validieren).

Start:
    streamlit run app.py

Lädt einen Orderbird-Kassenbuch-Export, einen Aplano-Auswertungs-Export und optional
einen Wareneinsatz-Export hoch, führt alles pro Tag zusammen und zeigt Umsatz,
Personalkosten (inkl. Geschäftsführung), Fixkosten, Wareneinsatz, den Vorwochenvergleich
und regelbasierte Empfehlungen an.
"""

import pandas as pd
import streamlit as st

from data_loader import load_orderbird, load_aplano, load_wareneinsatz
from metrics import build_daily_report, monthly_summary, weekly_summary
from exports import build_excel_report, build_pdf_report
import storage
from config import (
    FIXED_COSTS_MONTHLY,
    GESCHAEFTSFUEHRUNG,
    PERSONALKOSTENQUOTE_WARNUNG,
    WARENEINSATZQUOTE_WARNUNG,
)

storage.init_db()

st.set_page_config(page_title="Gastro Pilot – MVP", layout="wide")
st.title("Gastro Pilot – MVP-Cockpit")
st.caption(
    "Kennzahlen-Zusammenführung aus Orderbird (Umsatz), Aplano (Personalkosten) "
    "und Wareneinsatz"
)
st.caption(
    "Hochgeladene Daten werden lokal in `gastro_pilot.db` gespeichert – du musst nicht "
    "bei jedem Start alles neu hochladen, nur neue Tage ergänzen."
)

col1, col2, col3 = st.columns(3)
with col1:
    orderbird_file = st.file_uploader("Orderbird Kassenbuch-Export (CSV)", type=["csv"])
with col2:
    aplano_file = st.file_uploader("Aplano Auswertungs-Export (CSV)", type=["csv"])
with col3:
    wareneinsatz_file = st.file_uploader(
        "Wareneinsatz-Export (CSV, optional)", type=["csv"]
    )

with st.expander("Aktuelle Einstellungen (config.py)"):
    st.write("Monatliche Fixkosten (ohne Personal):", FIXED_COSTS_MONTHLY)
    gf_summe = GESCHAEFTSFUEHRUNG["Anzahl"] * GESCHAEFTSFUEHRUNG["Fixgehalt_pro_Person_Monat"]
    st.write(
        f"Geschäftsführung: {GESCHAEFTSFUEHRUNG['Anzahl']} x "
        f"{GESCHAEFTSFUEHRUNG['Fixgehalt_pro_Person_Monat']:,.2f} € = {gf_summe:,.2f} € / Monat"
    )
    st.write("Warnschwelle Personalkostenquote:", f"{PERSONALKOSTENQUOTE_WARNUNG:.0%}")
    st.write("Warnschwelle Wareneinsatzquote:", f"{WARENEINSATZQUOTE_WARNUNG:.0%}")
    st.divider()
    st.caption("Gespeicherte Daten (gastro_pilot.db) unwiderruflich löschen:")
    zuruecksetzen_bestaetigt = st.checkbox("Ja, ich will alle gespeicherten Daten löschen")
    if st.button("Gespeicherte Daten löschen", disabled=not zuruecksetzen_bestaetigt):
        storage.reset_all()
        st.success("Gespeicherte Daten wurden gelöscht.")
        st.rerun()

try:
    if orderbird_file:
        storage.save_umsatz(load_orderbird(orderbird_file))
    if aplano_file:
        storage.save_personal(load_aplano(aplano_file))
    if wareneinsatz_file:
        storage.save_wareneinsatz(load_wareneinsatz(wareneinsatz_file))
except ValueError as e:
    st.error(str(e))
    st.stop()

umsatz_df = storage.load_umsatz()
personal_df = storage.load_personal()
wareneinsatz_df = storage.load_wareneinsatz()
wareneinsatz_df = wareneinsatz_df if not wareneinsatz_df.empty else None

if not umsatz_df.empty and not personal_df.empty:
    daily = build_daily_report(umsatz_df, personal_df, wareneinsatz_df)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Umsatz gesamt", f"{daily['umsatz'].sum():,.2f} €")
    k2.metric("Personalkosten gesamt", f"{daily['personalkosten'].sum():,.2f} €")
    k3.metric("davon Geschäftsführung", f"{daily['personalkosten_geschaeftsfuehrung'].sum():,.2f} €")
    k4.metric("Fixkosten (Zeitraum)", f"{daily['fixkosten'].sum():,.2f} €")
    gesamtquote = daily["personalkosten"].sum() / daily["umsatz"].sum() if daily["umsatz"].sum() else 0
    k5.metric("Ø Personalkostenquote", f"{gesamtquote:.1%}")

    if wareneinsatz_df is not None:
        wk1, wk2 = st.columns(2)
        wk1.metric("Wareneinsatz gesamt", f"{daily['wareneinsatz'].sum():,.2f} €")
        we_quote = daily["wareneinsatz"].sum() / daily["umsatz"].sum() if daily["umsatz"].sum() else 0
        wk2.metric("Ø Wareneinsatzquote", f"{we_quote:.1%}")

    st.subheader("Vorwochenvergleich")
    weekly = weekly_summary(daily)
    if len(weekly) >= 2:
        letzte = weekly.iloc[-1]
        vk1, vk2, vk3 = st.columns(3)
        vk1.metric(
            "Umsatz diese Woche",
            f"{letzte['umsatz']:,.2f} €",
            f"{letzte['umsatz_delta_vorwoche']:+.1%}" if pd.notna(letzte["umsatz_delta_vorwoche"]) else None,
        )
        vk2.metric(
            "Personalkosten diese Woche",
            f"{letzte['personalkosten']:,.2f} €",
            f"{letzte['personalkosten_delta_vorwoche']:+.1%}"
            if pd.notna(letzte["personalkosten_delta_vorwoche"])
            else None,
        )
        vk3.metric(
            "Personalkostenquote diese Woche",
            f"{letzte['personalkostenquote']:.1%}",
            f"{letzte['personalkostenquote_delta_vorwoche'] * 100:+.1f} Pp"
            if pd.notna(letzte["personalkostenquote_delta_vorwoche"])
            else None,
        )
        st.dataframe(weekly, use_container_width=True)
    else:
        st.info(
            "Für einen Vorwochenvergleich werden Daten aus mindestens zwei Kalenderwochen "
            "benötigt. Lade einen längeren Zeitraum hoch, um diese Ansicht zu sehen."
        )

    st.subheader("Tagesübersicht")
    spalten = [
        "datum",
        "umsatz",
        "personalkosten",
        "personalkosten_geschaeftsfuehrung",
        "fixkosten",
        "personalkostenquote",
    ]
    if wareneinsatz_df is not None:
        spalten += ["wareneinsatz", "wareneinsatzquote"]
    spalten += ["ergebnis_vor_weiteren_kosten", "empfehlung"]
    st.dataframe(daily[spalten], use_container_width=True)

    st.subheader("Umsatz vs. Personalkosten")
    st.line_chart(daily.set_index("datum")[["umsatz", "personalkosten"]])

    st.subheader("Personalkostenquote im Zeitverlauf")
    st.line_chart(daily.set_index("datum")[["personalkostenquote"]])

    if wareneinsatz_df is not None:
        st.subheader("Wareneinsatzquote im Zeitverlauf")
        st.line_chart(daily.set_index("datum")[["wareneinsatzquote"]])

    warnungen = daily[daily["personalkostenquote"] > PERSONALKOSTENQUOTE_WARNUNG]
    if not warnungen.empty:
        st.subheader("Tage mit Warnung: Personalkostenquote")
        st.dataframe(
            warnungen[["datum", "personalkostenquote", "empfehlung"]], use_container_width=True
        )

    if wareneinsatz_df is not None:
        we_warnungen = daily[daily["wareneinsatzquote"] > WARENEINSATZQUOTE_WARNUNG]
        if not we_warnungen.empty:
            st.subheader("Tage mit Warnung: Wareneinsatzquote")
            st.dataframe(
                we_warnungen[["datum", "wareneinsatzquote", "empfehlung_wareneinsatz"]],
                use_container_width=True,
            )

    st.subheader("Monatsübersicht")
    monthly = monthly_summary(daily)
    st.dataframe(monthly, use_container_width=True)

    st.subheader("Export")
    st.caption("Zum Weiterleiten an den Steuerberater oder zur eigenen Ablage.")
    zeitraum_von = daily["datum"].min().strftime("%d.%m.%Y")
    zeitraum_bis = daily["datum"].max().strftime("%d.%m.%Y")

    ex1, ex2 = st.columns(2)
    with ex1:
        excel_bytes = build_excel_report(daily, weekly, monthly)
        st.download_button(
            "Excel-Export herunterladen (.xlsx)",
            data=excel_bytes,
            file_name=f"gastro_pilot_report_{daily['datum'].max().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with ex2:
        pdf_bytes = build_pdf_report(monthly, weekly, zeitraum_von, zeitraum_bis)
        st.download_button(
            "PDF-Bericht herunterladen (.pdf)",
            data=pdf_bytes,
            file_name=f"gastro_pilot_bericht_{daily['datum'].max().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf",
        )
else:
    st.info(
        "Noch keine gespeicherten Daten vorhanden. Bitte mindestens den Orderbird- und "
        "den Aplano-Export hochladen, um das Dashboard zu sehen. Der Wareneinsatz-Export "
        "ist optional. Einmal hochgeladene Daten bleiben für künftige Starts gespeichert."
    )
    st.markdown(
        "Falls die Spalten deines Exports nicht automatisch erkannt werden, trage die "
        "exakten Spaltennamen in `config.py` unter `COLUMN_OVERRIDES` ein."
    )
