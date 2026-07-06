""
pdf_report.py
─────────────────────────────────────────────────────────────────────────────
Generates a multi-section PDF report for the Residual Capacity Platform.

Key design decisions
────────────────────
* Charts are rendered to PNG bytes via plotly's `write_image` (kaleido engine).
  No external wkhtmltopdf / weasyprint / pdfkit dependency is required.
* If kaleido is unavailable a graceful fallback message is inserted instead of
  crashing.
* The cover page is rendered ONCE (duplicate removed).
* Variable labels that follow the  Base-suffix  convention are displayed with
  Unicode subscripts in the PDF body text.
"""

from __future__ import annotations

import io
import re
import datetime
from typing import Any

import streamlit as st

# ── ReportLab imports ─────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus import Image as RLImage
from reportlab.pdfgen import canvas as rl_canvas

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#1A2B3C")
BLUE   = colors.HexColor("#1f4e79")
ORANGE = colors.HexColor("#e17000")
LGRAY  = colors.HexColor("#f4f6f9")
MGRAY  = colors.HexColor("#e2e6ea")
DGRAY  = colors.HexColor("#555555")
WHITE  = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm

# ── Unicode subscript helper (mirrors app.py) ─────────────────────────────────
_SUB_MAP = str.maketrans(
    "0123456789abcdefghijklmnopqrstuvwxyz",
    "₀₁₂₃₄₅₆₇₈₉ₐᵦ꜀ᵈₑ꜁ᵍₕᵢⱼₖₗₘₙₒₚ꜀ᵣₛₜᵤᵥ𝓌ₓᵧ𝓏",
)

def fmt_var(label: str) -> str:
    """Convert 'X-i' style labels to 'Xᵢ' using Unicode subscripts."""
    def _replace(m):
        base, sub = m.group(1), m.group(2)
        return base + sub.translate(_SUB_MAP)
    return re.sub(r'([A-Za-z_]+)-([0-9a-z]+)', _replace, label)


# ── Plotly → PNG bytes ────────────────────────────────────────────────────────
def _fig_to_png(fig, width_px: int = 900, height_px: int = 400) -> bytes | None:
    """
    Convert a Plotly figure to PNG bytes using kaleido.

    Returns None if kaleido is not installed or conversion fails, so the
    caller can insert a placeholder instead of crashing.
    """
    try:
        import plotly.io as pio  # noqa: PLC0415
        png_bytes = pio.to_image(fig, format="png", width=width_px, height=height_px, scale=2)
        return png_bytes
    except Exception:
        return None


def _rl_image(fig, max_width: float, max_height: float) -> RLImage | Paragraph | None:
    """
    Return a ReportLab Image flowable from a Plotly figure, scaled to fit.
    Falls back to a styled Paragraph if rendering fails.
    """
    if fig is None:
        return None

    png = _fig_to_png(fig)
    if png is None:
        styles = getSampleStyleSheet()
        warn_style = ParagraphStyle(
            "warn", parent=styles["Normal"],
            textColor=ORANGE, fontSize=9, leading=12,
        )
        return Paragraph(
            "⚠ Chart could not be rendered (kaleido not available).",
            warn_style,
        )

    buf = io.BytesIO(png)
    img = RLImage(buf)
    # Scale proportionally to fit within the allowed box
    scale = min(max_width / img.imageWidth, max_height / img.imageHeight, 1.0)
    img.drawWidth  = img.imageWidth  * scale
    img.drawHeight = img.imageHeight * scale
    return img


# ── Styles ────────────────────────────────────────────────────────────────────
def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"],
            fontSize=28, leading=34, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"],
            fontSize=12, leading=16, textColor=colors.HexColor("#90b8d8"),
            fontName="Helvetica", alignment=TA_CENTER,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta", parent=base["Normal"],
            fontSize=9, leading=13, textColor=colors.HexColor("#aac4e0"),
            fontName="Helvetica", alignment=TA_CENTER,
        ),
        "section_h": ParagraphStyle(
            "section_h", parent=base["Heading1"],
            fontSize=13, leading=17, textColor=BLUE,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4,
        ),
        "sub_h": ParagraphStyle(
            "sub_h", parent=base["Heading2"],
            fontSize=10, leading=14, textColor=NAVY,
            fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, leading=13, textColor=DGRAY,
            fontName="Helvetica",
        ),
        "kv_key": ParagraphStyle(
            "kv_key", parent=base["Normal"],
            fontSize=8, leading=11, textColor=DGRAY,
            fontName="Helvetica-Bold",
        ),
        "kv_val": ParagraphStyle(
            "kv_val", parent=base["Normal"],
            fontSize=8, leading=11, textColor=NAVY,
            fontName="Helvetica",
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"],
            fontSize=8, leading=11, textColor=DGRAY,
            fontName="Helvetica-Oblique", alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=7, leading=10, textColor=colors.HexColor("#aaaaaa"),
            fontName="Helvetica", alignment=TA_CENTER,
        ),
    }


# ── Page template callbacks ───────────────────────────────────────────────────
def _on_page(canv: rl_canvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Draw header rule + footer on every page except the cover."""
    if doc.page == 1:
        return
    canv.saveState()
    # Top rule
    canv.setStrokeColor(ORANGE)
    canv.setLineWidth(2)
    canv.line(MARGIN, PAGE_H - 1.4 * cm, PAGE_W - MARGIN, PAGE_H - 1.4 * cm)
    # Header text
    canv.setFont("Helvetica-Bold", 7)
    canv.setFillColor(BLUE)
    canv.drawString(MARGIN, PAGE_H - 1.1 * cm, "RESIDUAL CAPACITY PLATFORM")
    canv.setFont("Helvetica", 7)
    canv.setFillColor(DGRAY)
    canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.1 * cm,
                         f"Generated {datetime.date.today().strftime('%d %b %Y')}")
    # Footer rule
    canv.setStrokeColor(MGRAY)
    canv.setLineWidth(0.5)
    canv.line(MARGIN, 1.2 * cm, PAGE_W - MARGIN, 1.2 * cm)
    # Page number
    canv.setFont("Helvetica", 7)
    canv.setFillColor(colors.HexColor("#aaaaaa"))
    canv.drawCentredString(PAGE_W / 2, 0.7 * cm, f"Page {doc.page}")
    canv.restoreState()


