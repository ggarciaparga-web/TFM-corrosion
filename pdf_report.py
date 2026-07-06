"""
pdf_report.py
─────────────────────────────────────────────────────────────────────────────
Módulo independiente para generar el informe PDF de la Residual Capacity
Platform.  Se importa desde app.py con:

    from pdf_report import render_pdf_button

Y se llama al final del script principal (fuera de cualquier pestaña):

    render_pdf_button(state)

donde `state` es un dict con todos los datos necesarios (ver docstring de
render_pdf_button).
─────────────────────────────────────────────────────────────────────────────
Dependencias: reportlab, plotly, pandas, matplotlib
Nota: NO requiere kaleido ni Chrome. Las figuras Plotly se exportan a PNG
      mediante matplotlib (engine="matplotlib" de plotly) o, si no está
      disponible, se inserta un bloque de texto como marcador de posición.
"""

from __future__ import annotations

import io
import datetime
import logging
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

logger = logging.getLogger(__name__)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Paleta corporativa ────────────────────────────────────────────────────────
ORANGE   = colors.HexColor("#e17000")
DARK     = colors.HexColor("#1A1A1A")
BLUE     = colors.HexColor("#1f4e79")
RED      = colors.HexColor("#c0392b")
GREY_LT  = colors.HexColor("#f5f5f5")
GREY_MID = colors.HexColor("#cccccc")
WHITE    = colors.white

PAGE_W, PAGE_H = A4          # 210 × 297 mm
MARGIN_L = MARGIN_R = 18*mm
MARGIN_T = 22*mm
MARGIN_B = 18*mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R


# ── Estilos de texto ──────────────────────────────────────────────────────────
def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {}

    styles["title"] = ParagraphStyle(
        "title", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=20,
        textColor=WHITE, alignment=TA_LEFT, leading=24,
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle", parent=base["Normal"],
        fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor("#dddddd"), alignment=TA_LEFT, leading=14,
    )
    styles["section"] = ParagraphStyle(
        "section", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=13,
        textColor=BLUE, spaceBefore=10, spaceAfter=4, leading=16,
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontName="Helvetica", fontSize=9,
        textColor=DARK, leading=13, spaceAfter=3,
    )
    styles["caption"] = ParagraphStyle(
        "caption", parent=base["Normal"],
        fontName="Helvetica-Oblique", fontSize=8,
        textColor=colors.HexColor("#666666"), alignment=TA_CENTER, leading=11,
    )
    styles["kv_key"] = ParagraphStyle(
        "kv_key", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=9,
        textColor=DARK, leading=13,
    )
    styles["kv_val"] = ParagraphStyle(
        "kv_val", parent=base["Normal"],
        fontName="Helvetica", fontSize=9,
        textColor=DARK, leading=13,
    )
    return styles


# ── Helpers ───────────────────────────────────────────────────────────────────
def _fig_to_image(fig: go.Figure, width_mm: float, height_mm: float) -> RLImage | Paragraph:
    """Convierte una figura Plotly a un objeto Image de ReportLab.

    Estrategia sin Chrome/Kaleido:
    1. Intenta exportar con engine='orca' (si está instalado).
    2. Si falla, usa matplotlib para renderizar la figura como PNG.
    3. Si todo falla, devuelve un Paragraph de texto como marcador.
    """
    scale = 3
    px_w  = int(width_mm / 25.4 * 96 * scale)
    px_h  = int(height_mm / 25.4 * 96 * scale)

    # ── Intento 1: matplotlib engine (no requiere Chrome) ────────────────────
    try:
        img_bytes = pio.to_image(fig, format="png", width=px_w, height=px_h,
                                 scale=1, engine="matplotlib")
        return RLImage(io.BytesIO(img_bytes), width=width_mm * mm, height=height_mm * mm)
    except Exception as e1:
        logger.warning(f"⚠️ matplotlib engine falló: {e1}")

    # ── Intento 2: kaleido engine (requiere Chrome, puede funcionar en local) ─
    try:
        img_bytes = pio.to_image(fig, format="png", width=px_w, height=px_h, scale=1)
        return RLImage(io.BytesIO(img_bytes), width=width_mm * mm, height=height_mm * mm)
    except Exception as e2:
        logger.warning(f"⚠️ kaleido engine falló: {e2}")

    # ── Intento 3: SVG → PNG via svglib (sin Chrome) ─────────────────────────
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF
        svg_bytes = pio.to_image(fig, format="svg", width=px_w, height=px_h, scale=1)
        drawing = svg2rlg(io.BytesIO(svg_bytes))
        if drawing:
            # Escalar al tamaño deseado
            sx = (width_mm * mm) / drawing.width
            sy = (height_mm * mm) / drawing.height
            drawing.width  = width_mm * mm
            drawing.height = height_mm * mm
            drawing.transform = (sx, 0, 0, sy, 0, 0)
            return drawing
    except Exception as e3:
        logger.warning(f"⚠️ svglib engine falló: {e3}")

    # ── Fallback: marcador de texto ───────────────────────────────────────────
    logger.error("❌ No se pudo exportar la figura. Insertando marcador de texto.")
    styles = getSampleStyleSheet()
    return Paragraph(
        "<i>[Gráfico no disponible — instala kaleido o matplotlib para exportar figuras]</i>",
        styles["Normal"]
    )


