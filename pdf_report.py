"""
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Register a Unicode-capable font for body text ────────────────────────────
# ReportLab's built-in Helvetica is Latin-1 only — subscript Unicode chars
# (₀₁₂…ₐₑᵢ…) render as dark boxes with it.  We register DejaVu Sans which
# ships with most Python environments (matplotlib bundles it) and covers the
# full Unicode Latin Extended block including all subscript codepoints we use.
import os as _os, sys as _sys

def _register_unicode_font() -> str:
    """Try to register DejaVuSans; return font name to use in styles."""
    candidates = [
        # matplotlib bundles DejaVu fonts — most reliable source
        _os.path.join(_os.path.dirname(_sys.modules.get("matplotlib", type("", (), {"__file__": ""})).__file__ or ""),
                      "mpl-data", "fonts", "ttf", "DejaVuSans.ttf"),
        # Common Linux system paths
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        # macOS / Homebrew
        "/opt/homebrew/share/fonts/dejavu-fonts/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
    ]
    for path in candidates:
        if path and _os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", path))
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold",
                    path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                    if _os.path.isfile(path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"))
                    else path))
                return "DejaVuSans"
            except Exception:
                continue
    # Fallback: Helvetica (subscripts may show as boxes for unsupported chars)
    return "Helvetica"

_BODY_FONT      = _register_unicode_font()
_BODY_FONT_BOLD = _BODY_FONT + "-Bold" if _BODY_FONT != "Helvetica" else "Helvetica-Bold"

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#002D62")
BLUE   = colors.HexColor("#005A9C")
ORANGE = colors.HexColor("#e17000")
LGRAY  = colors.HexColor("#f4f6f9")
MGRAY  = colors.HexColor("#e2e6ea")
DGRAY  = colors.HexColor("#555555")
WHITE  = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm

# ── Unicode subscript helper (mirrors app.py) ─────────────────────────────────
# CRITICAL: Only use subscript codepoints that Helvetica (ReportLab's built-in
# font) can render. Characters outside Latin-1 / Windows-1252 will appear as
# dark boxes. The safe set is: digits ₀–₉ and letters ₐ ₑ ᵢ ₙ ₒ ᵣ ₛ ᵤ ᵥ ₓ.
# All other suffix characters fall back to their normal (non-subscript) form.
_SUB_MAP = str.maketrans(
    "0123456789aeinorsuv x",
    "₀₁₂₃₄₅₆₇₈₉ₐₑᵢₙₒᵣₛᵤᵥ ₓ",
)

def fmt_var(label: str) -> str:
    """Convert 'X-i' style labels to 'Xᵢ' using safe Unicode subscripts.

    Only digits and the letters a, e, i, n, o, r, s, u, v, x have proper
    Unicode subscript codepoints supported by ReportLab's Helvetica font.
    All other suffix characters are left as normal text to avoid dark boxes.
    """
    def _replace(m):
        base, sub = m.group(1), m.group(2)
        return base + sub.translate(_SUB_MAP)
    return re.sub(r'([A-Za-z_]+)-([0-9a-z]+)', _replace, label)


# ── Plotly → PNG bytes (multi-engine, no kaleido required) ───────────────────
def _fig_to_png(fig, width_px: int = 900, height_px: int = 400) -> bytes | None:
    """
    Convert a Plotly figure to PNG bytes.

    Tries three engines in order:
      1. kaleido  (plotly.io.to_image)  — best quality, optional dependency
      2. orca     (plotly.io.to_image with orca engine)
      3. matplotlib — pure-Python fallback, always available, redraws the
         traces from the Plotly figure dict so no extra install is needed.

    Returns None only if all three engines fail.
    """
    # ── Engine 1: kaleido ────────────────────────────────────────────────────
    try:
        import plotly.io as pio
        png_bytes = pio.to_image(fig, format="png", width=width_px, height=height_px, scale=2)
        if png_bytes:
            return png_bytes
    except Exception:
        pass

    # ── Engine 2: orca ───────────────────────────────────────────────────────
    try:
        import plotly.io as pio
        png_bytes = pio.to_image(fig, format="png", width=width_px, height=height_px,
                                  engine="orca")
        if png_bytes:
            return png_bytes
    except Exception:
        pass

    # ── Engine 3: matplotlib fallback ────────────────────────────────────────
    try:
        return _fig_to_png_matplotlib(fig, width_px, height_px)
    except Exception:
        return None


# Colour cycle used by the matplotlib fallback (mirrors the app palette)
_MPL_COLORS = ["#e17000", "#1f4e79", "#2c2c2a", "#888888",
               "#4caf50", "#9c27b0", "#00bcd4", "#f44336"]

def _fig_to_png_matplotlib(fig, width_px: int = 900, height_px: int = 400) -> bytes | None:
    """
    Pure-matplotlib re-render of a Plotly figure.

    Iterates over fig.data traces and draws lines / scatter markers using
    matplotlib.  Axis titles, legend labels and vertical lines (shapes /
    annotations) are also reproduced so the PDF charts look clean even
    without kaleido.
    """
    import matplotlib  # noqa: PLC0415
    matplotlib.use("Agg")          # non-interactive backend, safe in any env
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    dpi = 150
    fig_w = width_px  / dpi
    fig_h = height_px / dpi

    mpl_fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)

    # ── Style ────────────────────────────────────────────────────────────────
    ax.set_facecolor("#ffffff")
    mpl_fig.patch.set_facecolor("#ffffff")
    ax.grid(True, color="#ebebeb", linewidth=0.8, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#cccccc")
    ax.tick_params(colors="#555555", labelsize=7)

    legend_handles = []
    color_idx = 0

    # ── Traces ───────────────────────────────────────────────────────────────
    for trace in fig.data:
        # Resolve colour: prefer the trace's own colour, else cycle
        raw_color = None
        if hasattr(trace, "line") and trace.line and trace.line.color:
            raw_color = trace.line.color
        elif hasattr(trace, "marker") and trace.marker and trace.marker.color:
            c = trace.marker.color
            if isinstance(c, str):
                raw_color = c
        color = raw_color or _MPL_COLORS[color_idx % len(_MPL_COLORS)]
        color_idx += 1

        x = list(trace.x) if trace.x is not None else []
        y = list(trace.y) if trace.y is not None else []
        if not x or not y:
            continue

        trace_type = type(trace).__name__.lower()
        label = str(trace.name) if trace.name else None

        if "scatter" in trace_type:
            mode = getattr(trace, "mode", None) or "lines"
            ls_map = {"dash": "--", "dot": ":", "dashdot": "-."}
            lw = 1.8
            ls = "-"
            if hasattr(trace, "line") and trace.line:
                if trace.line.dash:
                    ls = ls_map.get(trace.line.dash, "-")
                if trace.line.width:
                    lw = float(trace.line.width) * 0.7

            if "lines" in mode:
                line_obj, = ax.plot(x, y, color=color, linewidth=lw,
                                    linestyle=ls, zorder=3)
                if label:
                    legend_handles.append(
                        mpatches.Patch(color=color, label=label))

            if "markers" in mode:
                ms = 5
                if hasattr(trace, "marker") and trace.marker and trace.marker.size:
                    sz = trace.marker.size
                    ms = float(sz) * 0.5 if not isinstance(sz, (list, tuple)) else 5
                ax.scatter(x, y, color=color, s=ms**2, zorder=4)
                if label and "lines" not in mode:
                    legend_handles.append(
                        mpatches.Patch(color=color, label=label))

            # Fill under line
            if hasattr(trace, "fill") and trace.fill in ("tozeroy", "tonexty"):
                ax.fill_between(x, y, alpha=0.10, color=color, zorder=1)

        elif "bar" in trace_type:
            ax.bar(x, y, color=color, alpha=0.85, zorder=3)
            if label:
                legend_handles.append(mpatches.Patch(color=color, label=label))

    # ── Vertical lines from fig.layout.shapes ────────────────────────────────
    layout = fig.layout
    if layout.shapes:
        for shape in layout.shapes:
            if getattr(shape, "type", None) == "line":
                if shape.x0 == shape.x1:          # vertical
                    sc = getattr(shape, "line", None)
                    lc = (sc.color if sc and sc.color else "#888888")
                    ld = (sc.dash  if sc and sc.dash  else "solid")
                    ls_map = {"dash": "--", "dot": ":", "dashdot": "-."}
                    ax.axvline(x=shape.x0, color=lc,
                               linestyle=ls_map.get(ld, "--"),
                               linewidth=1.2, alpha=0.8, zorder=5)

    # ── Axis labels ──────────────────────────────────────────────────────────
    font_kw = dict(fontsize=8, color="#333333")
    if layout.xaxis and layout.xaxis.title and layout.xaxis.title.text:
        ax.set_xlabel(layout.xaxis.title.text, **font_kw)
    if layout.yaxis and layout.yaxis.title and layout.yaxis.title.text:
        ax.set_ylabel(layout.yaxis.title.text, **font_kw)
    if layout.title and layout.title.text:
        ax.set_title(layout.title.text, fontsize=9, color="#1f4e79", pad=6)

    # ── Legend ───────────────────────────────────────────────────────────────
    if legend_handles:
        ax.legend(handles=legend_handles, fontsize=7, framealpha=0.85,
                  loc="upper right", edgecolor="#dddddd")

    mpl_fig.tight_layout(pad=0.6)

    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def _rl_image(fig, max_width: float, max_height: float) -> RLImage | Paragraph | None:
    """
    Return a ReportLab Image flowable from a Plotly figure, scaled to fit.
    Falls back to a styled Paragraph only if ALL rendering engines fail.
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
            "⚠ Chart could not be rendered.",
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
            fontName=_BODY_FONT,
        ),
        "kv_key": ParagraphStyle(
            "kv_key", parent=base["Normal"],
            fontSize=8, leading=11, textColor=DGRAY,
            fontName=_BODY_FONT_BOLD,
        ),
        "kv_val": ParagraphStyle(
            "kv_val", parent=base["Normal"],
            fontSize=8, leading=11, textColor=NAVY,
            fontName=_BODY_FONT,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"],
            fontSize=8, leading=11, textColor=DGRAY,
            fontName=_BODY_FONT, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=7, leading=10, textColor=colors.HexColor("#aaaaaa"),
            fontName=_BODY_FONT, alignment=TA_CENTER,
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
    """Paint the cover page in UPM orange + blue palette on page 1 only."""
    if doc.page != 1:
        return
    canv.saveState()

    # ── Background: white base ────────────────────────────────────────────────
    canv.setFillColor(WHITE)
    canv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ── Top UPM-blue band (upper ~38 % of page) ───────────────────────────────
    canv.setFillColor(NAVY)                                   # #002D62
    canv.rect(0, PAGE_H * 0.62, PAGE_W, PAGE_H * 0.38, fill=1, stroke=0)

    # ── Thin orange accent stripe at the bottom of the blue band ─────────────
    canv.setFillColor(ORANGE)
    canv.rect(0, PAGE_H * 0.62 - 5, PAGE_W, 5, fill=1, stroke=0)

    # ── Bottom UPM-blue band (lower ~18 % of page) ────────────────────────────
    canv.setFillColor(colors.HexColor("#005A9C"))             # mid UPM blue
    canv.rect(0, 0, PAGE_W, PAGE_H * 0.18, fill=1, stroke=0)

    # ── Thin orange accent stripe at the top of the bottom band ──────────────
    canv.setFillColor(ORANGE)
    canv.rect(0, PAGE_H * 0.18, PAGE_W, 5, fill=1, stroke=0)

    # ── Title (inside blue top band) ──────────────────────────────────────────
    canv.setFont("Helvetica-Bold", 28)
    canv.setFillColor(WHITE)
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.76, "Residual Capacity Platform")

    # ── Subtitle (inside blue top band) ──────────────────────────────────────
    canv.setFont("Helvetica", 12)
    canv.setFillColor(colors.HexColor("#c8dff0"))             # light blue tint
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.71,
                           "Concrete Durability & Structural Capacity Report")

    # ── Orange version badge (white area, centred) ────────────────────────────
    badge_y = PAGE_H * 0.55
    canv.setFillColor(ORANGE)
    canv.roundRect(PAGE_W / 2 - 24, badge_y, 48, 17, 8, fill=1, stroke=0)
    canv.setFont("Helvetica-Bold", 9)
    canv.setFillColor(WHITE)
    canv.drawCentredString(PAGE_W / 2, badge_y + 5, "v2.0")

    # ── Date (white area) ─────────────────────────────────────────────────────
    canv.setFont("Helvetica", 10)
    canv.setFillColor(NAVY)
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.50,
                           datetime.date.today().strftime("%d %B %Y"))

    # ── Author / institution block (white area) ───────────────────────────────
    canv.setFont("Helvetica-Bold", 9)
    canv.setFillColor(colors.HexColor("#005A9C"))
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.44,
                           "Gabriela García-Parga")
    canv.setFont("Helvetica", 9)
    canv.setFillColor(DGRAY)
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.41,
                           "Master's Thesis · Universidad Politécnica de Madrid · 2026")
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.385,
                           "Supervisors: María del Mar Corral & Leonardo Todisco")

    # ── UPM label inside bottom blue band ────────────────────────────────────
    canv.setFont("Helvetica-Bold", 10)
    canv.setFillColor(WHITE)
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.09,
                           "Universidad Politécnica de Madrid")
    canv.setFont("Helvetica", 8)
    canv.setFillColor(colors.HexColor("#c8dff0"))
    canv.drawCentredString(PAGE_W / 2, PAGE_H * 0.065,
                           "E.T.S. de Ingenieros de Caminos, Canales y Puertos")

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

    # Header paragraphs use a white-on-blue style (overridden in TableStyle below)
    header_style = ParagraphStyle(
        "tbl_header", parent=styles["kv_key"],
        textColor=WHITE, fontName=_BODY_FONT_BOLD,
    )
    header = [Paragraph(c, header_style) for c in cols]

    def _fmt_cell(val) -> str:
        """Format numeric values to 1 decimal place; leave strings as-is."""
        try:
            f = float(val)
            return f"{f:.1f}"
        except (TypeError, ValueError):
            return str(val) if val is not None else "—"

    body_rows = [
        [Paragraph(_fmt_cell(row[c]), styles["kv_val"]) for c in df.columns]
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
    # The cover is painted entirely on the canvas via _draw_cover().
    # A single PageBreak is enough to "consume" page 1 and move the story
    # content to page 2 — no Spacer needed (and a full-height Spacer would
    # exceed the usable frame height and crash ReportLab).
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
        ("Φp [mm]",                 state.get("phi_p_val", "—")),
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
        "The platform was developed in 2026 as part of the Master\'s Thesis entitled "
        "<i>\'Residual Capacity of Corroded Reinforced and Prestressed Concrete Beams\'</i>, "
        "prepared by Gabriela García-Parga at the Universidad Politécnica de Madrid. "
        "The research was supervised by María del Mar Corral and Leonardo Todisco. "
        "The results presented in this report are intended for academic and research purposes "
        ,
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
