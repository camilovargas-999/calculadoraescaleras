import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import io
from datetime import datetime

st.set_page_config(page_title="Escaleras Pro V7.0", page_icon="🏗️", layout="wide")

# --- ESTILOS ---
st.markdown("""
<style>
    .metric-box {
        background: #1e2a3a; border-radius: 10px;
        padding: 16px; text-align: center;
        border-left: 4px solid #00c9a7;
    }
    .metric-label { color: #aaa; font-size: 13px; }
    .metric-value { color: #fff; font-size: 22px; font-weight: bold; }
    .section-title { font-size: 16px; font-weight: bold; color: #00c9a7; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADO ---
if 'precios' not in st.session_state:
    st.session_state['precios'] = {
        'cemento': 32000.0, 'mixto': 190000.0,
        'varilla_38': 24000.0, 'grafil_14': 5000.0,
        'alambre': 10000.0, 'pago_persona': 90000.0,
        'cantidad_personas': 4, 'bulto_pena': 10000.0,
        'cant_pena': 2, 'acarreo': 100000.0,
        'grafil_cant': 2, 'alambre_kg': 1,
        # MEJORA 3: gastos indirectos ahora es configurable (antes era 5% fijo)
        'gastos_indirectos_pct': 5.0,
    }
if 'historial' not in st.session_state:
    st.session_state['historial'] = []


def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")


def calcular_escalera(tipo, alt_cm, fondo_cm, anc_cm):
    alt = alt_cm / 100
    fondo = fondo_cm / 100
    anc = anc_cm / 100
    pasos = math.ceil(alt_cm / 18)
    contrahuella = alt_cm / pasos
    huella = fondo_cm / pasos if tipo == "Recta" else max(fondo_cm / pasos, 25)
    long_inclinada = math.sqrt(fondo**2 + alt**2)
    espesor = 0.11
    vol_base = long_inclinada * anc * espesor
    factores = {"Recta": 1.0, "En L con abanico": 1.35, "En U con abanico": 1.70, "Caracol": 1.50}
    vol = vol_base * factores.get(tipo, 1.0)
    bls_cemento = math.ceil(vol * 7.5)
    mix_m3 = round(vol * 1.1, 2)
    num_long = math.ceil(anc / 0.15) + 1
    barras_long = math.ceil((num_long * long_inclinada * 1.1) / 6)
    num_trans = math.ceil(long_inclinada / 0.20)
    barras_trans = math.ceil((num_trans * anc * 1.1) / 6)
    v38 = barras_long + barras_trans
    return {
        'pasos': pasos, 'contrahuella': round(contrahuella, 1),
        'huella': round(huella, 1), 'long_inclinada': round(long_inclinada, 2),
        'vol': round(vol, 3), 'bls_cemento': bls_cemento,
        'mix_m3': mix_m3, 'v38_barras': v38,
    }


# MEJORA 1: cálculo de costos extraído a su propia función
def calcular_costos(res, p):
    """
    Recibe los resultados técnicos (res) y los precios (p),
    y devuelve todos los costos calculados en un diccionario.
    Antes estos cálculos estaban sueltos en la interfaz — ahora
    son fáciles de reutilizar y de modificar en un solo lugar.
    """
    costo_cemento  = res['bls_cemento'] * p['cemento']
    costo_mixto    = res['mix_m3']      * p['mixto']
    costo_v38      = res['v38_barras']  * p['varilla_38']
    costo_grafil   = p['grafil_cant']   * p['grafil_14']
    costo_alambre  = p['alambre_kg']    * p['alambre']
    costo_pena     = p['cant_pena']     * p['bulto_pena']
    costo_mo       = p['pago_persona']  * p['cantidad_personas']
    costo_acarreo  = p['acarreo']

    costo_materiales  = costo_cemento + costo_mixto + costo_v38 + costo_grafil + costo_alambre + costo_pena
    costo_directo     = costo_materiales + costo_mo + costo_acarreo

    # MEJORA 3: porcentaje configurable en lugar de 5% fijo
    pct_indirectos    = p.get('gastos_indirectos_pct', 5.0) / 100
    gastos_indirectos = costo_directo * pct_indirectos
    costo_total       = costo_directo + gastos_indirectos

    return {
        'costo_cemento':     costo_cemento,
        'costo_mixto':       costo_mixto,
        'costo_v38':         costo_v38,
        'costo_grafil':      costo_grafil,
        'costo_alambre':     costo_alambre,
        'costo_pena':        costo_pena,
        'costo_mo':          costo_mo,
        'costo_acarreo':     costo_acarreo,
        'costo_materiales':  costo_materiales,
        'costo_directo':     costo_directo,
        'gastos_indirectos': gastos_indirectos,
        'costo_total':       costo_total,
        'pct_indirectos':    pct_indirectos,
    }


# ════════════════════════════════════════════════════════════
#  FUNCIONES DE DIBUJO TÉCNICO
# ════════════════════════════════════════════════════════════

# Paleta de colores para los dibujos técnicos.
# FONDO es para matplotlib — no cambia con el tema de Streamlit.
GRIS_CONCRETO = "#B0B0B0"
GRIS_OSCURO   = "#606060"
AZUL_COTA     = "#1565C0"
ROJO_ACENTO   = "#C62828"
FONDO         = "#F5F5F0"   # fondo claro fijo para exportar PNG
LINEA_CORTE   = "#455A64"


# MEJORA 4 (sugerencia): nombre más descriptivo para la función de cotas
def _dibujar_cota(ax, x1, y1, x2, y2, texto, offset=0.08, color=AZUL_COTA, fontsize=7.5):
    """Dibuja una cota (dimensión con flechas) entre dos puntos."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.2))
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if abs(x2 - x1) > abs(y2 - y1):   # cota horizontal → offset vertical
        ax.text(mx, my + offset, texto, ha='center', va='bottom',
                fontsize=fontsize, color=color, fontweight='bold')
    else:                               # cota vertical → offset horizontal
        ax.text(mx + offset, my, texto, ha='left', va='center',
                fontsize=fontsize, color=color, fontweight='bold')


def dibujo_perfil_lateral(tipo, alt_cm, fondo_cm, anc_cm, pasos, huella_cm, contrahuella_cm):
    """
    Genera el perfil lateral (vista de lado) de la escalera.
    Muestra: losa inclinada, escalones, cotas y datos técnicos.
    """
    huella = huella_cm / 100
    contra = contrahuella_cm / 100
    alt    = alt_cm / 100
    fondo  = fondo_cm / 100

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)

    # Polígono de la losa (contorno exterior de la escalera)
    pts_ext = [(0, 0)]
    x, y = 0, 0
    for _ in range(pasos):
        pts_ext.append((x + huella, y))
        pts_ext.append((x + huella, y + contra))
        x += huella
        y += contra
    pts_ext.append((x, y))

    angle = math.atan2(alt, fondo)
    dx = -math.sin(angle) * 0.11
    dy =  math.cos(angle) * 0.11
    pts_inf = [(px + dx, py - dy) for px, py in [(0, 0), (fondo, alt)]]

    losa_poly = pts_ext + list(reversed(pts_inf))
    xs = [p[0] for p in losa_poly]
    ys = [p[1] for p in losa_poly]
    ax.fill(xs, ys, color=GRIS_CONCRETO, alpha=0.85, zorder=2)
    ax.plot(xs + [xs[0]], ys + [ys[0]], color=GRIS_OSCURO, lw=1.2, zorder=3)

    # Líneas de cada escalón
    x, y = 0, 0
    for i in range(pasos):
        ax.plot([x, x + huella], [y, y], color=GRIS_OSCURO, lw=0.8, zorder=4)
        ax.plot([x + huella, x + huella], [y, y + contra], color=GRIS_OSCURO, lw=0.8, zorder=4)
        if i % 3 == 0 or i == pasos - 1:
            ax.text(x + huella / 2, y + 0.01, str(i + 1),
                    ha='center', va='bottom', fontsize=6, color=LINEA_CORTE, zorder=5)
        x += huella
        y += contra

    # Suelo
    ax.axhline(0, color=GRIS_OSCURO, lw=1.5, zorder=1)
    ax.fill_between([-.15, fondo + .15], [-.08, -.08], [0, 0],
                    color='#9E9E9E', alpha=0.4, hatch='////', zorder=1)

    # Cotas
    margin_h = 0.18
    margin_v = 0.18
    _dibujar_cota(ax, -margin_h, 0, -margin_h, alt, f"{alt_cm:.0f} cm", offset=0.06)
    _dibujar_cota(ax, 0, -margin_v, fondo, -margin_v, f"{fondo_cm:.0f} cm", offset=0.06)
    _dibujar_cota(ax, 0, -0.06, huella, -0.06,
                  f"h={huella_cm:.1f} cm", offset=0.04, color=ROJO_ACENTO, fontsize=7)
    _dibujar_cota(ax, fondo + 0.06, 0, fondo + 0.06, contra,
                  f"c={contrahuella_cm:.1f} cm", offset=0.04, color=ROJO_ACENTO, fontsize=7)

    info = (f"Tipo: {tipo}  |  Escalones: {pasos}  |  "
            f"Huella: {huella_cm:.1f} cm  |  Contrahuella: {contrahuella_cm:.1f} cm")
    ax.text(fondo / 2, alt + 0.12, info,
            ha='center', va='bottom', fontsize=8, color=LINEA_CORTE, style='italic')

    ax.set_title("PERFIL LATERAL — Vista de Lado", fontsize=11,
                 fontweight='bold', color=GRIS_OSCURO, pad=14)
    ax.set_aspect('equal')
    ax.set_xlim(-0.35, fondo + 0.35)
    ax.set_ylim(-0.25, alt + 0.28)
    ax.axis('off')
    fig.text(0.98, 0.01, "Escaleras Pro V7.0", ha='right', va='bottom',
             fontsize=7, color='#BDBDBD')
    plt.tight_layout()
    return fig


