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

gespeicherte_settings = storage.load_settings()

with st.expander("Einstellungen (Fixkosten, Gehälter, Warnschwellen)"):
    st.caption(
        "Wird lokal in `gastro_pilot.db` gespeichert und bei jedem Start automatisch "
        "geladen – kein Bearbeiten von config.py nötig."
    )
    with st.form("einstellungen_form"):
        st.markdown("**Monatliche Fixkosten (ohne Personal)**")
        c1, c2, c3, c4 = st.columns(4)
        miete = c1.number_input(
            "Miete (€)", min_value=0.0, value=float(gespeicherte_settings["miete"]), step=50.0
        )
        energie = c2.number_input(
            "Energie (€)", min_value=0.0, value=float(gespeicherte_settings["energie"]), step=50.0
        )
        versicherungen = c3.number_input(
            "Versicherungen (€)",
            min_value=0.0,
            value=float(gespeicherte_settings["versicherungen"]),
            step=50.0,
        )
        software_abos = c4.number_input(
            "Software/Abos (€)",
            min_value=0.0,
            value=float(gespeicherte_settings["software_abos"]),
            step=50.0,
        )

        st.markdown("**Geschäftsführung (Fixgehalt, nicht in Aplano erfasst)**")
        c5, c6 = st.columns(2)
        gf_anzahl = c5.number_input(
            "Anzahl Geschäftsführer/innen",
            min_value=0,
            value=int(gespeicherte_settings["gf_anzahl"]),
            step=1,
        )
        gf_fixgehalt = c6.number_input(
            "Fixgehalt pro Person/Monat (€)",
            min_value=0.0,
            value=float(gespeicherte_settings["gf_fixgehalt"]),
            step=100.0,
        )

        st.markdown("**Warnschwellen**")
        c7, c8 = st.columns(2)
        personalkostenquote_warnung_pct = c7.number_input(
            "Personalkostenquote-Warnung (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(gespeicherte_settings["personalkostenquote_warnung"]) * 100,
            step=1.0,
        )
        wareneinsatzquote_warnung_pct = c8.number_input(
            "Wareneinsatzquote-Warnung (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(gespeicherte_settings["wareneinsatzquote_warnung"]) * 100,
            step=1.0,
        )

        if st.form_submit_button("Einstellungen speichern"):
            storage.save_settings(
                {
                    "miete": miete,
                    "energie": energie,
                    "versicherungen": versicherungen,
                    "software_abos": software_abos,
                    "gf_anzahl": gf_anzahl,
                    "gf_fixgehalt": gf_fixgehalt,
                    "personalkostenquote_warnung": personalkostenquote_warnung_pct / 100,
                    "wareneinsatzquote_warnung": wareneinsatzquote_warnung_pct / 100,
                }
            )
            st.success("Einstellungen gespeichert.")
            st.rerun()

    st.divider()
    st.caption("Gespeicherte Daten (gastro_pilot.db) unwiderruflich löschen:")
    zuruecksetzen_bestaetigt = st.checkbox("Ja, ich will alle gespeicherten Daten löschen")
    if st.button("Gespeicherte Daten löschen", disabled=not zuruecksetzen_bestaetigt):
        storage.reset_all()
        st.success("Gespeicherte Daten (Umsatz/Personal/Wareneinsatz) wurden gelöscht.")
        st.rerun()

fixkosten_monatlich = (
    gespeicherte_settings["miete"]
    + gespeicherte_settings["energie"]
    + gespeicherte_settings["versicherungen"]
    + gespeicherte_settings["software_abos"]
)
gf_summe_monatlich = gespeicherte_settings["gf_anzahl"] * gespeicherte_settings["gf_fixgehalt"]
personalkostenquote_warnung = gespeicherte_settings["personalkostenquote_warnung"]
wareneinsatzquote_warnung = gespeicherte_settings["wareneinsatzquote_warnung"]

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
    daily = build_daily_report(
        umsatz_df,
        personal_df,
        wareneinsatz_df,
        fixkosten_monatlich=fixkosten_monatlich,
        gf_summe_monatlich=gf_summe_monatlich,
        personalkostenquote_warnung=personalkostenquote_warnung,
        wareneinsatzquote_warnung=wareneinsatzquote_warnung,
    )

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

    warnungen = daily[daily["personalkostenquote"] > personalkostenquote_warnung]
    if not warnungen.empty:
        st.subheader("Tage mit Warnung: Personalkostenquote")
        st.dataframe(
            warnungen[["datum", "personalkostenquote", "empfehlung"]], use_container_width=True
        )

    if wareneinsatz_df is not None:
        we_warnungen = daily[daily["wareneinsatzquote"] > wareneinsatzquote_warnung]
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
