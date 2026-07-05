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

from data_loader import (
    load_orderbird,
    load_aplano,
    load_wareneinsatz,
    load_wareneingang,
    load_verkaufsmengen,
    load_zutatenliste,
)
from metrics import build_daily_report, monthly_summary, weekly_summary
from exports import build_excel_report, build_pdf_report
from warenverlust import berechne_warenverlust
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

st.divider()
st.header("Warenwirtschaft & Warenverlust")
st.caption(
    "Zutatenliste, Rezepturen, Wareneingang und Inventur pflegen, um echten Warenverlust "
    "(Schwund) je Zutat zu berechnen: tatsächlicher Verbrauch (Anfangsbestand + "
    "Wareneingang − Endbestand) im Vergleich zum theoretischen Verbrauch laut Verkäufen "
    "und Rezepturen."
)

with st.expander("Zutaten verwalten"):
    zutaten_df = storage.list_zutaten()
    with st.form("zutat_form", clear_on_submit=True):
        zc1, zc2, zc3 = st.columns(3)
        neuer_zutat_name = zc1.text_input("Name (z. B. Kaffeebohnen)")
        neue_einheit = zc2.text_input("Einheit (z. B. kg, l, Stück)")
        neuer_preis = zc3.number_input(
            "Einkaufspreis pro Einheit (€)", min_value=0.0, step=0.1
        )
        if st.form_submit_button("Zutat speichern"):
            if neuer_zutat_name and neue_einheit:
                storage.add_zutat(neuer_zutat_name, neue_einheit, neuer_preis)
                st.success(f"Zutat '{neuer_zutat_name}' gespeichert.")
                st.rerun()
            else:
                st.warning("Name und Einheit sind Pflichtfelder.")

    st.caption(
        "Viele Zutaten auf einmal? Statt einzeln einzutippen, kannst du auch eine "
        "Warenliste als CSV hochladen (Spalten: Name, Einheit, Einkaufspreis)."
    )
    zutatenliste_file = st.file_uploader(
        "Zutatenliste hochladen (CSV)", type=["csv"], key="zutatenliste_upload"
    )
    if zutatenliste_file:
        try:
            storage.save_zutatenliste(load_zutatenliste(zutatenliste_file))
            st.success("Zutatenliste importiert.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    if not zutaten_df.empty:
        st.dataframe(zutaten_df, use_container_width=True)
        loesch_zutat = st.selectbox(
            "Zutat löschen", ["(keine Auswahl)"] + zutaten_df["name"].tolist()
        )
        if loesch_zutat != "(keine Auswahl)" and st.button("Ausgewählte Zutat löschen"):
            storage.delete_zutat(loesch_zutat)
            st.success(f"Zutat '{loesch_zutat}' gelöscht.")
            st.rerun()
    else:
        st.info("Noch keine Zutaten angelegt.")

with st.expander("Rezepturen verwalten"):
    zutaten_df = storage.list_zutaten()
    if zutaten_df.empty:
        st.info("Bitte zuerst mindestens eine Zutat unter 'Zutaten verwalten' anlegen.")
    else:
        with st.form("rezeptur_form", clear_on_submit=True):
            rc1, rc2, rc3 = st.columns(3)
            produkt_name = rc1.text_input(
                "Produkt (Name wie im Orderbird-Export, z. B. 'Cappuccino')"
            )
            zutat_wahl = rc2.selectbox("Zutat", zutaten_df["name"].tolist())
            menge_pro_einheit = rc3.number_input(
                "Menge pro verkaufter Einheit", min_value=0.0, step=0.01, format="%.3f"
            )
            if st.form_submit_button("Zeile zur Rezeptur hinzufügen"):
                if produkt_name:
                    storage.add_rezeptur_zeile(produkt_name, zutat_wahl, menge_pro_einheit)
                    st.success(f"'{zutat_wahl}' zur Rezeptur von '{produkt_name}' hinzugefügt.")
                    st.rerun()
                else:
                    st.warning("Produktname ist ein Pflichtfeld.")

        rezepturen_df = storage.list_rezepturen()
        if not rezepturen_df.empty:
            st.dataframe(rezepturen_df, use_container_width=True)
            rezeptur_optionen = {
                f"#{zeile.id}: {zeile.produkt} – {zeile.zutat} ({zeile.menge_pro_einheit})": zeile.id
                for zeile in rezepturen_df.itertuples()
            }
            rezeptur_auswahl = st.selectbox(
                "Zeile löschen", ["(keine Auswahl)"] + list(rezeptur_optionen.keys())
            )
            if rezeptur_auswahl != "(keine Auswahl)" and st.button(
                "Ausgewählte Rezeptur-Zeile löschen"
            ):
                storage.delete_rezeptur_zeile(rezeptur_optionen[rezeptur_auswahl])
                st.success("Zeile gelöscht.")
                st.rerun()
        else:
            st.info("Noch keine Rezepturen hinterlegt.")

with st.expander("Wareneingang & Verkaufsmengen hochladen"):
    wc1, wc2 = st.columns(2)
    with wc1:
        wareneingang_file = st.file_uploader(
            "Wareneingang (CSV: Datum, Zutat, Menge, Preis)",
            type=["csv"],
            key="wareneingang_upload",
        )
        if wareneingang_file:
            try:
                storage.save_wareneingang(load_wareneingang(wareneingang_file))
                st.success("Wareneingang gespeichert.")
            except ValueError as e:
                st.error(str(e))
    with wc2:
        verkaufsmengen_file = st.file_uploader(
            "Verkaufsmengen (CSV: Datum, Produkt, Menge) – aus Orderbirds "
            "Umsatzanalyse-Export (MY orderbird → Berichte → Umsatzanalyse → CSV)",
            type=["csv"],
            key="verkaufsmengen_upload",
        )
        if verkaufsmengen_file:
            try:
                storage.save_verkaufsmengen(load_verkaufsmengen(verkaufsmengen_file))
                st.success("Verkaufsmengen gespeichert.")
            except ValueError as e:
                st.error(str(e))

with st.expander("Inventur eintragen"):
    zutaten_df = storage.list_zutaten()
    if zutaten_df.empty:
        st.info("Bitte zuerst mindestens eine Zutat unter 'Zutaten verwalten' anlegen.")
    else:
        with st.form("inventur_form"):
            inventur_datum = st.date_input("Stichtag der Zählung")
            bestand_werte = {}
            for zeile in zutaten_df.itertuples():
                bestand_werte[zeile.name] = st.number_input(
                    f"{zeile.name} ({zeile.einheit})",
                    min_value=0.0,
                    step=0.1,
                    key=f"inventur_{zeile.name}",
                )
            if st.form_submit_button("Inventur speichern"):
                for zutat, bestand in bestand_werte.items():
                    storage.save_inventur_zeile(pd.Timestamp(inventur_datum), zutat, bestand)
                st.success(f"Inventur zum {inventur_datum} gespeichert.")
                st.rerun()

    inventur_df = storage.load_inventur()
    if not inventur_df.empty:
        st.caption("Bisher erfasste Stichtage:")
        st.dataframe(
            inventur_df.pivot(index="datum", columns="zutat", values="bestand"),
            use_container_width=True,
        )

st.subheader("Warenverlust")
warenverlust_ergebnis = berechne_warenverlust(
    storage.list_zutaten(),
    storage.list_rezepturen(),
    storage.load_wareneingang(),
    storage.load_inventur(),
    storage.load_verkaufsmengen(),
)
if not warenverlust_ergebnis["ok"]:
    st.info(warenverlust_ergebnis["grund"])
else:
    st.caption(
        f"Zeitraum: {warenverlust_ergebnis['datum_von'].strftime('%d.%m.%Y')} – "
        f"{warenverlust_ergebnis['datum_bis'].strftime('%d.%m.%Y')} "
        "(zwischen den letzten zwei Inventur-Stichtagen)"
    )
    warenverlust_tabelle = warenverlust_ergebnis["tabelle"]
    st.dataframe(warenverlust_tabelle, use_container_width=True)
    gesamtverlust_euro = warenverlust_tabelle["warenverlust_euro"].sum(skipna=True)
    st.metric("Warenverlust gesamt im Zeitraum (€)", f"{gesamtverlust_euro:,.2f} €")
