"""Erstellt Excel- und PDF-Reports aus den berechneten Kennzahlen, z. B. zum
Weiterleiten an den Steuerberater oder zur eigenen Ablage."""

from __future__ import annotations
from datetime import datetime
from io import BytesIO

import pandas as pd
from fpdf import FPDF


def build_excel_report(daily: pd.DataFrame, weekly: pd.DataFrame, monthly: pd.DataFrame) -> bytes:
    """Baut eine Excel-Datei mit drei Tabellenblättern (Tagesübersicht,
    Vorwochenvergleich, Monatsübersicht) und gibt sie als Bytes zurück, z. B. für
    st.download_button."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        sheets = {
            "Tagesuebersicht": daily,
            "Vorwochenvergleich": weekly,
            "Monatsuebersicht": monthly,
        }
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            for i, col in enumerate(df.columns):
                max_len = df[col].astype(str).str.len().max()
                width = max(12, min(30, int(max_len if pd.notna(max_len) else 10) + 2))
                col_letter = chr(65 + i) if i < 26 else "A" + chr(65 + i - 26)
                worksheet.column_dimensions[col_letter].width = width

    return buffer.getvalue()


# Kurze, PDF-taugliche Spaltenüberschriften und welche Werte Prozentwerte sind.
_SPALTEN_KURZ = {
    "monat": "Monat",
    "woche": "Woche",
    "umsatz": "Umsatz (EUR)",
    "personalkosten": "Personal (EUR)",
    "fixkosten": "Fixkosten (EUR)",
    "wareneinsatz": "Wareneinsatz (EUR)",
    "ergebnis_vor_weiteren_kosten": "Ergebnis (EUR)",
    "personalkostenquote": "Personal-Quote",
    "wareneinsatzquote": "Waren-Quote",
    "umsatz_delta_vorwoche": "Umsatz Delta",
    "personalkosten_delta_vorwoche": "Personal Delta",
    "personalkostenquote_delta_vorwoche": "Personal-Quote Delta (Pp)",
    "wareneinsatzquote_delta_vorwoche": "Waren-Quote Delta (Pp)",
}
_PROZENT_SPALTEN = {
    "personalkostenquote",
    "wareneinsatzquote",
    "umsatz_delta_vorwoche",
    "personalkosten_delta_vorwoche",
}
_PROZENTPUNKT_SPALTEN = {
    "personalkostenquote_delta_vorwoche",
    "wareneinsatzquote_delta_vorwoche",
}


def _format_value(spalte: str, value) -> str:
    if pd.isna(value):
        return "-"
    if spalte in _PROZENT_SPALTEN:
        return f"{value:+.1%}" if spalte.endswith("delta_vorwoche") else f"{value:.1%}"
    if spalte in _PROZENTPUNKT_SPALTEN:
        return f"{value * 100:+.1f}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _pdf_table(pdf: FPDF, df: pd.DataFrame) -> None:
    if df.empty:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 8, "Keine Daten fuer diesen Zeitraum.", ln=True)
        return

    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = usable_width / max(len(df.columns), 1)

    pdf.set_font("Helvetica", "B", 8)
    for col in df.columns:
        pdf.cell(col_width, 7, _SPALTEN_KURZ.get(col, col)[:22], border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        for col in df.columns:
            text = _format_value(col, row[col])
            pdf.cell(col_width, 7, text[:22], border=1)
        pdf.ln()


def build_pdf_report(
    monthly: pd.DataFrame,
    weekly: pd.DataFrame,
    zeitraum_von: str,
    zeitraum_bis: str,
) -> bytes:
    """Baut einen kompakten PDF-Bericht mit Monats- und Wochenübersicht und gibt ihn
    als Bytes zurück, z. B. für st.download_button."""
    pdf = FPDF(orientation="L")  # Querformat, damit die Tabellen mehr Platz haben
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Gastro Pilot - Bericht", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Zeitraum: {zeitraum_von} bis {zeitraum_bis}", ln=True)
    pdf.cell(0, 7, f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Monatsuebersicht", ln=True)
    _pdf_table(pdf, monthly)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Vorwochenvergleich", ln=True)
    _pdf_table(pdf, weekly)

    return bytes(pdf.output())