def _kv_table(rows: list[tuple[str, str]], styles: dict) -> Table:
    """Tabla de dos columnas clave–valor con fondo alternado."""
    data = [[Paragraph(k, styles["kv_key"]), Paragraph(v, styles["kv_val"])]
            for k, v in rows]
    col_w = [CONTENT_W * 0.42, CONTENT_W * 0.58]
    tbl = Table(data, colWidths=col_w, repeatRows=0)
    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),  GREY_LT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, GREY_LT]),
        ("GRID",       (0, 0), (-1, -1), 0.3, GREY_MID),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ])
    tbl.setStyle(ts)
    return tbl


def _df_table(df: pd.DataFrame, styles: dict,
              col_widths: list[float] | None = None) -> Table:
    """Convierte un DataFrame en una tabla ReportLab."""
    header = [Paragraph(f"<b>{c}</b>", styles["kv_key"]) for c in df.columns]
    body   = [
        [Paragraph(str(round(v, 3) if isinstance(v, float) else v), styles["kv_val"])
         for v in row]
        for row in df.itertuples(index=False)
    ]
    data = [header] + body

    if col_widths is None:
        n = len(df.columns)
        col_widths = [CONTENT_W / n] * n

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    ts = TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_LT]),
        ("GRID",         (0, 0), (-1, -1), 0.3, GREY_MID),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ])
    tbl.setStyle(ts)
    return tbl


