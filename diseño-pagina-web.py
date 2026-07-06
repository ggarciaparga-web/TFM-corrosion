import io
import logging
import numpy as np
import matplotlib

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyArrowPatch
import matplotlib.lines
import matplotlib.patheffects as pe
from PIL import Image
import plotly.graph_objects as go
import viktor as vkt

logger = logging.getLogger("viktor")

# ---------------------------------------------------------------------------
# Colour palette — UPM institutional blue + professional thesis style
# ---------------------------------------------------------------------------
# Primary:   UPM Blue  #003DA5  (Universidad Politécnica de Madrid)
# Secondary: UPM Dark  #002060  (deep navy for headings / axes)
# Accent:    UPM Red   #C8102E  (pitting / warning elements)
# Neutral:   warm grey family for concrete and backgrounds

C_CONCRETE   = "#DDD9D3"   # light warm grey — concrete fill
C_CONCRETE_E = "#4A4540"   # dark grey — concrete outline
C_STIRRUP    = "#2C2C2C"   # near-black — dashed stirrup
C_REBAR_FILL = "#C8102E"   # UPM red — rebar fill
C_REBAR_EDGE = "#8B0000"   # dark red — rebar edge
C_ORIG_EDGE  = "#BBBBBB"   # light grey — original bar outline (dashed)
C_BG         = "#FFFFFF"   # pure white — figure background
C_ANNOT      = "#0D1B2A"   # near-black — annotation text
C_BLUE       = "#003DA5"   # UPM blue — uniform corrosion title / primary
C_ORANGE     = "#C8102E"   # UPM red — pitting corrosion title / accent


def rebar_positions(b: float, h: float, cover: float, r_bar: float) -> list[tuple[float, float]]:
    """
    Return the (cx, cy) centres of the 4 corner rebars inside the stirrup.

    The stirrup inner edge is at `cover` from the concrete face; the rebar
    centre is a further `r_bar` inward so the bar just touches the stirrup.
    """
    margin = cover + r_bar
    return [
        (-b / 2 + margin,  h / 2 - margin),   # top-left
        ( b / 2 - margin,  h / 2 - margin),   # top-right
        (-b / 2 + margin, -h / 2 + margin),   # bottom-left
        ( b / 2 - margin, -h / 2 + margin),   # bottom-right
    ]


def uniform_radius(r0: float, corrosion_rate: float, t: float) -> float:
    """Remaining radius under uniform corrosion at time t."""
    return max(r0 - corrosion_rate * t, 0.0)