def dibujo_planta(tipo, alt_cm, fondo_cm, anc_cm, pasos, huella_cm):
    """
    Genera la vista en planta (desde arriba) de la escalera.
    Muestra: proyección de huellas, ancho, numeración y cotas.
    """
    huella = huella_cm / 100
    anc    = anc_cm / 100
    fondo  = fondo_cm / 100

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)

    if tipo == "Recta":
        rect = patches.Rectangle((0, 0), fondo, anc,
                                  linewidth=1.5, edgecolor=GRIS_OSCURO,
                                  facecolor=GRIS_CONCRETO, alpha=0.5, zorder=2)
        ax.add_patch(rect)
        x = 0
        for i in range(pasos + 1):
            lw = 1.5 if i == 0 or i == pasos else 0.7
            ax.plot([x, x], [0, anc], color=GRIS_OSCURO, lw=lw, zorder=3)
            if i < pasos:
                ax.text(x + huella / 2, anc / 2, str(i + 1),
                        ha='center', va='center', fontsize=7, color=LINEA_CORTE, zorder=4)
            x += huella
        ax.annotate("", xy=(fondo * 0.85, anc / 2), xytext=(fondo * 0.15, anc / 2),
                    arrowprops=dict(arrowstyle="-|>", color=ROJO_ACENTO, lw=1.5, mutation_scale=14))
        ax.text(fondo / 2, anc / 2 + anc * 0.18, "SUBE →",
                ha='center', va='bottom', fontsize=8, color=ROJO_ACENTO, fontweight='bold')
        _dibujar_cota(ax, 0, -0.12, fondo, -0.12, f"{fondo_cm:.0f} cm", offset=0.06)
        _dibujar_cota(ax, -0.14, 0, -0.14, anc, f"{anc_cm:.0f} cm", offset=0.05)
        ax.set_xlim(-0.30, fondo + 0.20)
        ax.set_ylim(-0.28, anc + 0.20)

    elif tipo == "En L con abanico":
        tramo1 = pasos // 2
        tramo2 = pasos - tramo1
        long1  = tramo1 * huella
        long2  = tramo2 * huella
        r1 = patches.Rectangle((0, 0), long1, anc,
                                linewidth=1.5, edgecolor=GRIS_OSCURO,
                                facecolor=GRIS_CONCRETO, alpha=0.5, zorder=2)
        ax.add_patch(r1)
        x = 0
        for i in range(tramo1 + 1):
            ax.plot([x, x], [0, anc], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < tramo1:
                ax.text(x + huella / 2, anc / 2, str(i + 1),
                        ha='center', va='center', fontsize=7, color=LINEA_CORTE)
            x += huella
        x0_t2 = long1
        r2 = patches.Rectangle((x0_t2 - anc, 0), anc, long2,
                                linewidth=1.5, edgecolor=GRIS_OSCURO,
                                facecolor=GRIS_CONCRETO, alpha=0.6, zorder=2)
        ax.add_patch(r2)
        y = 0
        for i in range(tramo2 + 1):
            ax.plot([x0_t2 - anc, x0_t2], [y, y], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < tramo2:
                ax.text(x0_t2 - anc / 2, y + huella / 2, str(tramo1 + i + 1),
                        ha='center', va='center', fontsize=7, color=LINEA_CORTE)
            y += huella
        wedge = patches.Wedge((x0_t2 - anc, 0), anc * 0.7, 0, 90,
                               facecolor='#CFD8DC', edgecolor=GRIS_OSCURO,
                               lw=1.0, alpha=0.6, zorder=3)
        ax.add_patch(wedge)
        ax.text(x0_t2 - anc + anc * 0.35, anc * 0.35, "abanico",
                ha='center', va='center', fontsize=6.5, color=LINEA_CORTE, style='italic')
        ax.annotate("", xy=(long1 * 0.75, anc / 2), xytext=(long1 * 0.15, anc / 2),
                    arrowprops=dict(arrowstyle="-|>", color=ROJO_ACENTO, lw=1.5, mutation_scale=14))
        _dibujar_cota(ax, 0, -0.12, long1, -0.12, f"{long1 * 100:.0f} cm", offset=0.06)
        _dibujar_cota(ax, -0.14, 0, -0.14, anc, f"{anc_cm:.0f} cm", offset=0.05)
        _dibujar_cota(ax, x0_t2 + 0.06, 0, x0_t2 + 0.06, long2, f"{long2 * 100:.0f} cm", offset=0.05)
        ax.set_xlim(-0.30, long1 + 0.25)
        ax.set_ylim(-0.28, max(long2, anc) + 0.20)

    elif tipo == "En U con abanico":
        tramo  = pasos // 3
        long_t = tramo * huella
        r1 = patches.Rectangle((0, 0), long_t, anc,
                                linewidth=1.5, edgecolor=GRIS_OSCURO,
                                facecolor=GRIS_CONCRETO, alpha=0.5, zorder=2)
        ax.add_patch(r1)
        x = 0
        for i in range(tramo + 1):
            ax.plot([x, x], [0, anc], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < tramo:
                ax.text(x + huella / 2, anc / 2, str(i + 1),
                        ha='center', va='center', fontsize=6.5, color=LINEA_CORTE)
            x += huella
        x0 = long_t
        r2 = patches.Rectangle((x0 - anc, 0), anc, long_t,
                                linewidth=1.5, edgecolor=GRIS_OSCURO,
                                facecolor=GRIS_CONCRETO, alpha=0.6, zorder=2)
        ax.add_patch(r2)
        y = 0
        for i in range(tramo + 1):
            ax.plot([x0 - anc, x0], [y, y], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < tramo:
                ax.text(x0 - anc / 2, y + huella / 2, str(tramo + i + 1),
                        ha='center', va='center', fontsize=6.5, color=LINEA_CORTE)
            y += huella
        y0 = long_t
        r3 = patches.Rectangle((0, y0 - anc), long_t - anc, anc,
                                linewidth=1.5, edgecolor=GRIS_OSCURO,
                                facecolor=GRIS_CONCRETO, alpha=0.7, zorder=2)
        ax.add_patch(r3)
        x = long_t - anc
        for i in range(tramo + 1):
            ax.plot([x, x], [y0 - anc, y0], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < tramo:
                ax.text(x - huella / 2, y0 - anc / 2, str(2 * tramo + i + 1),
                        ha='center', va='center', fontsize=6.5, color=LINEA_CORTE)
            x -= huella
        for cx, cy, ang1, ang2 in [(long_t - anc, 0, 0, 90), (long_t - anc, long_t - anc, 90, 180)]:
            w = patches.Wedge((cx, cy), anc * 0.6, ang1, ang2,
                              facecolor='#CFD8DC', edgecolor=GRIS_OSCURO,
                              lw=1.0, alpha=0.6, zorder=3)
            ax.add_patch(w)
        ax.annotate("", xy=(long_t * 0.7, anc / 2), xytext=(long_t * 0.1, anc / 2),
                    arrowprops=dict(arrowstyle="-|>", color=ROJO_ACENTO, lw=1.5, mutation_scale=14))
        _dibujar_cota(ax, 0, -0.12, long_t, -0.12, f"{long_t * 100:.0f} cm", offset=0.06)
        _dibujar_cota(ax, -0.14, 0, -0.14, long_t, "alt total", offset=0.05)
        ax.set_xlim(-0.30, long_t + 0.25)
        ax.set_ylim(-0.28, long_t + 0.20)

    elif tipo == "Caracol":
        radio_ext = anc / 2
        radio_int = radio_ext * 0.25
        cx, cy    = radio_ext, radio_ext
        circ_ext  = plt.Circle((cx, cy), radio_ext,
                               color=GRIS_CONCRETO, alpha=0.5, zorder=2)
        ax.add_patch(circ_ext)
        ax.add_patch(plt.Circle((cx, cy), radio_ext,
                                fill=False, edgecolor=GRIS_OSCURO, lw=1.5, zorder=3))
        circ_int = plt.Circle((cx, cy), radio_int,
                              color='#9E9E9E', alpha=0.8, zorder=4)
        ax.add_patch(circ_int)
        ax.add_patch(plt.Circle((cx, cy), radio_int,
                                fill=False, edgecolor=GRIS_OSCURO, lw=1.5, zorder=5))
        ax.text(cx, cy, "núcleo", ha='center', va='center',
                fontsize=7, color='white', fontweight='bold', zorder=6)
        for i in range(pasos):
            angulo = math.radians(i * 360 / pasos)
            xi = cx + radio_int * math.cos(angulo)
            yi = cy + radio_int * math.sin(angulo)
            xe = cx + radio_ext * math.cos(angulo)
            ye = cy + radio_ext * math.sin(angulo)
            ax.plot([xi, xe], [yi, ye], color=GRIS_OSCURO, lw=0.8, zorder=4)
            if i % 3 == 0:
                r_txt = (radio_int + radio_ext) / 2
                ax.text(cx + r_txt * math.cos(angulo + math.radians(180 / pasos)),
                        cy + r_txt * math.sin(angulo + math.radians(180 / pasos)),
                        str(i + 1), ha='center', va='center',
                        fontsize=6, color=LINEA_CORTE, zorder=5)
        r_mid = (radio_int + radio_ext) * 0.5
        ax.annotate("", xy=(cx + r_mid * math.cos(math.radians(330)),
                            cy + r_mid * math.sin(math.radians(330))),
                    xytext=(cx + r_mid * math.cos(math.radians(310)),
                            cy + r_mid * math.sin(math.radians(310))),
                    arrowprops=dict(arrowstyle="-|>", color=ROJO_ACENTO, lw=1.5, mutation_scale=14))
        ax.text(cx, cy - radio_ext - 0.08, "giro horario",
                ha='center', fontsize=8, color=ROJO_ACENTO, fontweight='bold')
        _dibujar_cota(ax, cx, cy, cx + radio_ext, cy,
                      f"R={anc_cm / 2:.0f} cm", offset=0.05, color=AZUL_COTA)
        _dibujar_cota(ax, cx - radio_ext - 0.14, cy - radio_ext,
                      cx - radio_ext - 0.14, cy + radio_ext,
                      f"Ø={anc_cm:.0f} cm", offset=0.06)
        ax.set_xlim(-0.30, 2 * radio_ext + 0.25)
        ax.set_ylim(-0.35, 2 * radio_ext + 0.15)

    ax.set_title(f"VISTA EN PLANTA — {tipo}", fontsize=11,
                 fontweight='bold', color=GRIS_OSCURO, pad=14)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.text(0.98, 0.01, "Escaleras Pro V7.0", ha='right', va='bottom',
             fontsize=7, color='#BDBDBD')
    plt.tight_layout()
    return fig


def fig_to_bytes(fig):
    """Convierte figura matplotlib a bytes PNG para descarga."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    return buf.read()


# ════════════════════════════════════════
#  MENÚ
# ════════════════════════════════════════
st.sidebar.title("🏗️ ESCALERAS PRO V7.0")
pestana = st.sidebar.radio(
    "Sección:",
    ["🚀 Calculadora", "📐 Dibujo Técnico", "💰 Configuración de Costos", "📊 Historial"]
)

# ════════════════════════════════════════
#  CALCULADORA
# ════════════════════════════════════════
if pestana == "🚀 Calculadora":
    st.title("🚀 Presupuesto de Escalera Prefabricada")

    st.subheader("📐 Dimensiones de la Escalera")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tipo = st.selectbox("Diseño", ["Recta", "En L con abanico", "En U con abanico", "Caracol"])
    with c2:
        alt = st.number_input("Altura total (cm)", value=240.0, min_value=80.0, max_value=600.0)
    with c3:
        fondo = st.number_input("Fondo / Largo (cm)", value=300.0, min_value=60.0, max_value=800.0)
    with c4:
        anc = st.number_input("Ancho (cm)", value=100.0, min_value=60.0, max_value=300.0)

    st.session_state['ultimo_tipo']  = tipo
    st.session_state['ultimo_alt']   = alt
    st.session_state['ultimo_fondo'] = fondo
    st.session_state['ultimo_anc']   = anc

    c5, _ = st.columns([1, 3])
    with c5:
        margen = st.slider("Ganancia Deseada %", 10, 200, 50) / 100

    st.markdown("---")

    res = calcular_escalera(tipo, alt, fondo, anc)
    p   = st.session_state.precios

    # MEJORA 1: una sola llamada a la función centralizada
    costos = calcular_costos(res, p)

    precio_venta  = costos['costo_total'] * (1 + margen)
    ganancia_neta = precio_venta - costos['costo_total']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Precio de Venta",  formato_cop(precio_venta))
    m2.metric("🔨 Costo Total Obra", formato_cop(costos['costo_total']))
    m3.metric("📈 Ganancia Neta",    formato_cop(ganancia_neta))
    m4.metric("📊 Margen real",      f"{margen * 100:.0f}%")

    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("#### 📐 Datos Técnicos")
        st.write(f"• Número de escalones: **{res['pasos']}**")
        st.write(f"• Contrahuella: **{res['contrahuella']} cm**")
        st.write(f"• Huella estimada: **{res['huella']} cm**")
        st.write(f"• Longitud inclinada: **{res['long_inclinada']} m**")
        st.write(f"• Volumen concreto: **{res['vol']} m³**")
        ok_contra = 16 <= res['contrahuella'] <= 20
        ok_huella = res['huella'] >= 25
        if ok_contra and ok_huella:
            st.success("✅ Medidas dentro de norma (contrahuella 16–20 cm, huella ≥ 25 cm)")
        else:
            msgs = []
            if not ok_contra:
                msgs.append(f"Contrahuella {res['contrahuella']} cm fuera de rango 16–20 cm")
            if not ok_huella:
                msgs.append(f"Huella {res['huella']} cm menor a 25 cm mínimo")
            st.warning("⚠️ " + " | ".join(msgs))

    with col_b:
        st.markdown("#### 📦 Cantidades de Material")
        st.dataframe(pd.DataFrame({
            "Material": ["Cemento (bultos)", "Mixto (m³)", "Varilla 3/8\" (barras 6m)",
                         "Grafil 1/4\" (barras)", "Alambre (kg)", "Arena de Peña (bultos)"],
            "Cantidad": [res['bls_cemento'], res['mix_m3'], res['v38_barras'],
                         p['grafil_cant'], p['alambre_kg'], p['cant_pena']],
            "Costo":    [formato_cop(costos['costo_cemento']), formato_cop(costos['costo_mixto']),
                         formato_cop(costos['costo_v38']),     formato_cop(costos['costo_grafil']),
                         formato_cop(costos['costo_alambre']), formato_cop(costos['costo_pena'])],
        }), use_container_width=True, hide_index=True)

    with col_c:
        st.markdown("#### 💸 Desglose de Costos")
        st.write(f"• Materiales: **{formato_cop(costos['costo_materiales'])}**")
        st.write(f"• Mano de obra ({int(p['cantidad_personas'])} pers.): **{formato_cop(costos['costo_mo'])}**")
        st.write(f"• Acarreo: **{formato_cop(costos['costo_acarreo'])}**")
        st.write(f"• Costo Directo: **{formato_cop(costos['costo_directo'])}**")
        # MEJORA 3: muestra el porcentaje real configurado
        pct_display = int(p.get('gastos_indirectos_pct', 5.0))
        st.write(f"• Gastos Indirectos ({pct_display}%): **{formato_cop(costos['gastos_indirectos'])}**")
        st.markdown("---")
        st.success(f"**Costo Total: {formato_cop(costos['costo_total'])}**")
        st.info(f"**Precio Venta: {formato_cop(precio_venta)}**")

    st.markdown("---")
    cb1, cb2 = st.columns([1, 3])
    with cb1:
        if st.button("💾 GUARDAR EN HISTORIAL"):
            st.session_state.historial.append({
                "Fecha":       datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Tipo":        tipo,
                "Alto (cm)":   alt,
                "Fondo (cm)":  fondo,
                "Ancho (cm)":  anc,
                "Escalones":   res['pasos'],
                "Vol. m³":     res['vol'],
                "Costo Total": formato_cop(costos['costo_total']),
                "Precio Venta":formato_cop(precio_venta),
                "Ganancia":    formato_cop(ganancia_neta),
            })
            st.toast("✅ Guardado en historial")
    with cb2:
        st.info("💡 Ve a **📐 Dibujo Técnico** para ver el perfil lateral y planta de esta escalera.")


# ════════════════════════════════════════
#  DIBUJO TÉCNICO
# ════════════════════════════════════════
elif pestana == "📐 Dibujo Técnico":
    st.title("📐 Dibujo Técnico de Escalera")
    st.info("💡 Los valores se sincronizan automáticamente desde la Calculadora. También puedes cambiarlos aquí.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tipo_d = st.selectbox("Diseño", ["Recta", "En L con abanico", "En U con abanico", "Caracol"],
                              index=["Recta", "En L con abanico", "En U con abanico", "Caracol"].index(
                                  st.session_state.get('ultimo_tipo', 'Recta')))
    with c2:
        alt_d  = st.number_input("Altura total (cm)", value=st.session_state.get('ultimo_alt', 240.0),
                                  min_value=80.0, max_value=600.0, key="d_alt")
    with c3:
        fond_d = st.number_input("Fondo / Largo (cm)", value=st.session_state.get('ultimo_fondo', 300.0),
                                  min_value=60.0, max_value=800.0, key="d_fondo")
    with c4:
        anc_d  = st.number_input("Ancho (cm)", value=st.session_state.get('ultimo_anc', 100.0),
                                  min_value=60.0, max_value=300.0, key="d_anc")

    res_d = calcular_escalera(tipo_d, alt_d, fond_d, anc_d)

    st.markdown("---")
    tab1, tab2 = st.tabs(["📏 Perfil Lateral", "🗺️ Vista en Planta"])

    with tab1:
        st.markdown(f"**Escalera {tipo_d}** · {res_d['pasos']} escalones · "
                    f"Huella {res_d['huella']} cm · Contrahuella {res_d['contrahuella']} cm")
        # MEJORA 2: try/finally garantiza que la figura siempre se libere de memoria
        fig_lat = dibujo_perfil_lateral(
            tipo_d, alt_d, fond_d, anc_d,
            res_d['pasos'], res_d['huella'], res_d['contrahuella']
        )
        try:
            st.pyplot(fig_lat, use_container_width=True)
            st.download_button(
                "⬇️ Descargar Perfil Lateral (PNG)",
                data=fig_to_bytes(fig_lat),
                file_name=f"perfil_lateral_{tipo_d.replace(' ', '_')}.png",
                mime="image/png"
            )
        finally:
            plt.close(fig_lat)   # siempre se libera, haya error o no

    with tab2:
        st.markdown(f"**Escalera {tipo_d}** · Ancho {anc_d} cm · {res_d['pasos']} escalones")
        fig_plan = dibujo_planta(
            tipo_d, alt_d, fond_d, anc_d,
            res_d['pasos'], res_d['huella']
        )
        try:
            st.pyplot(fig_plan, use_container_width=True)
            st.download_button(
                "⬇️ Descargar Vista en Planta (PNG)",
                data=fig_to_bytes(fig_plan),
                file_name=f"planta_{tipo_d.replace(' ', '_')}.png",
                mime="image/png"
            )
        finally:
            plt.close(fig_plan)  # siempre se libera, haya error o no


# ════════════════════════════════════════
#  CONFIGURACIÓN DE COSTOS
# ════════════════════════════════════════
elif pestana == "💰 Configuración de Costos":
    st.title("💰 Configuración de Precios e Insumos")

    with st.form("form_precios"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🧱 Materiales")
            cem       = st.number_input("Bulto Cemento (COP)",           value=float(st.session_state.precios['cemento']))
            mix       = st.number_input("Mixto m³ (COP)",                value=float(st.session_state.precios['mixto']))
            var       = st.number_input("Varilla 3/8\" barra 6m (COP)",  value=float(st.session_state.precios['varilla_38']))
            graf      = st.number_input("Grafil 1/4\" barra (COP)",      value=float(st.session_state.precios['grafil_14']))
            graf_cant = st.number_input("Cantidad Grafil 1/4\" (barras)", value=int(st.session_state.precios['grafil_cant']), step=1)
            alam      = st.number_input("Alambre kg (COP)",               value=float(st.session_state.precios['alambre']))
            alam_kg   = st.number_input("Cantidad Alambre (kg)",          value=int(st.session_state.precios['alambre_kg']), step=1)
            pena      = st.number_input("Bulto Arena de Peña (COP)",      value=float(st.session_state.precios['bulto_pena']))
            cant_pena = st.number_input("Cantidad Bultos Peña",           value=int(st.session_state.precios['cant_pena']), step=1)
        with col2:
            st.subheader("👷 Mano de Obra y Logística")
            pago   = st.number_input("Pago por Persona/día (COP)", value=float(st.session_state.precios['pago_persona']))
            cant_p = st.number_input("Cantidad de Personas",       value=int(st.session_state.precios['cantidad_personas']), step=1)
            aca    = st.number_input("Costo de Acarreo (COP)",     value=float(st.session_state.precios['acarreo']))
            st.subheader("📉 Gastos Indirectos")
            # MEJORA 3: campo editable para el porcentaje de gastos indirectos
            gi_pct = st.number_input(
                "Gastos Indirectos (%)",
                value=float(st.session_state.precios.get('gastos_indirectos_pct', 5.0)),
                min_value=0.0, max_value=100.0, step=0.5,
                help="Se aplica sobre el costo directo (materiales + mano de obra + acarreo)."
            )

        if st.form_submit_button("✅ GUARDAR CAMBIOS"):
            st.session_state.precios.update({
                'cemento': cem, 'mixto': mix, 'varilla_38': var,
                'grafil_14': graf, 'grafil_cant': graf_cant,
                'alambre': alam, 'alambre_kg': alam_kg,
                'bulto_pena': pena, 'cant_pena': cant_pena,
                'pago_persona': pago, 'cantidad_personas': cant_p,
                'acarreo': aca,
                'gastos_indirectos_pct': gi_pct,   # MEJORA 3
            })
            st.success("✅ Configuración actualizada correctamente.")


# ════════════════════════════════════════
#  HISTORIAL
# ════════════════════════════════════════
else:
    st.title("📊 Historial de Presupuestos")
    if st.session_state.historial:
        df = pd.DataFrame(st.session_state.historial)
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Exportar CSV", data=csv,
                           file_name=f"historial_{datetime.now().strftime('%Y%m%d')}.csv",
                           mime='text/csv')
        if st.button("🗑️ Limpiar Historial"):
            st.session_state.historial = []
            st.rerun()
    else:
        st.info("Aún no hay presupuestos guardados. Ve a la Calculadora y guarda uno.")