# ── Cabecera y pie de página ──────────────────────────────────────────────────
def _header_footer(canvas, doc):
    canvas.saveState()

    # ── Cabecera: banda naranja ───────────────────────────────────────────────
    canvas.setFillColor(ORANGE)
    canvas.rect(0, PAGE_H - 14*mm, PAGE_W, 14*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN_L, PAGE_H - 9*mm, "Residual Capacity Platform")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 9*mm,
                           f"Report generated: {datetime.date.today().strftime('%d %b %Y')}")

    # ── Pie de página ─────────────────────────────────────────────────────────
    canvas.setFillColor(GREY_MID)
    canvas.rect(0, 0, PAGE_W, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(DARK)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(MARGIN_L, 3.5*mm, "Concrete Durability & Structural Capacity Tool")
    canvas.drawRightString(PAGE_W - MARGIN_R, 3.5*mm, f"Page {doc.page}")

    canvas.restoreState()


# ── Portada ───────────────────────────────────────────────────────────────────
def _cover_page(canvas, doc):
    """Primera página: portada con fondo oscuro."""
    canvas.saveState()

    # Fondo
    canvas.setFillColor(colors.HexColor("#1A2B3C"))
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Banda naranja superior
    canvas.setFillColor(ORANGE)
    canvas.rect(0, PAGE_H - 28*mm, PAGE_W, 28*mm, fill=1, stroke=0)

    # Título
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawString(MARGIN_L, PAGE_H - 18*mm, "Residual Capacity Platform")
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(colors.HexColor("#dddddd"))
    canvas.drawString(MARGIN_L, PAGE_H - 24*mm, "Concrete Durability & Structural Capacity Report")

    # Línea decorativa
    canvas.setStrokeColor(ORANGE)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN_L, PAGE_H - 60*mm, PAGE_W - MARGIN_R, PAGE_H - 60*mm)

    # Fecha
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 10)
    canvas.drawString(MARGIN_L, PAGE_H - 68*mm,
                      f"Date: {datetime.date.today().strftime('%d %B %Y')}")

    # Pie
    canvas.setFillColor(GREY_MID)
    canvas.rect(0, 0, PAGE_W, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(DARK)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(MARGIN_L, 3.5*mm, "Concrete Durability & Structural Capacity Tool")
    canvas.drawRightString(PAGE_W - MARGIN_R, 3.5*mm, "Page 1")

    canvas.restoreState()


# ── Constructor principal del PDF ─────────────────────────────────────────────
def build_pdf(state: dict[str, Any]) -> bytes:
    """
    Construye el PDF completo y devuelve los bytes.

    Parámetros esperados en `state`
    ────────────────────────────────
    Globales:
        t_global        float   Tiempo de estudio [años]
        icorr_val       float   Icorr [µA/cm²]
        attack_type     str     "Carbonation" | "Chlorides"
        t_ini_calc      float   Tiempo de iniciación [años]

    Pestaña 1 — Initiation:
        fig_tuutti      go.Figure
        fig_ini         go.Figure

    Pestaña 2 — Residual capacity:
        fig_res         go.Figure
        df_criticos     pd.DataFrame   columnas: Tiempo, Px, Mu
        b_val, h_val    float          sección [mm]
        fck_val, fyk    float          resistencias [MPa]
        n_sup, p_sup    int/float      armado superior
        n_inf, phi_inf_0 int/float     armado inferior
        t_life          float | None

    Pestaña 3 — Prestressed:
        fig_stresses    go.Figure
        fig_shear       go.Figure
        df_t            pd.DataFrame   columnas: t, sigma_inferior, sigma_superior, px
        df_cor          pd.DataFrame   columnas: t, vrd
        h_p, b_p        float
        phi_p_val, np_p float/int
        fpy_p3_val      float
        ae_p3_val       float
        t_life_p3       float | None
    """
    buf = io.BytesIO()
    styles = _build_styles()

    # ── Plantillas de página ──────────────────────────────────────────────────
    frame_cover = Frame(0, 0, PAGE_W, PAGE_H, leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)
    frame_body  = Frame(MARGIN_L, MARGIN_B, CONTENT_W, PAGE_H - MARGIN_T - MARGIN_B,
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T,  bottomMargin=MARGIN_B,
    )
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame_cover],
                     onPage=_cover_page),
        PageTemplate(id="body",  frames=[frame_body],
                     onPage=_header_footer),
    ])

    story: list = []

    # ══════════════════════════════════════════════════════════════════════════
    # PORTADA  (página 1 — template "cover")
    # ══════════════════════════════════════════════════════════════════════════
    # La portada la dibuja _cover_page directamente en el canvas;
    # sólo necesitamos un salto de página para pasar al template "body".
    from reportlab.platypus import NextPageTemplate, PageBreak
    story.append(NextPageTemplate("cover"))
    story.append(PageBreak())          # genera la portada
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())          # primera página de contenido

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 0 — Parámetros globales
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Global Parameters", styles["section"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1, color=ORANGE, spaceAfter=6))

    global_rows = [
        ("Study time",          f"{state.get('t_global', '—')} years"),
        ("Corrosion current",   f"{state.get('icorr_val', '—')} µA/cm²"),
        ("Attack type",         state.get('attack_type', '—')),
        ("Initiation time",     f"{state.get('t_ini_calc', 0.0):.2f} years"),
    ]
    story.append(_kv_table(global_rows, styles))
    story.append(Spacer(1, 8*mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1 — Initiation Period
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1 — Initiation Period", styles["section"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1, color=ORANGE, spaceAfter=6))

    half_w = CONTENT_W / 2 - 3*mm
    fig_h   = 65   # mm

    # Dos gráficas en fila
    if state.get("fig_tuutti") and state.get("fig_ini"):
        img_tuutti = _fig_to_image(state["fig_tuutti"], half_w / mm, fig_h)
        img_ini    = _fig_to_image(state["fig_ini"],    half_w / mm, fig_h)
        row_data   = [[img_tuutti, img_ini]]
        row_tbl    = Table(row_data, colWidths=[half_w, half_w])
        row_tbl.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER"),
                                     ("VALIGN",(0,0), (-1,-1), "TOP"),
                                     ("LEFTPADDING", (0,0),(-1,-1), 3),
                                     ("RIGHTPADDING",(0,0),(-1,-1), 3)]))
        story.append(row_tbl)
        story.append(Paragraph(
            "Left: Tuutti's model (corrosion penetration Pₓ).  "
            "Right: Initiation progress vs. cover depth.",
            styles["caption"]
        ))
    else:
        story.append(Paragraph("⚠ Charts not available — run the analysis first.",
                                styles["body"]))

    story.append(Spacer(1, 8*mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2 — Residual Flexural Capacity
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2 — Residual Flexural Capacity", styles["section"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1, color=ORANGE, spaceAfter=6))

    # Parámetros de sección
    sec_rows = [
        ("Section h × b",       f"{state.get('h_val','—')} × {state.get('b_val','—')} mm"),
        ("Concrete strength fck", f"{state.get('fck_val','—')} MPa"),
        ("Steel yield fyk",       f"{state.get('fyk','—')} MPa"),
        ("Top reinforcement",     f"{state.get('n_sup','—')} × Ø{state.get('p_sup','—')} mm"),
        ("Bottom reinforcement",  f"{state.get('n_inf','—')} × Ø{state.get('phi_inf_0','—')} mm"),
        ("End of service life",   f"{state.get('t_life','—')} years" if state.get('t_life') else "Not reached"),
    ]
    story.append(_kv_table(sec_rows, styles))
    story.append(Spacer(1, 5*mm))

    # Gráfica de capacidad residual (ancho completo)
    if state.get("fig_res"):
        img_res = _fig_to_image(state["fig_res"], CONTENT_W / mm, 90)
        story.append(img_res)
        story.append(Paragraph(
            "Residual flexural capacity over time: Contevect model, MC Standard and MC Conservative.",
            styles["caption"]
        ))
    story.append(Spacer(1, 5*mm))

    # Tabla de eventos críticos
    if state.get("df_criticos") is not None and not state["df_criticos"].empty:
        story.append(Paragraph("Key Degradation Steps (Contevect)", styles["body"]))
        df_show = state["df_criticos"][["Tiempo", "Px", "Mu"]].copy()
        df_show.columns = ["Time [y]", "Corr. [mm]", "Mu [kNm]"]
        story.append(_df_table(df_show, styles,
                               col_widths=[CONTENT_W*0.33]*3))

    story.append(Spacer(1, 8*mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3 — Prestressed
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3 — Prestressed Section", styles["section"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=1, color=ORANGE, spaceAfter=6))

    pre_rows = [
        ("Section h × b",         f"{state.get('h_p','—')} × {state.get('b_p','—')} mm"),
        ("Prestress strand Ø",     f"{state.get('phi_p_val','—')} mm"),
        ("Number of strands",      str(state.get('np_p','—'))),
        ("Strand area Ae",         f"{state.get('ae_p3_val','—')} mm²"),
        ("Yield strength fpy",     f"{state.get('fpy_p3_val','—')} MPa"),
        ("End of service life",    f"{state.get('t_life_p3','—')} years" if state.get('t_life_p3') else "Not reached"),
    ]
    story.append(_kv_table(pre_rows, styles))
    story.append(Spacer(1, 5*mm))

    # Dos gráficas: tensiones + cortante
    if state.get("fig_stresses") and state.get("fig_shear"):
        img_stress = _fig_to_image(state["fig_stresses"], half_w / mm, fig_h)
        img_shear  = _fig_to_image(state["fig_shear"],   half_w / mm, fig_h)
        row_data2  = [[img_stress, img_shear]]
        row_tbl2   = Table(row_data2, colWidths=[half_w, half_w])
        row_tbl2.setStyle(TableStyle([("ALIGN", (0,0),(-1,-1),"CENTER"),
                                      ("VALIGN",(0,0),(-1,-1),"TOP"),
                                      ("LEFTPADDING", (0,0),(-1,-1), 3),
                                      ("RIGHTPADDING",(0,0),(-1,-1), 3)]))
        story.append(row_tbl2)
        story.append(Paragraph(
            "Left: prestress evolution (σ top & bottom).  Right: shear capacity V_Rd over time.",
            styles["caption"]
        ))

    story.append(Spacer(1, 5*mm))

    # Tabla de tensiones (muestra primeras 20 filas)
    if state.get("df_t") is not None and not state["df_t"].empty:
        story.append(Paragraph("Prestress stress evolution (first 20 time steps)", styles["body"]))
        df_t_show = state["df_t"][["t", "sigma_inferior", "sigma_superior"]].head(20).copy()
        df_t_show.columns = ["Time [y]", "σ Bottom [MPa]", "σ Top [MPa]"]
        story.append(_df_table(df_t_show, styles,
                               col_widths=[CONTENT_W*0.33]*3))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    return buf.getvalue()


# ── Función pública que añade el botón a Streamlit ────────────────────────────
def render_pdf_button(state: dict[str, Any]) -> None:
    """
    Renderiza un botón flotante en la esquina superior derecha de la página
    que genera y descarga el informe PDF.

    Llama a esta función AL FINAL de tu app.py, fuera de cualquier pestaña:

        from pdf_report import render_pdf_button
        render_pdf_button(state)

    `state` debe contener las claves descritas en build_pdf().
    """
    # Botón flotante (posición fija, esquina superior derecha)
    st.markdown("""
    <style>
    div[data-testid="stDownloadButton"] > button {
        position: fixed;
        top: 60px;
        right: 24px;
        z-index: 9999;
        background-color: #e17000;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        cursor: pointer;
        transition: background-color 0.2s ease;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #c45e00;
    }
    </style>
    """, unsafe_allow_html=True)

    # Generamos el PDF sólo cuando el usuario pulsa el botón
    with st.spinner("Generating PDF report…"):
        try:
            pdf_bytes = build_pdf(state)
            filename  = f"residual_capacity_{datetime.date.today().strftime('%Y%m%d')}.pdf"
            st.download_button(
                label="⬇ Download PDF Report",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                key="pdf_download_btn",
            )
        except Exception as exc:
            st.error(f"❌ Could not generate PDF: {exc}")