def pitting_boundary(
    r0: float,
    pit_angles: np.ndarray,
    pit_widths: np.ndarray,
    pit_depths: np.ndarray,
    severity: float,
    t: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (x, y) boundary of a rebar under pitting corrosion at time t.

    Physical model
    --------------
    Each pit is a **circular crater** whose centre is placed on the inward
    normal at angle θᵢ, at a distance chosen so the crater is internally
    tangent to the bar surface.  The crater carves material inward from the
    bar outer surface — perpendicular to the perimeter.

    Depth formula (decoupled from width)
    -------------------------------------
    Each pit has an independent maximum depth fraction f_i ∈ [0.35, 0.90],
    so the actual depth at time t is:

        d_i(t) = severity · t · f_i · r0

    This means at t=1 and severity=1 the deepest pit can consume up to 90 %
    of the bar radius — producing dramatically visible damage.

    Crater geometry
    ---------------
    Given depth d_i and bar radius r0, the crater radius is:

        R_c = sqrt(2 · r0 · d_i)

    This is the unique radius of a circle that is internally tangent to the
    bar circle at angle θᵢ and reaches exactly d_i below the surface.

    The crater centre sits on the inward normal at:

        C_i = (r0 − (R_c − d_i)) · (cos θᵢ, sin θᵢ)

    Boundary computation
    --------------------
    For every sample angle θ:

        r(θ) = r0 − max_i [ max(0,  R_c_i − dist(sample, C_i)) ]

    An angular window of ±(pit_widths[i] · 3.5) prevents a very deep pit
    from wrapping around the entire bar.

    Guarantees
    ----------
      - Pits always start ON the bar outer surface.
      - Material loss is perpendicular to the bar perimeter (normal direction).
      - Pits grow inward toward the bar centre as t increases.
      - The boundary is always <= r0 (no material added).
      - The boundary is always >= 0 (bar cannot go negative).

    Parameters
    ----------
    r0          : original bar radius (mm)
    pit_angles  : array of pit centre angles (radians), shape (n_pits,)
    pit_widths  : array of pit half-width angles (radians), shape (n_pits,)
    pit_depths  : array of per-pit maximum depth fractions (0–1), shape (n_pits,)
    severity    : dimensionless severity factor (0–1); global depth scale
    t           : normalised time (0–1)
    """
    N_THETA = 1440                                   # angular resolution
    theta   = np.linspace(0, 2 * np.pi, N_THETA, endpoint=False)

    # Reference surface sample points (original bar circle)
    sx = r0 * np.cos(theta)   # shape (N_THETA,)
    sy = r0 * np.sin(theta)

    # Accumulate the maximum inward penetration at each sample angle
    max_penetration = np.zeros(N_THETA)

    for i, angle_i in enumerate(pit_angles):
        # ── Pit depth: independent per-pit fraction of r0 ───────────────────
        # pit_depths[i] ∈ [0.35, 0.90] — decoupled from width so narrow pits
        # can still be very deep (realistic pitting morphology).
        d_i = severity * t * pit_depths[i] * r0
        d_i = min(d_i, r0 * 0.95)   # hard cap: never consume more than 95 % of radius

        if d_i <= 1e-9:
            continue

        # ── Crater radius (geometric tangency condition) ─────────────────────
        R_c = np.sqrt(2.0 * r0 * d_i)
        R_c = min(R_c, r0)           # safety cap

        # ── Crater centre: on the inward normal at θᵢ ───────────────────────
        # The crater circle is internally tangent to the bar at angle θᵢ.
        # Its centre is at distance (r0 − R_c + d_i) from the bar centre.
        inward_offset = r0 - R_c + d_i
        cx_i = inward_offset * np.cos(angle_i)
        cy_i = inward_offset * np.sin(angle_i)

        # ── Penetration at each surface sample ──────────────────────────────
        dist2 = (sx - cx_i) ** 2 + (sy - cy_i) ** 2   # shape (N_THETA,)
        inside = dist2 < R_c ** 2
        if not np.any(inside):
            continue

        dist          = np.sqrt(np.where(inside, dist2, R_c ** 2))
        penetration_i = np.where(inside, R_c - dist, 0.0)

        # ── Angular window guard ─────────────────────────────────────────────
        # Limit each pit to its own angular footprint so deep pits don't
        # accidentally carve material on the far side of the bar.
        delta    = theta - angle_i
        delta    = (delta + np.pi) % (2 * np.pi) - np.pi   # wrap to [−π, π]
        in_window = np.abs(delta) <= pit_widths[i] * 3.5
        penetration_i = np.where(in_window, penetration_i, 0.0)

        max_penetration = np.maximum(max_penetration, penetration_i)

    # Final boundary: original surface minus maximum inward penetration
    r_boundary = np.clip(r0 - max_penetration, 0.0, r0)
    return r_boundary * np.cos(theta), r_boundary * np.sin(theta)


def shoelace_area(x: np.ndarray, y: np.ndarray) -> float:
    """Polygon area via the shoelace formula."""
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def cover_attack_angle(bar_index: int, b: float, h: float, cover: float, r_bar: float) -> float:
    """
    Return the angle (radians) pointing FROM the rebar centre TOWARD the nearest
    concrete surface (i.e. the cover face).

    This is the physically correct attack direction for chloride-induced pitting:
    aggressive agents penetrate through the cover and reach the rebar from the
    outside face, so pits nucleate on the side of the bar that faces the cover.

    Bar layout (corner indices):
        0 → top-left     1 → top-right
        2 → bottom-left  3 → bottom-right
    """
    margin = cover + r_bar
    cx = [-b / 2 + margin,  b / 2 - margin,
          -b / 2 + margin,  b / 2 - margin][bar_index]
    cy = [ h / 2 - margin,  h / 2 - margin,
          -h / 2 + margin, -h / 2 + margin][bar_index]

    # Vector from bar centre to the nearest concrete face
    # For a corner bar the nearest face is the diagonal corner, but we decompose
    # into the two closest faces and pick the one with the smaller distance.
    dist_left   = cx - (-b / 2)   # distance to left face
    dist_right  =  b / 2 - cx     # distance to right face
    dist_bottom = cy - (-h / 2)   # distance to bottom face
    dist_top    =  h / 2 - cy     # distance to top face

    # Nearest face in x and y
    dx = -1.0 if dist_left < dist_right  else 1.0   # toward left or right face
    dy = -1.0 if dist_bottom < dist_top  else 1.0   # toward bottom or top face

    # The corner bar is equidistant to both nearest faces; combine both directions
    # so the attack comes from the true outer corner (diagonal toward cover corner)
    return np.arctan2(dy, dx)


def get_pit_geometry(
    n_pits: int,
    bar_index: int = 0,
    seed: int = 7,
    b: float = 300.0,
    h: float = 400.0,
    cover: float = 30.0,
    r_bar: float = 10.0,
    arc_half_width: float = np.pi / 2.0,   # ±90° arc centred on attack direction
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return (pit_angles, pit_widths, pit_depths) for a given bar — reproducible
    per bar index.

    Physical basis
    --------------
    Chloride ions diffuse through the concrete cover and reach the rebar on its
    **outer face** (the side closest to the concrete surface).  Pits therefore
    nucleate on the cover-facing arc of the bar, not randomly around the full
    perimeter.

    pit_angles : angular positions of pit centres (radians), concentrated in the
                 arc facing the nearest concrete face.
    pit_widths : half-width angle (radians) of each pit's mouth on the bar surface.
                 Range [π/8, π/3.5] (22.5°–51°) — wider than before so craters
                 are clearly visible even at moderate severity.
    pit_depths : per-pit maximum depth fraction of r0, range [0.40, 0.92].
                 Decoupled from width so narrow pits can be very deep (realistic
                 pitting morphology: some pits are needle-like, others are wide
                 and shallow).  The large upper bound (0.92) ensures that at
                 full severity the most aggressive pits consume nearly the entire
                 bar radius, making the damage dramatically visible.

    Parameters
    ----------
    arc_half_width : float
        Half-width of the attack arc (radians).  Default ±90° (π/2) keeps
        pits on the cover-facing hemisphere while allowing realistic spread.
    """
    rng = np.random.default_rng(seed + bar_index * 31)

    # ── Attack direction: from bar centre toward nearest concrete face ───────
    attack_angle = cover_attack_angle(bar_index, b, h, cover, r_bar)

    # ── Pit angles: uniformly distributed within the cover-facing arc ────────
    offsets    = rng.uniform(-arc_half_width, arc_half_width, n_pits)
    pit_angles = (attack_angle + offsets) % (2 * np.pi)

    # ── Pit widths: half-width angles in [π/8, π/3.5] (22.5°–51°) ───────────
    # Wider than the previous [15°–36°] range so craters have a clearly visible
    # mouth on the bar surface.
    pit_widths = rng.uniform(np.pi / 8, np.pi / 3.5, n_pits)

    # ── Pit depths: independent per-pit depth fraction of r0 ─────────────────
    # Range [0.40, 0.92] — decoupled from width.
    # A depth fraction of 0.92 means the pit can reach 92 % of the bar radius
    # at full severity, creating a dramatic, clearly visible notch.
    pit_depths = rng.uniform(0.40, 0.92, n_pits)

    return pit_angles, pit_widths, pit_depths


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_rc_section(
    ax: plt.Axes,
    b: float,
    h: float,
    cover: float,
    r_bar: float,
    bar_shapes: list,
    title: str,
    title_color: str,
) -> None:
    """
    Draw a clean RC cross-section on *ax* — no axes, no grid, no legend.

    Parameters
    ----------
    bar_shapes : list of tuples
        One entry per corner rebar:
        ``('circle', radius)`` for uniform corrosion or
        ``('polygon', x_offsets, y_offsets)`` for pitting corrosion.
    title_color : str
        Hex colour for the panel title text.
    """
    # ── Background: pure white ───────────────────────────────────────────────
    ax.set_facecolor(C_BG)
    ax.set_aspect("equal")

    # ── Concrete rectangle (light grey) ─────────────────────────────────────
    concrete = mpatches.FancyBboxPatch(
        (-b / 2, -h / 2), b, h,
        boxstyle="square,pad=0",
        facecolor=C_CONCRETE,
        edgecolor=C_CONCRETE_E,
        linewidth=2.0,
        zorder=1,
    )
    ax.add_patch(concrete)

    # ── Inner stirrup (dashed rectangle) ────────────────────────────────────
    stir_x = -b / 2 + cover
    stir_y = -h / 2 + cover
    stir_w = b - 2 * cover
    stir_h = h - 2 * cover
    stirrup = mpatches.Rectangle(
        (stir_x, stir_y), stir_w, stir_h,
        fill=False,
        edgecolor=C_STIRRUP,
        linewidth=1.5,
        linestyle=(0, (6, 3)),
        zorder=3,
    )
    ax.add_patch(stirrup)

    # ── Reinforcement bars ───────────────────────────────────────────────────
    positions = rebar_positions(b, h, cover, r_bar)
    for idx, (cx, cy) in enumerate(positions):
        shape = bar_shapes[idx]

        # Original bar outline (dashed grey reference circle)
        orig = plt.Circle(
            (cx, cy), r_bar,
            fill=False,
            edgecolor=C_ORIG_EDGE,
            linewidth=0.8,
            linestyle="--",
            alpha=0.6,
            zorder=4,
        )
        ax.add_patch(orig)

        if shape[0] == "circle":
            r = shape[1]
            if r > 0:
                bar = plt.Circle(
                    (cx, cy), r,
                    facecolor=C_REBAR_FILL,
                    edgecolor=C_REBAR_EDGE,
                    linewidth=0.8,
                    zorder=5,
                )
                ax.add_patch(bar)

        elif shape[0] == "polygon":
            px_off, py_off = shape[1], shape[2]
            px = px_off + cx
            py = py_off + cy
            ax.fill(px, py, color=C_REBAR_FILL, alpha=0.95, zorder=5)
            ax.plot(
                np.append(px, px[0]),
                np.append(py, py[0]),
                color=C_REBAR_EDGE, linewidth=0.8, zorder=6,
            )

    # ── Panel title ──────────────────────────────────────────────────────────
    ax.set_title(
        title,
        fontsize=12, fontweight="bold",
        color=title_color, pad=12,
        fontfamily="DejaVu Sans",
        loc="center",
    )

    # ── Remove all axes decorations ──────────────────────────────────────────
    ax.axis("off")

    # ── Thin top border in title colour for visual anchoring ─────────────────
    for spine in ax.spines.values():
        spine.set_visible(False)

    # ── Set view limits with a small margin around the section ───────────────
    pad = max(b, h) * 0.18
    ax.set_xlim(-b / 2 - pad, b / 2 + pad)
    ax.set_ylim(-h / 2 - pad, h / 2 + pad)


# ---------------------------------------------------------------------------
# Frame generation
# ---------------------------------------------------------------------------

def generate_animation_frames(
    b: float,
    h: float,
    cover: float,
    r_bar: float,
    corrosion_rate: float,
    n_pits: int,
    pit_severity: float,
    time_steps: int,
) -> list[Image.Image]:
    """
    Generate one PIL Image per time step.

    Left panel  → Uniform corrosion (all 4 bars shrink uniformly).
    Right panel → Pitting corrosion (each bar develops independent pits
                  originating from the cover face).

    The figure is completely clean: no axes, no grid, no legend, no time
    counter.  Only the % area loss is shown per panel.
    """
    frames: list[Image.Image] = []

    # Time axis: runs until the uniform bar is fully consumed
    t_max    = r_bar / max(corrosion_rate, 1e-9)
    t_values = np.linspace(0, t_max, time_steps)

    # Pre-compute pit geometry for each of the 4 bars (different per bar).
    # Each bar gets its own set of pit angles AND pit widths, both concentrated
    # on the cover-facing arc (physically: chloride attack from the outer face).
    all_pit_geom = [
        get_pit_geometry(n_pits, bar_index=i, b=b, h=h, cover=cover, r_bar=r_bar)
        for i in range(4)
    ]

    # Total steel area at t = 0 (4 bars)
    A0_total = 4 * np.pi * r_bar ** 2

    logger.info(f"RC section: b={b}, h={h}, cover={cover}, r_bar={r_bar}")
    logger.info(
        f"t_max={t_max:.1f} yr, steps={time_steps}, "
        f"rate={corrosion_rate}, pits={n_pits}, severity={pit_severity}"
    )

    for frame_idx, t in enumerate(t_values):

        # ── Figure: two panels, pure white background ─────────────────────
        fig, axes = plt.subplots(
            1, 2,
            figsize=(12, 7),
            facecolor=C_BG,
        )
        # Tight layout — no extra padding that would show a grey border
        fig.subplots_adjust(
            left=0.02, right=0.98,
            top=0.90, bottom=0.08,
            wspace=0.06,
        )

        # ── Compute steel areas for this frame ────────────────────────────
        # Uniform: all 4 bars shrink to the same radius
        r_u            = uniform_radius(r_bar, corrosion_rate, t)
        A_uniform      = 4 * np.pi * r_u ** 2
        pct_loss_u     = 100.0 * (1.0 - A_uniform / A0_total)

        # Pitting: each bar has its own irregular boundary carved from the surface
        A_pit_total = 0.0
        pit_shapes  = []
        for i in range(4):
            p_angles, p_widths, p_depths = all_pit_geom[i]
            px, py = pitting_boundary(
                r_bar, p_angles, p_widths, p_depths, pit_severity, t / t_max,
            )
            A_pit_total += shoelace_area(px, py)
            pit_shapes.append(("polygon", px, py))
        pct_loss_p = 100.0 * (1.0 - A_pit_total / A0_total)

        # ── Left panel: Uniform corrosion ─────────────────────────────────
        uniform_shapes = [("circle", r_u)] * 4
        draw_rc_section(
            ax=axes[0],
            b=b, h=h, cover=cover, r_bar=r_bar,
            bar_shapes=uniform_shapes,
            title="(a)  Uniform Corrosion",
            title_color=C_BLUE,
        )

        # ── Right panel: Pitting corrosion ────────────────────────────────
        draw_rc_section(
            ax=axes[1],
            b=b, h=h, cover=cover, r_bar=r_bar,
            bar_shapes=pit_shapes,
            title="(b)  Pitting Corrosion",
            title_color=C_ORANGE,
        )

        # ── Render frame to PIL Image ─────────────────────────────────────
        buf = io.BytesIO()
        fig.savefig(
            buf, format="png", dpi=110,
            bbox_inches="tight",
            facecolor=C_BG,
            edgecolor="none",
        )
        buf.seek(0)
        frames.append(Image.open(buf).copy())
        plt.close(fig)

    logger.info(f"Generated {len(frames)} RC section frames")
    return frames


# ---------------------------------------------------------------------------
# GIF compilation
# ---------------------------------------------------------------------------

def compile_gif(frames: list[Image.Image], fps: int = 8) -> bytes:
    """Compile PIL Images into an animated GIF and return raw bytes."""
    buf = io.BytesIO()
    duration_ms = max(1000 // fps, 40)
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=duration_ms,
        optimize=False,
    )
    buf.seek(0)
    logger.info(f"GIF compiled: {len(frames)} frames @ {fps} fps ({duration_ms} ms/frame)")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Area series for Plotly chart
# ---------------------------------------------------------------------------

def compute_area_series(
    b: float,
    h: float,
    cover: float,
    r_bar: float,
    corrosion_rate: float,
    n_pits: int,
    pit_severity: float,
    time_steps: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return (t_values, uniform_total_areas, pitting_total_areas).
    Areas are the *total* steel area of all 4 bars combined.
    Pitting angles are seeded from the cover-facing arc of each bar.
    """
    t_max = r_bar / max(corrosion_rate, 1e-9)
    t_values = np.linspace(0, t_max, time_steps)
    all_pit_geom = [
        get_pit_geometry(n_pits, bar_index=i, b=b, h=h, cover=cover, r_bar=r_bar)
        for i in range(4)
    ]

    uniform_areas: list[float] = []
    pitting_areas: list[float] = []

    for t in t_values:
        r_u = uniform_radius(r_bar, corrosion_rate, t)
        uniform_areas.append(4 * np.pi * r_u ** 2)

        A_pit = 0.0
        for i in range(4):
            p_angles, p_widths, p_depths = all_pit_geom[i]
            px, py = pitting_boundary(
                r_bar, p_angles, p_widths, p_depths, pit_severity, t / t_max,
            )
            A_pit += shoelace_area(px, py)
        pitting_areas.append(A_pit)

    return t_values, np.array(uniform_areas), np.array(pitting_areas)


# ---------------------------------------------------------------------------
# Capacity degradation curve animation
# ---------------------------------------------------------------------------

# Colour palette for the degradation view — UPM blue family
C_CURVE      = "#003DA5"   # UPM blue — MRd curve
C_STAGE_DOT  = "#C8102E"   # UPM red — stage marker dots
C_STAGE_LINE = "#AAAAAA"   # light grey — vertical connector lines
C_AXIS       = "#002060"   # UPM dark navy — axis lines and labels
C_GRID       = "#E4E8F0"   # very light blue-grey — grid
C_HIGHLIGHT  = "#E8EEF8"   # light UPM blue tint — active section highlight
C_LABEL_BOX  = "#003DA5"   # UPM blue — stage label background

# ── Degradation curve shape ──────────────────────────────────────────────────
# Five key stages with their normalised time positions and MRd fractions.
# The curve is smooth (cubic spline through these anchors).
STAGES = [
    # (t_norm, MRd_fraction, short_label, long_label, corrosion_type)
    (0.00, 1.000, "①", "Initiation\nperiod",          "none"),
    (0.22, 0.980, "②", "Rebar\ndepassivation",        "light"),
    (0.48, 0.880, "③", "Crack\nformation",            "moderate"),
    (0.72, 0.680, "④", "Concrete\nspalling",          "heavy"),
    (1.00, 0.350, "⑤", "Failure",                     "severe"),
]

# Corrosion severity mapped to a normalised t for the section drawing
STAGE_T_NORM = {
    "none":     0.00,
    "light":    0.18,
    "moderate": 0.42,
    "heavy":    0.68,
    "severe":   1.00,
}


def _mrd_curve(t_norm_array: np.ndarray) -> np.ndarray:
    """
    Return MRd/MRd0 values for an array of normalised times using a smooth
    piecewise cubic Hermite interpolation through the five stage anchors.
    The curve is monotonically decreasing and S-shaped — realistic for
    chloride-induced corrosion in a marine or de-icing salt environment.
    """
    from scipy.interpolate import PchipInterpolator
    t_knots   = np.array([s[0] for s in STAGES])
    mrd_knots = np.array([s[1] for s in STAGES])
    interp    = PchipInterpolator(t_knots, mrd_knots)
    return np.clip(interp(t_norm_array), 0.0, 1.0)


def _draw_mini_section(
    ax: plt.Axes,
    b: float,
    h: float,
    cover: float,
    r_bar: float,
    corrosion_type: str,
    n_pits: int,
    pit_severity: float,
    active: bool,
) -> None:
    """
    Draw a compact RC cross-section thumbnail on *ax*.

    corrosion_type : one of 'none', 'light', 'moderate', 'heavy', 'severe'
    active         : if True, draw a warm highlight border around the section
    """
    ax.set_facecolor(C_BG)
    ax.set_aspect("equal")
    ax.axis("off")

    t_norm = STAGE_T_NORM[corrosion_type]

    # ── Highlight border for the active (current) stage ──────────────────────
    if active:
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_edgecolor(C_BLUE)
            spine.set_linewidth(2.5)
    else:
        ax.set_frame_on(False)

    # ── Concrete rectangle ───────────────────────────────────────────────────
    concrete = mpatches.FancyBboxPatch(
        (-b / 2, -h / 2), b, h,
        boxstyle="square,pad=0",
        facecolor=C_CONCRETE,
        edgecolor=C_CONCRETE_E,
        linewidth=1.2,
        zorder=1,
    )
    ax.add_patch(concrete)

    # ── Stirrup ──────────────────────────────────────────────────────────────
    stir_x = -b / 2 + cover
    stir_y = -h / 2 + cover
    stirrup = mpatches.Rectangle(
        (stir_x, stir_y), b - 2 * cover, h - 2 * cover,
        fill=False,
        edgecolor=C_STIRRUP,
        linewidth=0.9,
        linestyle=(0, (5, 3)),
        zorder=3,
    )
    ax.add_patch(stirrup)

    # ── Rebars ───────────────────────────────────────────────────────────────
    positions = rebar_positions(b, h, cover, r_bar)

    # Pre-compute pit geometry once per bar (seeded, reproducible)
    all_pit_geom = [
        get_pit_geometry(n_pits, bar_index=i, b=b, h=h, cover=cover, r_bar=r_bar)
        for i in range(4)
    ]

    for idx, (cx, cy) in enumerate(positions):
        # Original bar outline (dashed grey)
        orig = plt.Circle(
            (cx, cy), r_bar,
            fill=False,
            edgecolor=C_ORIG_EDGE,
            linewidth=0.5,
            linestyle="--",
            alpha=0.5,
            zorder=4,
        )
        ax.add_patch(orig)

        if corrosion_type == "none":
            # Pristine bar — full circle
            bar = plt.Circle(
                (cx, cy), r_bar,
                facecolor=C_REBAR_FILL,
                edgecolor=C_REBAR_EDGE,
                linewidth=0.6,
                zorder=5,
            )
            ax.add_patch(bar)
        else:
            # Pitting corrosion — irregular boundary
            p_angles, p_widths, p_depths = all_pit_geom[idx]
            px, py = pitting_boundary(
                r_bar, p_angles, p_widths, p_depths, pit_severity, t_norm,
            )
            ax.fill(px + cx, py + cy, color=C_REBAR_FILL, alpha=0.95, zorder=5)
            ax.plot(
                np.append(px + cx, px[0] + cx),
                np.append(py + cy, py[0] + cy),
                color=C_REBAR_EDGE, linewidth=0.5, zorder=6,
            )

    # ── View limits ──────────────────────────────────────────────────────────
    pad = max(b, h) * 0.15
    ax.set_xlim(-b / 2 - pad, b / 2 + pad)
    ax.set_ylim(-h / 2 - pad, h / 2 + pad)


def generate_degradation_frames(
    b: float,
    h: float,
    cover: float,
    r_bar: float,
    n_pits: int,
    pit_severity: float,
    time_steps: int,
) -> list[Image.Image]:
    """
    Generate frames for the capacity-degradation animation.

    Layout
    ------
    Top (60 % height) : MRd/MRd0 curve drawn progressively left-to-right.
                        Five stage markers (dots + vertical dashed connectors).
    Bottom (40 % height): Five RC section thumbnails, one per stage.
                          The thumbnail corresponding to the most recently
                          passed stage is highlighted with a red border.

    The curve is drawn frame-by-frame; sections appear and update as the
    animated line reaches each stage marker.
    """
    frames: list[Image.Image] = []

    # ── Full time axis and MRd curve ─────────────────────────────────────────
    t_full  = np.linspace(0.0, 1.0, 600)   # high-res for smooth curve
    mrd_full = _mrd_curve(t_full)

    # Stage positions in data coordinates
    stage_t   = np.array([s[0] for s in STAGES])
    stage_mrd = _mrd_curve(stage_t)

    # ── Animation time steps ─────────────────────────────────────────────────
    # We animate t_norm from 0 → 1 over `time_steps` frames.
    # Add a short hold at the end (10 % extra frames at t=1).
    hold_frames = max(4, time_steps // 8)
    t_anim = np.concatenate([
        np.linspace(0.0, 1.0, time_steps),
        np.ones(hold_frames),
    ])

    logger.info(
        f"Degradation animation: {len(t_anim)} frames "
        f"(steps={time_steps}, hold={hold_frames})"
    )

    # ── Figure geometry constants ─────────────────────────────────────────────
    FIG_W, FIG_H = 14, 9
    # Section thumbnail aspect ratio
    sec_aspect = h / b   # height/width of the RC section

    for frame_idx, t_now in enumerate(t_anim):

        fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=C_BG)

        # GridSpec: 2 rows — curve (top) + sections (bottom)
        gs = GridSpec(
            2, 1,
            figure=fig,
            height_ratios=[1.55, 1.0],
            hspace=0.08,
            left=0.08, right=0.97,
            top=0.93, bottom=0.04,
        )

        ax_curve = fig.add_subplot(gs[0])
        ax_secs  = fig.add_subplot(gs[1])   # invisible host for section axes

        # ── Curve panel ──────────────────────────────────────────────────────
        ax_curve.set_facecolor(C_BG)
        ax_curve.set_xlim(-0.02, 1.08)
        ax_curve.set_ylim(0.15, 1.12)

        # Light grid
        for yg in [0.4, 0.6, 0.8, 1.0]:
            ax_curve.axhline(yg, color=C_GRID, linewidth=0.8, zorder=0)
        for xg in np.linspace(0, 1, 6):
            ax_curve.axvline(xg, color=C_GRID, linewidth=0.8, zorder=0)

        # Axes spines — keep left and bottom only
        for spine in ["top", "right"]:
            ax_curve.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax_curve.spines[spine].set_color(C_AXIS)
            ax_curve.spines[spine].set_linewidth(1.4)

        # Axis labels
        ax_curve.set_xlabel(
            "Normalised service life  $(t \\ /\\ t_{\\mathrm{service}})$",
            fontsize=10.5, color=C_AXIS, labelpad=7,
            fontfamily="DejaVu Sans",
        )
        ax_curve.set_ylabel(
            "Bending capacity  $M_{Rd} \\ /\\ M_{Rd,0}$",
            fontsize=10.5, color=C_AXIS, labelpad=9,
            fontfamily="DejaVu Sans",
        )
        ax_curve.tick_params(colors=C_AXIS, labelsize=9, direction="out", length=4)
        ax_curve.set_xticks(np.linspace(0, 1, 6))
        ax_curve.set_xticklabels([f"{v:.1f}" for v in np.linspace(0, 1, 6)])
        ax_curve.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])

        # ── Draw the curve up to t_now ────────────────────────────────────────
        mask = t_full <= t_now
        if np.any(mask):
            t_drawn   = t_full[mask]
            mrd_drawn = mrd_full[mask]

            # Filled area under the curve (light navy fill)
            ax_curve.fill_between(
                t_drawn, mrd_drawn, 0.15,
                color=C_CURVE, alpha=0.07, zorder=1,
            )
            # Main curve line
            ax_curve.plot(
                t_drawn, mrd_drawn,
                color=C_CURVE, linewidth=2.8, zorder=3,
                solid_capstyle="round",
            )
            # Animated tip dot
            ax_curve.scatter(
                [t_drawn[-1]], [mrd_drawn[-1]],
                s=55, color=C_CURVE, zorder=5, clip_on=False,
            )

        # ── Stage markers (only for stages already reached) ───────────────────
        active_stage_idx = -1
        for si, (st, sm, slabel, slong, _) in enumerate(STAGES):
            if st > t_now + 1e-6:
                break
            active_stage_idx = si

            # Vertical dashed connector from curve to bottom panel
            ax_curve.axvline(
                st, ymin=0, ymax=(sm - 0.15) / (1.12 - 0.15),
                color=C_STAGE_LINE, linewidth=1.0,
                linestyle=(0, (4, 3)), zorder=2,
            )

            # Stage dot on the curve
            ax_curve.scatter(
                [st], [sm],
                s=80, color=C_STAGE_DOT,
                edgecolors="white", linewidths=1.2,
                zorder=6, clip_on=False,
            )

            # Stage number label (circled numeral above the dot)
            ax_curve.text(
                st, sm + 0.048, slabel,
                ha="center", va="bottom",
                fontsize=10, fontweight="bold",
                color=C_STAGE_DOT, zorder=7,
                fontfamily="DejaVu Sans",
            )

        # ── Title ─────────────────────────────────────────────────────────────
        ax_curve.set_title(
            "Structural Capacity Degradation due to Reinforcement Corrosion",
            fontsize=13, fontweight="bold",
            color=C_AXIS, pad=12,
            fontfamily="DejaVu Sans",
        )

        # ── Section thumbnails panel ──────────────────────────────────────────
        ax_secs.set_visible(False)   # hide the host axes

        n_stages = len(STAGES)
        # Evenly space 5 thumbnails across the bottom panel
        # We use figure-level axes positioned manually in figure coordinates.
        gs_bottom = gs[1].get_position(fig)
        panel_y0  = gs_bottom.y0
        panel_y1  = gs_bottom.y1
        panel_x0  = gs_bottom.x0
        panel_x1  = gs_bottom.x1
        panel_w   = panel_x1 - panel_x0
        panel_h   = panel_y1 - panel_y0

        # Each thumbnail occupies an equal horizontal slot
        slot_w = panel_w / n_stages
        thumb_h_frac = 0.72   # fraction of panel height used by the thumbnail
        thumb_w_fig  = slot_w * 0.72
        thumb_h_fig  = thumb_h_frac * panel_h

        # Keep aspect ratio of the RC section
        # (limit height so it doesn't overflow)
        thumb_h_fig = min(thumb_h_fig, thumb_w_fig * sec_aspect * 1.1)

        for si, (st, sm, slabel, slong, ctype) in enumerate(STAGES):
            slot_cx = panel_x0 + slot_w * (si + 0.5)   # centre x of slot

            # ── Vertical connector line (figure coords → data coords) ─────────
            # Draw a line from the curve panel bottom to the section thumbnail top
            # using figure-level coordinates via ax_curve's transform.
            if st <= t_now + 1e-6:
                # Convert stage t position to figure x coordinate
                ax_curve_pos = ax_curve.get_position()
                curve_x_fig = (
                    ax_curve_pos.x0
                    + (st - ax_curve.get_xlim()[0])
                    / (ax_curve.get_xlim()[1] - ax_curve.get_xlim()[0])
                    * ax_curve_pos.width
                )
                # Draw connector in figure coordinates
                fig.add_artist(
                    matplotlib.lines.Line2D(
                        [curve_x_fig, slot_cx],
                        [ax_curve_pos.y0, panel_y1],
                        transform=fig.transFigure,
                        color=C_STAGE_LINE,
                        linewidth=0.9,
                        linestyle=(0, (4, 3)),
                        zorder=0,
                        clip_on=False,
                    )
                )

            # ── Section thumbnail axes ────────────────────────────────────────
            thumb_x0 = slot_cx - thumb_w_fig / 2
            thumb_y0 = panel_y0 + (panel_h - thumb_h_fig) * 0.35

            ax_thumb = fig.add_axes(
                [thumb_x0, thumb_y0, thumb_w_fig, thumb_h_fig],
            )

            # Only draw sections that have been reached
            reached = st <= t_now + 1e-6
            is_active = (si == active_stage_idx)

            if reached:
                _draw_mini_section(
                    ax=ax_thumb,
                    b=b, h=h, cover=cover, r_bar=r_bar,
                    corrosion_type=ctype,
                    n_pits=n_pits,
                    pit_severity=pit_severity,
                    active=is_active,
                )
            else:
                # Not yet reached — draw a faint placeholder
                ax_thumb.set_facecolor("#F5F5F5")
                ax_thumb.set_aspect("equal")
                ax_thumb.axis("off")
                ax_thumb.text(
                    0.5, 0.5, "—",
                    ha="center", va="center",
                    fontsize=14, color="#CCCCCC",
                    transform=ax_thumb.transAxes,
                )

            # ── Stage label below the thumbnail ───────────────────────────────
            label_y = thumb_y0 - 0.025
            label_color = C_AXIS if reached else "#BBBBBB"
            fig.text(
                slot_cx, label_y,
                slong,
                ha="center", va="top",
                fontsize=7.8,
                color=label_color,
                fontfamily="DejaVu Sans",
                fontweight="semibold" if reached else "normal",
                multialignment="center",
            )

        # ── Render frame ──────────────────────────────────────────────────────
        buf = io.BytesIO()
        fig.savefig(
            buf, format="png", dpi=110,
            bbox_inches="tight",
            facecolor=C_BG,
            edgecolor="none",
        )
        buf.seek(0)
        frames.append(Image.open(buf).copy())
        plt.close(fig)

    logger.info(f"Degradation frames generated: {len(frames)}")
    return frames




class Parametrization(vkt.Parametrization):
    """Input parameters for the RC section corrosion visualisation app."""

    # ── Section geometry ─────────────────────────────────────────────────────
    sec_geom = vkt.Section("Section Geometry")
    sec_geom.width = vkt.NumberField(
        "Section width  b",
        default=300.0, min=100.0, max=600.0, suffix="mm",
        description="Overall width of the rectangular concrete section.",
    )
    sec_geom.height = vkt.NumberField(
        "Section height  h",
        default=400.0, min=100.0, max=800.0, suffix="mm",
        description="Overall height of the rectangular concrete section.",
    )
    sec_geom.cover = vkt.NumberField(
        "Concrete cover  c",
        default=30.0, min=10.0, max=80.0, suffix="mm",
        description="Nominal concrete cover to the stirrup face.",
    )
    sec_geom.rebar_diameter = vkt.NumberField(
        "Rebar diameter  \u00f8",
        default=20.0, min=6.0, max=40.0, suffix="mm",
        description="Nominal diameter of each corner reinforcement bar.",
    )

    # ── Uniform corrosion ────────────────────────────────────────────────────
    sec_uniform = vkt.Section("Uniform Corrosion")
    sec_uniform.corrosion_rate = vkt.NumberField(
        "Corrosion rate  \u1d35\u1d9c\u1d52\u02b3\u02b3",
        default=0.05, min=0.005, max=0.5,
        num_decimals=3, suffix="mm/yr", variant="slider",
        description=(
            "Radial section loss per year, proportional to the corrosion "
            "current density I\u1d9c\u1d52\u02b3\u02b3. "
            "Typical values: 0.01\u20130.05\u202fmm/yr (low), "
            "0.05\u20130.2\u202fmm/yr (moderate), >0.2\u202fmm/yr (severe)."
        ),
    )

    # ── Pitting corrosion ────────────────────────────────────────────────────
    sec_pitting = vkt.Section("Pitting Corrosion")
    sec_pitting.n_pits = vkt.IntegerField(
        "Number of pits  n\u209a\u1d62\u209c",
        default=6, min=1, max=12,
        description="Number of localised pits distributed around each bar perimeter.",
    )
    sec_pitting.pit_severity = vkt.NumberField(
        "Pit severity  \u03b1\u209a\u1d62\u209c",
        default=0.75, min=0.05, max=1.0,
        num_decimals=2, variant="slider",
        description=(
            "Dimensionless severity factor \u03b1\u209a\u1d62\u209c \u2208 [0, 1]. "
            "Controls the maximum depth of each pit relative to the bar radius r\u2080. "
            "Higher values produce deeper, more aggressive pitting."
        ),
    )

    # ── Animation ────────────────────────────────────────────────────────────
    sec_anim = vkt.Section("Animation")
    sec_anim.time_steps = vkt.IntegerField(
        "Number of frames  N\u1da0\u02b3\u1d43\u1d50\u1d49\u02e2",
        default=40, min=10, max=80,
        description="Total number of animation frames (more = smoother but slower to render).",
    )

    # ── Export ───────────────────────────────────────────────────────────────
    sec_export = vkt.Section("Export")
    sec_export.btn_download = vkt.DownloadButton(
        "Download Corrosion Animation GIF",
        method="download_gif",
        longpoll=True,
    )
    sec_export.btn_download_deg = vkt.DownloadButton(
        "Download Degradation Curve GIF",
        method="download_degradation_gif",
        longpoll=True,
    )


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class Controller(vkt.Controller):
    """Main controller for the RC section corrosion visualisation."""

    parametrization = Parametrization

    # ── Shared input extraction ───────────────────────────────────────────────

    def _get_inputs(self, params) -> dict:
        """Extract, validate and return all inputs as a dict."""
        b        = params.sec_geom.width          or 300.0
        h        = params.sec_geom.height         or 400.0
        cover    = params.sec_geom.cover          or 30.0
        diam     = params.sec_geom.rebar_diameter or 20.0
        r_bar    = diam / 2.0

        rate     = params.sec_uniform.corrosion_rate or 0.05
        n_pits   = params.sec_pitting.n_pits         or 4
        severity = params.sec_pitting.pit_severity   or 0.4
        steps    = params.sec_anim.time_steps        or 40

        # Sanity: cover + r_bar must fit inside the section
        max_margin = min(b, h) / 2.0 - 5.0
        cover  = min(cover, max_margin - r_bar)
        r_bar  = min(r_bar, max_margin - cover)

        logger.info(
            f"Inputs: b={b}, h={h}, cover={cover}, r_bar={r_bar:.1f}, "
            f"rate={rate}, n_pits={n_pits}, severity={severity}, steps={steps}"
        )
        return dict(b=b, h=h, cover=cover, r_bar=r_bar,
                    rate=rate, n_pits=n_pits, severity=severity, steps=steps)

    # ── View 1: Animated GIF ─────────────────────────────────────────────────

    @vkt.ImageView("Corrosion Animation", duration_guess=35)
    def show_animation(self, params, **kwargs):
        """Render the RC section corrosion animation as an inline GIF."""
        inp = self._get_inputs(params)
        frames = generate_animation_frames(
            b=inp["b"], h=inp["h"], cover=inp["cover"], r_bar=inp["r_bar"],
            corrosion_rate=inp["rate"], n_pits=inp["n_pits"],
            pit_severity=inp["severity"], time_steps=inp["steps"],
        )
        gif_bytes = compile_gif(frames, fps=8)
        return vkt.ImageResult(io.BytesIO(gif_bytes))

    # ── View 2: Steel area over time ─────────────────────────────────────────

    @vkt.PlotlyView("Steel Area vs. Time")
    def show_area_plot(self, params, **kwargs):
        """Interactive chart of total remaining steel area for both corrosion modes."""
        inp = self._get_inputs(params)
        r_bar    = inp["r_bar"]
        rate     = inp["rate"]
        n_pits   = inp["n_pits"]
        severity = inp["severity"]
        steps    = inp["steps"]

        t_values, uniform_areas, pitting_areas = compute_area_series(
            b=inp["b"], h=inp["h"], cover=inp["cover"],
            r_bar=r_bar, corrosion_rate=rate,
            n_pits=n_pits, pit_severity=severity, time_steps=steps,
        )

        A0 = 4 * np.pi * r_bar ** 2   # initial total steel area

        # Percentage remaining
        pct_uniform = 100.0 * uniform_areas / A0
        pct_pitting = 100.0 * pitting_areas / A0

        fig = go.Figure()

        # ── Uniform trace ────────────────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=t_values, y=uniform_areas,
            mode="lines", name="Uniform — Aₛ (mm²)",
            line=dict(color="#003DA5", width=2.5),
            fill="tozeroy", fillcolor="rgba(0,61,165,0.10)",
            yaxis="y1",
        ))
        fig.add_trace(go.Scatter(
            x=t_values, y=pct_uniform,
            mode="lines", name="Uniform — % remaining",
            line=dict(color="#003DA5", width=1.5, dash="dot"),
            yaxis="y2",
            visible="legendonly",
        ))

        # ── Pitting trace ────────────────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=t_values, y=pitting_areas,
            mode="lines", name="Pitting — Aₛ (mm²)",
            line=dict(color="#C8102E", width=2.5, dash="dash"),
            fill="tozeroy", fillcolor="rgba(200,16,46,0.10)",
            yaxis="y1",
        ))
        fig.add_trace(go.Scatter(
            x=t_values, y=pct_pitting,
            mode="lines", name="Pitting — % remaining",
            line=dict(color="#C8102E", width=1.5, dash="dashdot"),
            yaxis="y2",
            visible="legendonly",
        ))

        # ── Reference line: initial area ─────────────────────────────────────
        fig.add_hline(
            y=A0,
            line_dash="dot", line_color="rgba(80,80,80,0.45)",
            annotation_text=f"A₀ = {A0:.1f} mm²",
            annotation_position="top right",
            annotation_font_color="#555555",
        )

        fig.update_layout(
            title=dict(
                text="Total Remaining Steel Area — 4 Corner Bars",
                font=dict(size=15, color="#002060", family="Arial, sans-serif"),
                x=0.5,
            ),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F4F6FB",
            font=dict(color="#0D1B2A", family="Arial, sans-serif"),
            xaxis=dict(
                title=dict(
                    text="Time  t  (years)",
                    font=dict(size=12, color="#002060"),
                ),
                tickfont=dict(size=10),
                gridcolor="#D8DFF0",
                zeroline=False,
                showline=True, linecolor="#AAAAAA", linewidth=1,
            ),
            yaxis=dict(
                title=dict(
                    text="Steel area  Aₛ  (mm²)",
                    font=dict(size=12, color="#002060"),
                ),
                tickfont=dict(size=10),
                gridcolor="#D8DFF0",
                zeroline=False,
                showline=True, linecolor="#AAAAAA", linewidth=1,
                rangemode="tozero",
            ),
            yaxis2=dict(
                title=dict(
                    text="Remaining area  Aₛ / Aₛ,₀  (%)",
                    font=dict(size=12, color="#002060"),
                ),
                tickfont=dict(size=10),
                overlaying="y",
                side="right",
                range=[0, 105],
                showgrid=False,
                zeroline=False,
                showline=True, linecolor="#AAAAAA", linewidth=1,
            ),
            legend=dict(
                bgcolor="rgba(255,255,255,0.90)",
                bordercolor="#C8D0E8",
                borderwidth=1,
                font=dict(size=10),
                x=0.75, y=0.95,
            ),
            hovermode="x unified",
            margin=dict(l=65, r=75, t=75, b=65),
        )

        return vkt.PlotlyResult(fig)

    # ── View 3: Capacity degradation curve animation ─────────────────────────

    @vkt.ImageView("Capacity Degradation", duration_guess=40)
    def show_degradation(self, params, **kwargs):
        """Animated MRd degradation curve with synchronized RC section thumbnails."""
        inp = self._get_inputs(params)
        frames = generate_degradation_frames(
            b=inp["b"], h=inp["h"], cover=inp["cover"], r_bar=inp["r_bar"],
            n_pits=inp["n_pits"], pit_severity=inp["severity"],
            time_steps=inp["steps"],
        )
        gif_bytes = compile_gif(frames, fps=7)
        return vkt.ImageResult(io.BytesIO(gif_bytes))

    # ── Download: Degradation GIF ─────────────────────────────────────────────

    def download_degradation_gif(self, params, **kwargs):
        """Generate and return the degradation curve GIF as a downloadable file."""
        inp = self._get_inputs(params)
        logger.info("Degradation GIF download requested")
        frames = generate_degradation_frames(
            b=inp["b"], h=inp["h"], cover=inp["cover"], r_bar=inp["r_bar"],
            n_pits=inp["n_pits"], pit_severity=inp["severity"],
            time_steps=inp["steps"],
        )
        gif_bytes = compile_gif(frames, fps=7)
        b_val = int(inp["b"])
        h_val = int(inp["h"])
        return vkt.DownloadResult(
            file_content=gif_bytes,
            file_name=f"RC_degradation_{b_val}x{h_val}.gif",
        )

    # ── Download: Corrosion section GIF ──────────────────────────────────────

    def download_gif(self, params, **kwargs):
        """Generate and return the animated GIF as a downloadable file."""
        inp = self._get_inputs(params)
        logger.info(f"GIF download requested")
        frames = generate_animation_frames(
            b=inp["b"], h=inp["h"], cover=inp["cover"], r_bar=inp["r_bar"],
            corrosion_rate=inp["rate"], n_pits=inp["n_pits"],
            pit_severity=inp["severity"], time_steps=inp["steps"],
        )
        gif_bytes = compile_gif(frames, fps=8)
        b_val = int(inp["b"])
        h_val = int(inp["h"])
        rate  = inp["rate"]
        return vkt.DownloadResult(
            file_content=gif_bytes,
            file_name=f"RC_corrosion_{b_val}x{h_val}_rate{rate:.3f}.gif",
        )