# ── Cover page (drawn once via canvas, not as a flowable) ─────────────────────
def _draw_cover(canv: rl_canvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Paint the cover page background and text on page 1 only."""
    if doc.page != 1:
        return
    canv.saveState()
    # Dark gradient background (simulated with two rectangles)
    canv.setFillColor(colors.HexColor("#0f1e2d"))
    canv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canv.setFillColor(colors.HexColor("#1a3a5c"))
    canv.rect(0, PAGE_H * 0.35, PAGE_W, PAGE_H * 0.65, fill=1, stroke=0)
    # Orange accent bar
    canv.setFillColor(ORANGE)
    canv.rect(0, PAGE_H * 0.35 - 4, PAGE_W, 4, fill=1, stroke=0)
    # Title
    canv.setFont("Helvetica-Bold", 30)
    canv.setFillColor(WHITE)
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.62, "Residual Capacity Platform")
    # Subtitle
    canv.setFont("Helvetica", 13)
    canv.setFillColor(colors.HexColor("#90b8d8"))
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.57,
                           "Concrete Durability & Structural Capacity Report")
    # Version badge
    canv.setFillColor(ORANGE)
    canv.roundRect(PAGE_W / 2 - 22, PAGE_H * 0.52, 44, 16, 8, fill=1, stroke=0)
    canv.setFont("Helvetica-Bold", 9)
    canv.setFillColor(WHITE)
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.524, "v2.0")
    # Date
    canv.setFont("Helvetica", 9)
    canv.setFillColor(colors.HexColor("#aac4e0"))
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.47,
                           datetime.date.today().strftime("%d %B %Y"))
    canv.restoreState()


# ── KV table helper ───────────────────────────────────────────────────────────
def _kv_table(rows: list[tuple[str, Any]], styles: dict) -> Table:
    """Build a two-column key/value parameter table."""
    data = [[Paragraph(fmt_var(k), styles["kv_key"]),
             Paragraph(str(v),     styles["kv_val"])]
            for k, v in rows]
    col_w = (PAGE_W - 2 * MARGIN) / 2
    tbl = Table(data, colWidths=[col_w * 0.45, col_w * 0.55])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LGRAY]),
        ("GRID",       (0, 0), (-1, -1), 0.3, MGRAY),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


# ── DataFrame → ReportLab Table ───────────────────────────────────────────────
def _df_table(df, styles: dict, col_labels: list[str] | None = None) -> Table:
    """Convert a pandas DataFrame to a styled ReportLab Table."""
    import pandas as pd  # noqa: PLC0415

    if df is None or (hasattr(df, "empty") and df.empty):
        return Paragraph("No data available.", styles["body"])

    cols = col_labels or list(df.columns)
    header = [Paragraph(c, styles["kv_key"]) for c in cols]
    body_rows = [
        [Paragraph(str(row[c]), styles["kv_val"]) for c in df.columns]
        for _, row in df.iterrows()
    ]
    data = [header] + body_rows
    avail_w = PAGE_W - 2 * MARGIN
    col_w = avail_w / len(cols)
    tbl = Table(data, colWidths=[col_w] * len(cols), repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LGRAY]),
        ("GRID",         (0, 0), (-1, -1), 0.3, MGRAY),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


# ── Section divider ───────────────────────────────────────────────────────────
def _section(title: str, styles: dict) -> list:
    return [
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=4),
        Paragraph(title, styles["section_h"]),
    ]


# ── Main PDF builder ──────────────────────────────────────────────────────────
def build_pdf(state: dict) -> bytes:
    """
    Build the full PDF report and return it as bytes.

    Parameters
    ----------
    state : dict
        Dictionary produced by app.py containing all figures, dataframes,
        and scalar parameters needed for the report.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.2 * cm, bottomMargin=1.8 * cm,
        title="Residual Capacity Report",
        author="RCP v2.0",
    )

    styles = _build_styles()
    story: list = []

    # ── Cover page ─────────────────────────────────────────────────────────
    # The cover is painted entirely via _draw_cover() in the page callback.
    # We push a single blank spacer so the first page is "consumed" and the
    # content starts on page 2.  NO duplicate cover is added here.
    story.append(Spacer(1, PAGE_H - 2 * MARGIN))
    story.append(PageBreak())

    # ── 1. Global Parameters ───────────────────────────────────────────────
    story += _section("1. Global Parameters", styles)
    story.append(_kv_table([
        ("Study time [years]",  state.get("t_global", "—")),
        (fmt_var("I-corr") + " [µA/cm²]", state.get("icorr_val", "—")),
        ("Attack type",         state.get("attack_type", "—")),
        ("Initiation time [y]", f"{state.get('t_ini_calc', 0.0):.2f}"),
    ], styles))
    story.append(Spacer(1, 8))

    # ── 2. Initiation Period ───────────────────────────────────────────────
    story += _section("2. Initiation Period", styles)

    fig_tuutti = state.get("fig_tuutti")
    fig_ini    = state.get("fig_ini")
    avail_w    = PAGE_W - 2 * MARGIN
    chart_h    = 5.5 * cm

    if fig_tuutti or fig_ini:
        chart_cols = []
        for fig, cap in [(fig_tuutti, "Tuutti's Model — Pₓ"),
                         (fig_ini,    "Initiation Progress")]:
            img = _rl_image(fig, max_width=avail_w / 2 - 4, max_height=chart_h * 2)
            cell = [img or Paragraph("—", styles["body"]),
                    Paragraph(cap, styles["caption"])]
            chart_cols.append(cell)
        tbl = Table([chart_cols], colWidths=[avail_w / 2] * 2)
        tbl.setStyle(TableStyle([
            ("VALIGN",  (0, 0), (-1, -1), "TOP"),
            ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No initiation charts available.", styles["body"]))

    story.append(Spacer(1, 8))

    # ── 3. Residual Flexural Capacity ──────────────────────────────────────
    story += _section("3. Residual Flexural Capacity", styles)

    # Section parameters
    story.append(Paragraph("Section Parameters", styles["sub_h"]))
    story.append(_kv_table([
        ("h [mm]",                  state.get("h_val", "—")),
        ("b [mm]",                  state.get("b_val", "—")),
        (fmt_var("f-ck") + " [MPa]", state.get("fck_val", "—")),
        (fmt_var("f-yk") + " [MPa]", state.get("fyk", "—")),
        (fmt_var("n-top") + " / Φ_top [mm]",
         f"{state.get('n_sup','—')} / {state.get('p_sup','—')}"),
        (fmt_var("n-bot") + " / Φ_bot [mm]",
         f"{state.get('n_inf','—')} / {state.get('phi_inf_0','—')}"),
    ], styles))
    story.append(Spacer(1, 6))

    # Capacity chart
    fig_res = state.get("fig_res")
    img_res = _rl_image(fig_res, max_width=avail_w, max_height=chart_h * 2.2)
    if img_res:
        story.append(img_res)
        story.append(Paragraph("Fig. 1 — Residual Flexural Capacity over time", styles["caption"]))
    story.append(Spacer(1, 6))

    # Critical events table
    df_crit = state.get("df_criticos")
    if df_crit is not None and not df_crit.empty:
        story.append(Paragraph("Key Degradation Steps", styles["sub_h"]))
        story.append(_df_table(
            df_crit[["Tiempo", "Px", "Mu"]],
            styles,
            col_labels=["Time [y]", "Corr. [mm]", "Mu [kNm]"],
        ))

    t_life = state.get("t_life")
    if t_life:
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"⚠ <b>End of service life:</b> {t_life:.1f} years",
            ParagraphStyle("eol", parent=styles["body"],
                           textColor=ORANGE, fontName="Helvetica-Bold"),
        ))

    story.append(Spacer(1, 8))

    # ── 4. Prestressed Section ─────────────────────────────────────────────
    story += _section("4. Prestressed Section", styles)

    story.append(Paragraph("Section Parameters", styles["sub_h"]))
    story.append(_kv_table([
        ("h [mm]",                   state.get("h_p", "—")),
        ("b [mm]",                   state.get("b_p", "—")),
        ("Φ_p [mm]",                 state.get("phi_p_val", "—")),
        (fmt_var("n-bot"),           state.get("np_p", "—")),
        (fmt_var("f-py") + " [MPa]", state.get("fpy_p3_val", "—")),
        (fmt_var("A-e") + " [mm²]",  state.get("ae_p3_val", "—")),
    ], styles))
    story.append(Spacer(1, 6))

    # Stress + shear charts side by side
    fig_stresses = state.get("fig_stresses")
    fig_shear    = state.get("fig_shear")
    if fig_stresses or fig_shear:
        chart_cols = []
        for fig, cap in [(fig_stresses, "Prestress Evolution"),
                         (fig_shear,    "Shear Capacity V_Rd")]:
            img = _rl_image(fig, max_width=avail_w / 2 - 4, max_height=chart_h * 2)
            cell = [img or Paragraph("—", styles["body"]),
                    Paragraph(cap, styles["caption"])]
            chart_cols.append(cell)
        tbl = Table([chart_cols], colWidths=[avail_w / 2] * 2)
        tbl.setStyle(TableStyle([
            ("VALIGN",  (0, 0), (-1, -1), "TOP"),
            ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(tbl)

    t_life_p3 = state.get("t_life_p3")
    if t_life_p3:
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"⚠ <b>End of service life (prestressed):</b> {t_life_p3:.1f} years",
            ParagraphStyle("eol2", parent=styles["body"],
                           textColor=ORANGE, fontName="Helvetica-Bold"),
        ))

    story.append(Spacer(1, 8))

    # ── 5. Disclaimer ──────────────────────────────────────────────────────
    story += _section("5. Disclaimer", styles)
    story.append(Paragraph(
        "This report has been generated automatically by the Residual Capacity Platform v2.0. "
        "Results are indicative and should be verified by a qualified structural engineer before "
        "use in any design or assessment decision.",
        styles["body"],
    ))

    # ── Build PDF ──────────────────────────────────────────────────────────
    # onFirstPage draws the cover; onLaterPages draws the running header/footer.
    doc.build(story, onFirstPage=_draw_cover, onLaterPages=_on_page)
    return buf.getvalue()


# ── Streamlit button ──────────────────────────────────────────────────────────
def render_pdf_button(state: dict) -> None:
    """Render a floating Streamlit download button that triggers PDF generation."""
    try:
        pdf_bytes = build_pdf(state)
        filename  = (
            f"RCP_Report_{datetime.date.today().strftime('%Y%m%d')}.pdf"
        )
        st.download_button(
            label="⬇ Download PDF Report",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
        )
    except Exception as exc:
        st.error(f"PDF generation failed: {exc}")
