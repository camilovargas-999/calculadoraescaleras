import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import os
import json
import sqlite3
import base64
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Image as RLImage

APP_NAME    = "Escalerapp"
APP_VERSION = "V10.0"

st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
    .metric-box { background:#1e2a3a; border-radius:10px; padding:16px; text-align:center; border-left:4px solid #00c9a7; }
    .metric-label { color:#aaa; font-size:13px; }
    .metric-value { color:#fff; font-size:22px; font-weight:bold; }
    .section-title { font-size:16px; font-weight:bold; color:#00c9a7; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)

# ── PERSISTENCIA (SQLite) ────────────────────────────────────
# Archivo local junto al script. Guarda config de precios/empresa
# e historial de cotizaciones para que no se pierdan al reiniciar
# la app o cerrar el navegador.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "escaleras_pro.db")

DEFAULT_PRECIOS = {
    'cemento': 32000, 'mixto': 190000,
    'varilla_38': 24000, 'grafil_14': 5000,
    'alambre': 10000, 'pago_persona': 90000,
    'cantidad_personas': 4, 'bulto_pena': 10000,
    'cant_pena': 2, 'acarreo': 100000,
    'grafil_cant': 2, 'alambre_kg': 1,
    'gastos_indirectos_pct': 5.0,
    'ganancia_pct': 30,
    # bloques estructurales
    'bloque_precio': 5200, 'bloque_cant': 0,
    # datos empresa
    'empresa_nombre': '', 'empresa_tel': '',
    'empresa_dir': '', 'empresa_logo': None,
    # orientación escalera
    'orientacion': 'Derecha',
}

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT, tipo TEXT,
                alto_cm INTEGER, fondo_cm INTEGER, ancho_cm INTEGER,
                escalones INTEGER, vol_m3 REAL,
                costo_total TEXT, precio_venta TEXT
            )
        """)
        conn.commit()

def cargar_precios_db():
    """Devuelve el dict de precios guardado en disco, o None si no hay nada aún."""
    with _get_conn() as conn:
        row = conn.execute("SELECT data FROM config WHERE id = 1").fetchone()
    if not row:
        return None
    data = json.loads(row[0])
    # el logo se guarda como base64 en el JSON; se reconstruye a bytes
    if data.get('empresa_logo'):
        data['empresa_logo'] = base64.b64decode(data['empresa_logo'])
    # completa con defaults cualquier clave nueva que no exista en un guardado viejo
    return {**DEFAULT_PRECIOS, **data}

def guardar_precios_db(precios: dict):
    """Persiste el dict de precios/empresa completo en disco."""
    data = dict(precios)
    if data.get('empresa_logo'):
        data['empresa_logo'] = base64.b64encode(data['empresa_logo']).decode('ascii')
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO config (id, data) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (json.dumps(data),)
        )
        conn.commit()

def cargar_historial_db():
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT fecha, tipo, alto_cm, fondo_cm, ancho_cm, escalones, "
            "vol_m3, costo_total, precio_venta FROM historial ORDER BY id"
        ).fetchall()
    return [
        {
            "Fecha": r[0], "Tipo": r[1], "Alto (cm)": r[2],
            "Fondo (cm)": r[3], "Ancho (cm)": r[4], "Escalones": r[5],
            "Vol. m³": r[6], "Costo Total": r[7], "Precio Venta": r[8],
        }
        for r in rows
    ]

def guardar_historial_db(registro: dict):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO historial (fecha, tipo, alto_cm, fondo_cm, ancho_cm, "
            "escalones, vol_m3, costo_total, precio_venta) VALUES (?,?,?,?,?,?,?,?,?)",
            (registro["Fecha"], registro["Tipo"], registro["Alto (cm)"],
             registro["Fondo (cm)"], registro["Ancho (cm)"], registro["Escalones"],
             registro["Vol. m³"], registro["Costo Total"], registro["Precio Venta"])
        )
        conn.commit()

def limpiar_historial_db():
    with _get_conn() as conn:
        conn.execute("DELETE FROM historial")
        conn.commit()

init_db()

# ── ESTADO INICIAL ──────────────────────────────────────────
# Al primer render de cada sesión, se carga lo que haya en disco
# (si no hay nada guardado todavía, se usan los valores por defecto).
if 'precios' not in st.session_state:
    st.session_state['precios'] = cargar_precios_db() or dict(DEFAULT_PRECIOS)
if 'historial' not in st.session_state:
    st.session_state['historial'] = cargar_historial_db()

# ── HELPERS ─────────────────────────────────────────────────
def fmt(valor):
    """Formato COP sin decimales ni comas: COP 1.234.567"""
    return "COP {:,.0f}".format(int(round(valor))).replace(",", ".")

def _calcular_refuerzo(pasos, anc_cm):
    """Varilla 3/8: una por paso, longitud = ancho + 12 cm. Grafil 1/4 = varillas_38 x 4."""
    long_varilla_cm = anc_cm + 12
    long_varilla_m  = long_varilla_cm / 100
    metros_totales  = pasos * long_varilla_m
    v38_barras_reales = metros_totales / 6
    v38_barras        = math.ceil(v38_barras_reales)
    grafil_cant       = v38_barras * 4
    return {
        'long_varilla_cm': long_varilla_cm,
        'v38_barras_reales': round(v38_barras_reales, 2),
        'v38_barras': v38_barras,
        'grafil_cant': grafil_cant,
    }

def _pasos_rectos(largo_cm, huella_objetivo=25, huella_min=23):
    """Pasos rectangulares por defecto a huella_objetivo cm, sin bajar de huella_min."""
    pasos = max(1, round(largo_cm / huella_objetivo))
    huella = largo_cm / pasos
    while huella < huella_min and pasos > 1:
        pasos -= 1
        huella = largo_cm / pasos
    return pasos, huella

def calcular_escalera_u(salida_cm, fondo_cm, llegada_cm, hueco_cm, alt_cm, anc_cm):
    """
    Lógica real de obra para escalera "En U con abanico":
    1. Se resta el hueco del fondo a la salida y a la llegada (el giro
       "come" ese espacio de cada tramo recto).
    2. Los tramos rectos (salida/llegada ya ajustados) se dividen en
       pasos de 25 cm de huella por defecto (mínimo 23 cm).
    3. El giro se calcula por la periferia del hueco (hueco+fondo+hueco),
       probando cantidades de pasos en abanico cuya huella quede entre
       35-70 cm Y cuya contrahuella resultante (con el total de pasos)
       quede entre 16-22 cm. Si hay varias opciones válidas, se toma la
       del medio.
    4. Contrahuella final = altura / (total_pasos + 1).
    """
    salida_aj  = salida_cm  - hueco_cm
    llegada_aj = llegada_cm - hueco_cm

    pasos_salida,  huella_salida  = _pasos_rectos(max(salida_aj, 1))
    pasos_llegada, huella_llegada = _pasos_rectos(max(llegada_aj, 1))

    periferia = hueco_cm + fondo_cm + hueco_cm

    def _contrahuella_para(n_giro):
        total = pasos_salida + n_giro + pasos_llegada
        return alt_cm / (total + 1)

    candidatos_estrictos = []
    candidatos_solo_huella = []
    for n in range(2, 21):
        huella_giro = periferia / n
        if not (35 <= huella_giro <= 70):
            continue
        candidatos_solo_huella.append(n)
        contra = _contrahuella_para(n)
        if 16 <= contra <= 22:
            candidatos_estrictos.append(n)

    ajuste_relajado = False
    if candidatos_estrictos:
        candidatos_estrictos.sort()
        n_giro = candidatos_estrictos[len(candidatos_estrictos) // 2]  # valor mediano
    elif candidatos_solo_huella:
        # No hay ninguna opción que cumpla huella Y contrahuella a la vez:
        # se prioriza la huella del giro (35-70) y se elige la que deje
        # la contrahuella más cercana al rango 16-22.
        ajuste_relajado = True
        candidatos_solo_huella.sort(
            key=lambda n: min(abs(_contrahuella_para(n) - 16), abs(_contrahuella_para(n) - 22))
            if not (16 <= _contrahuella_para(n) <= 22) else 0
        )
        n_giro = candidatos_solo_huella[0]
    else:
        # Caso extremo: ninguna cantidad de pasos deja la huella del giro
        # entre 35-70 cm con este hueco/fondo. Se usa el valor más cercano
        # al centro del rango (52.5 cm) como último recurso.
        ajuste_relajado = True
        n_giro = max(2, round(periferia / 52.5))

    huella_giro   = periferia / n_giro
    pasos         = pasos_salida + n_giro + pasos_llegada
    contrahuella  = alt_cm / (pasos + 1)

    huella_giro_ok  = 35 <= huella_giro <= 70
    contrahuella_ok = 16 <= contrahuella <= 22

    # ── Volumen: se aproxima con el recorrido horizontal total (salida+fondo+llegada) ──
    alt   = alt_cm / 100
    anc   = anc_cm / 100
    recorrido_horizontal = (salida_cm + fondo_cm + llegada_cm) / 100
    long_inclinada = math.sqrt(recorrido_horizontal**2 + alt**2)
    espesor = 0.055
    vol = long_inclinada * anc * espesor * 1.70  # mismo factor empírico usado antes para "En U"

    bls_cemento = math.ceil(vol * 7.5)
    mix_m3      = round(vol * 1.1, 2)

    refuerzo = _calcular_refuerzo(pasos, anc_cm)

    return {
        'pasos': pasos,
        'pasos_salida': pasos_salida, 'pasos_giro': n_giro, 'pasos_llegada': pasos_llegada,
        'huella_salida': round(huella_salida, 1),
        'huella_giro': round(huella_giro, 1),
        'huella_llegada': round(huella_llegada, 1),
        'huella': round(huella_giro, 1),  # valor "principal" para compatibilidad con el resto de la app
        'contrahuella': round(contrahuella, 1),
        'long_inclinada': round(long_inclinada, 2),
        'vol': round(vol, 3),
        'bls_cemento': bls_cemento,
        'mix_m3': mix_m3,
        'huella_ok': huella_salida >= 23 and huella_llegada >= 23,
        'huella_giro_ok': huella_giro_ok,
        'contrahuella_ok': contrahuella_ok,
        'ajuste_relajado': ajuste_relajado,
        **refuerzo,
    }

def calcular_escalera(tipo, alt_cm, fondo_cm, anc_cm):
    """
    Lógica de cálculo v9.
    - Pasos base = round(fondo / 25); contrahuella usa pasos+1 (cambio #4)
    - Huella mínima 23 cm
    - Volumen recta: losa horizontal + losa vertical (cambio #7)
    - Varillas 3/8: una por paso, longitud = ancho + 12 cm (cambio #6)
    - Grafil 1/4: varillas_38 × 4 (cambio #8)
    """
    pasos, huella = _pasos_rectos(fondo_cm)

    # Cambio #4: contrahuella se divide entre pasos+1
    contrahuella = alt_cm / (pasos + 1)

    alt   = alt_cm  / 100
    fondo = fondo_cm / 100
    anc   = anc_cm  / 100

    long_inclinada = math.sqrt(fondo**2 + alt**2)

    # ── Volumen ──
    espesor = 0.055  # 5.5 cm

    if tipo == "Recta":
        # Cambio #7: vol_horizontal + vol_vertical
        vol_horizontal = fondo * anc * espesor
        vol_vertical   = alt   * anc * espesor
        vol = vol_horizontal + vol_vertical
    else:
        # Otros tipos: losa inclinada con factores
        vol_base = long_inclinada * anc * espesor
        factores = {"En L con abanico": 1.35,
                    "En U con abanico": 1.70, "Caracol": 1.50}
        vol = vol_base * factores.get(tipo, 1.0)

    bls_cemento = math.ceil(vol * 7.5)
    mix_m3      = round(vol * 1.1, 2)

    refuerzo = _calcular_refuerzo(pasos, anc_cm)

    return {
        'pasos': pasos,
        'contrahuella': round(contrahuella, 1),
        'huella': round(huella, 1),
        'long_inclinada': round(long_inclinada, 2),
        'vol': round(vol, 3),
        'bls_cemento': bls_cemento,
        'mix_m3': mix_m3,
        'huella_ok': huella >= 23,
        **refuerzo,
    }

def calcular_costos(res, p):
    costo_cemento  = res['bls_cemento']  * p['cemento']
    costo_mixto    = res['mix_m3']       * p['mixto']
    costo_v38      = res['v38_barras']   * p['varilla_38']
    costo_grafil   = res['grafil_cant']  * p['grafil_14']   # grafil viene del cálculo
    costo_alambre  = p['alambre_kg']     * p['alambre']
    costo_pena     = p['cant_pena']      * p['bulto_pena']
    costo_bloque   = p['bloque_cant']    * p['bloque_precio']
    costo_mo       = p['pago_persona']   * p['cantidad_personas']
    costo_acarreo  = p['acarreo']

    costo_materiales  = (costo_cemento + costo_mixto + costo_v38 +
                         costo_grafil + costo_alambre + costo_pena + costo_bloque)
    costo_directo     = costo_materiales + costo_mo + costo_acarreo
    pct_ind           = p.get('gastos_indirectos_pct', 5.0) / 100
    gastos_indirectos = costo_directo * pct_ind
    costo_total       = costo_directo + gastos_indirectos
    margen            = p.get('ganancia_pct', 50) / 100
    precio_venta      = costo_total * (1 + margen)

    return {
        'costo_cemento': costo_cemento, 'costo_mixto': costo_mixto,
        'costo_v38': costo_v38, 'costo_grafil': costo_grafil,
        'costo_alambre': costo_alambre, 'costo_pena': costo_pena,
        'costo_bloque': costo_bloque,
        'costo_mo': costo_mo, 'costo_acarreo': costo_acarreo,
        'costo_materiales': costo_materiales, 'costo_directo': costo_directo,
        'gastos_indirectos': gastos_indirectos, 'costo_total': costo_total,
        'precio_venta': precio_venta, 'pct_ind': pct_ind,
    }

# ── DIBUJO TÉCNICO ──────────────────────────────────────────
GRIS_CONCRETO = "#B0B0B0"
GRIS_OSCURO   = "#606060"
AZUL_COTA     = "#1565C0"
ROJO_ACENTO   = "#C62828"
FONDO         = "#F5F5F0"
LINEA_CORTE   = "#455A64"

def _dibujar_cota(ax, x1, y1, x2, y2, texto, offset=0.08, color=AZUL_COTA, fontsize=7.5):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.2))
    mx, my = (x1+x2)/2, (y1+y2)/2
    if abs(x2-x1) > abs(y2-y1):
        ax.text(mx, my+offset, texto, ha='center', va='bottom',
                fontsize=fontsize, color=color, fontweight='bold')
    else:
        ax.text(mx+offset, my, texto, ha='left', va='center',
                fontsize=fontsize, color=color, fontweight='bold')

def dibujo_perfil_lateral(tipo, alt_cm, fondo_cm, anc_cm, pasos, huella_cm, contrahuella_cm):
    huella = huella_cm / 100
    contra = contrahuella_cm / 100
    alt    = alt_cm / 100
    fondo  = fondo_cm / 100
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    # Nota: contrahuella = alt / (pasos+1), es decir hay un contrapaso
    # de arranque además de los 'pasos' escalones. Se dibuja primero
    # ese contrapaso inicial para que el perfil llegue a la altura 'alt'.
    pts_ext = [(0, 0), (0, contra)]
    x, y = 0, contra
    for _ in range(pasos):
        pts_ext.append((x+huella, y))
        pts_ext.append((x+huella, y+contra))
        x += huella; y += contra
    pts_ext.append((x, y))
    angle = math.atan2(alt, fondo)
    dx = -math.sin(angle)*0.11; dy = math.cos(angle)*0.11
    pts_inf = [(px+dx, py-dy) for px, py in [(0,0),(fondo,alt)]]
    losa = pts_ext + list(reversed(pts_inf))
    xs = [p[0] for p in losa]; ys = [p[1] for p in losa]
    ax.fill(xs, ys, color=GRIS_CONCRETO, alpha=0.85, zorder=2)
    ax.plot(xs+[xs[0]], ys+[ys[0]], color=GRIS_OSCURO, lw=1.2, zorder=3)
    ax.plot([0, 0], [0, contra], color=GRIS_OSCURO, lw=0.8, zorder=4)  # contrapaso de arranque
    x, y = 0, contra
    for i in range(pasos):
        ax.plot([x, x+huella], [y, y], color=GRIS_OSCURO, lw=0.8, zorder=4)
        ax.plot([x+huella, x+huella], [y, y+contra], color=GRIS_OSCURO, lw=0.8, zorder=4)
        if i % 3 == 0 or i == pasos-1:
            ax.text(x+huella/2, y+0.01, str(i+1), ha='center', va='bottom',
                    fontsize=6, color=LINEA_CORTE, zorder=5)
        x += huella; y += contra
    ax.axhline(0, color=GRIS_OSCURO, lw=1.5, zorder=1)
    ax.fill_between([-.15, fondo+.15], [-.08,-.08], [0,0],
                    color='#9E9E9E', alpha=0.4, hatch='////', zorder=1)
    _dibujar_cota(ax, -0.18, 0, -0.18, alt, f"{alt_cm:.0f} cm", offset=0.06)
    _dibujar_cota(ax, 0, -0.18, fondo, -0.18, f"{fondo_cm:.0f} cm", offset=0.06)
    _dibujar_cota(ax, 0, -0.06, huella, -0.06,
                  f"h={huella_cm:.0f} cm", offset=0.04, color=ROJO_ACENTO, fontsize=7)
    _dibujar_cota(ax, fondo+0.06, 0, fondo+0.06, contra,
                  f"c={contrahuella_cm:.0f} cm", offset=0.04, color=ROJO_ACENTO, fontsize=7)
    info = (f"Tipo: {tipo}  |  Escalones: {pasos}  |  "
            f"Huella: {huella_cm:.0f} cm  |  Contrahuella: {contrahuella_cm:.0f} cm")
    ax.text(fondo/2, alt+0.12, info, ha='center', va='bottom',
            fontsize=8, color=LINEA_CORTE, style='italic')
    ax.set_title("PERFIL LATERAL — Vista de Lado", fontsize=11,
                 fontweight='bold', color=GRIS_OSCURO, pad=14)
    ax.set_aspect('equal')
    ax.set_xlim(-0.35, fondo+0.35); ax.set_ylim(-0.25, alt+0.28)
    ax.axis('off')
    fig.text(0.98, 0.01, f"{APP_NAME} {APP_VERSION}", ha='right', va='bottom',
             fontsize=7, color='#BDBDBD')
    plt.tight_layout()
    return fig

def dibujo_planta(tipo, alt_cm, fondo_cm, anc_cm, pasos, huella_cm, orientacion="Derecha", u_segmentos=None):
    huella = huella_cm / 100
    anc    = anc_cm / 100
    fondo  = fondo_cm / 100
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(FONDO); ax.set_facecolor(FONDO)

    if tipo == "Recta":
        ax.add_patch(patches.Rectangle((0,0), fondo, anc, linewidth=1.5,
                     edgecolor=GRIS_OSCURO, facecolor=GRIS_CONCRETO, alpha=0.5, zorder=2))
        x = 0
        for i in range(pasos+1):
            lw = 1.5 if i == 0 or i == pasos else 0.7
            ax.plot([x,x], [0,anc], color=GRIS_OSCURO, lw=lw, zorder=3)
            if i < pasos:
                ax.text(x+huella/2, anc/2, str(i+1), ha='center', va='center',
                        fontsize=7, color=LINEA_CORTE, zorder=4)
            x += huella
        ax.annotate("", xy=(fondo*0.85, anc/2), xytext=(fondo*0.15, anc/2),
                    arrowprops=dict(arrowstyle="-|>", color=ROJO_ACENTO, lw=1.5, mutation_scale=14))
        ax.text(fondo/2, anc/2+anc*0.18, "SUBE →", ha='center', va='bottom',
                fontsize=8, color=ROJO_ACENTO, fontweight='bold')
        _dibujar_cota(ax, 0,-0.12, fondo,-0.12, f"{fondo_cm:.0f} cm", offset=0.06)
        _dibujar_cota(ax, -0.14,0, -0.14,anc, f"{anc_cm:.0f} cm", offset=0.05)
        ax.set_xlim(-0.30, fondo+0.20); ax.set_ylim(-0.28, anc+0.20)

    elif tipo == "En L con abanico":
        t1 = pasos//2; t2 = pasos-t1
        l1 = t1*huella; l2 = t2*huella
        ax.add_patch(patches.Rectangle((0,0), l1, anc, linewidth=1.5,
                     edgecolor=GRIS_OSCURO, facecolor=GRIS_CONCRETO, alpha=0.5, zorder=2))
        x = 0
        for i in range(t1+1):
            ax.plot([x,x],[0,anc], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < t1:
                ax.text(x+huella/2, anc/2, str(i+1), ha='center', va='center',
                        fontsize=7, color=LINEA_CORTE)
            x += huella
        x0 = l1
        ax.add_patch(patches.Rectangle((x0-anc,0), anc, l2, linewidth=1.5,
                     edgecolor=GRIS_OSCURO, facecolor=GRIS_CONCRETO, alpha=0.6, zorder=2))
        y = 0
        for i in range(t2+1):
            ax.plot([x0-anc,x0],[y,y], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < t2:
                ax.text(x0-anc/2, y+huella/2, str(t1+i+1), ha='center', va='center',
                        fontsize=7, color=LINEA_CORTE)
            y += huella
        ax.add_patch(patches.Wedge((x0-anc,0), anc*0.7, 0, 90,
                     facecolor='#CFD8DC', edgecolor=GRIS_OSCURO, lw=1.0, alpha=0.6, zorder=3))
        ax.text(x0-anc+anc*0.35, anc*0.35, "abanico", ha='center', va='center',
                fontsize=6.5, color=LINEA_CORTE, style='italic')
        ax.annotate("", xy=(l1*0.75, anc/2), xytext=(l1*0.15, anc/2),
                    arrowprops=dict(arrowstyle="-|>", color=ROJO_ACENTO, lw=1.5, mutation_scale=14))
        _dibujar_cota(ax, 0,-0.12, l1,-0.12, f"{l1*100:.0f} cm", offset=0.06)
        _dibujar_cota(ax, -0.14,0, -0.14,anc, f"{anc_cm:.0f} cm", offset=0.05)
        _dibujar_cota(ax, x0+0.06,0, x0+0.06,l2, f"{l2*100:.0f} cm", offset=0.05)
        ax.set_xlim(-0.30, l1+0.25); ax.set_ylim(-0.28, max(l2,anc)+0.20)

    elif tipo == "En U con abanico":
        if u_segmentos:
            t1 = max(1, u_segmentos['pasos_salida'])
            t2 = max(1, u_segmentos['pasos_giro'])
            t3 = max(1, u_segmentos['pasos_llegada'])
            h1 = u_segmentos['huella_salida'] / 100
            h2 = u_segmentos['huella_giro'] / 100
            h3 = u_segmentos['huella_llegada'] / 100
        else:
            # Sin datos reales de tramo: aproximación anterior (partes iguales)
            t1 = t2 = t3 = max(1, pasos // 3)
            h1 = h2 = h3 = huella

        l1, l2, l3 = t1*h1, t2*h2, t3*h3   # salida, giro, llegada
        x0, y0 = l1, l2

        # Tramo 1: salida (horizontal, abajo)
        ax.add_patch(patches.Rectangle((0, 0), l1, anc, linewidth=1.5,
                     edgecolor=GRIS_OSCURO, facecolor=GRIS_CONCRETO, alpha=0.5, zorder=2))
        x = 0
        for i in range(t1 + 1):
            ax.plot([x, x], [0, anc], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < t1:
                ax.text(x + h1/2, anc/2, str(i+1), ha='center', va='center',
                        fontsize=6.5, color=LINEA_CORTE)
            x += h1

        # Tramo 2: giro (vertical, a la derecha) — pasos en abanico
        ax.add_patch(patches.Rectangle((x0-anc, 0), anc, l2, linewidth=1.5,
                     edgecolor=GRIS_OSCURO, facecolor=GRIS_CONCRETO, alpha=0.6, zorder=2))
        y = 0
        for i in range(t2 + 1):
            ax.plot([x0-anc, x0], [y, y], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < t2:
                ax.text(x0-anc/2, y + h2/2, str(t1+i+1), ha='center', va='center',
                        fontsize=6.5, color=LINEA_CORTE)
            y += h2

        # Tramo 3: llegada (horizontal, arriba, regresa hacia la izquierda)
        x3_ini = x0 - anc
        ax.add_patch(patches.Rectangle((x3_ini - l3, y0-anc), l3, anc, linewidth=1.5,
                     edgecolor=GRIS_OSCURO, facecolor=GRIS_CONCRETO, alpha=0.7, zorder=2))
        x = x3_ini
        for i in range(t3 + 1):
            ax.plot([x, x], [y0-anc, y0], color=GRIS_OSCURO, lw=0.7, zorder=3)
            if i < t3:
                ax.text(x - h3/2, y0-anc/2, str(t1+t2+i+1), ha='center', va='center',
                        fontsize=6.5, color=LINEA_CORTE)
            x -= h3

        for cx, cy, a1, a2 in [(x0-anc, 0, 0, 90), (x0-anc, y0-anc, 90, 180)]:
            ax.add_patch(patches.Wedge((cx, cy), anc*0.6, a1, a2,
                         facecolor='#CFD8DC', edgecolor=GRIS_OSCURO, lw=1.0, alpha=0.6, zorder=3))

        ax.annotate("", xy=(l1*0.75, anc/2), xytext=(l1*0.1, anc/2),
                    arrowprops=dict(arrowstyle="-|>", color=ROJO_ACENTO, lw=1.5, mutation_scale=14))

        _dibujar_cota(ax, 0, -0.12, l1, -0.12, f"salida {l1*100:.0f} cm", offset=0.06)
        _dibujar_cota(ax, -0.14, 0, -0.14, l2, f"giro {l2*100:.0f} cm", offset=0.05)
        _dibujar_cota(ax, x3_ini-l3, y0+0.06, x3_ini, y0+0.06, f"llegada {l3*100:.0f} cm", offset=0.05)

        min_x = min(0, x3_ini - l3) - 0.30
        max_x = x0 + 0.25
        ax.set_xlim(min_x, max_x); ax.set_ylim(-0.28, y0+0.28)

    elif tipo == "Caracol":
        re_ = anc/2; ri_ = re_*0.25; cx, cy = re_, re_
        ax.add_patch(plt.Circle((cx,cy), re_, color=GRIS_CONCRETO, alpha=0.5, zorder=2))
        ax.add_patch(plt.Circle((cx,cy), re_, fill=False, edgecolor=GRIS_OSCURO, lw=1.5, zorder=3))
        ax.add_patch(plt.Circle((cx,cy), ri_, color='#9E9E9E', alpha=0.8, zorder=4))
        ax.add_patch(plt.Circle((cx,cy), ri_, fill=False, edgecolor=GRIS_OSCURO, lw=1.5, zorder=5))
        ax.text(cx, cy, "núcleo", ha='center', va='center',
                fontsize=7, color='white', fontweight='bold', zorder=6)
        for i in range(pasos):
            ang = math.radians(i*360/pasos)
            ax.plot([cx+ri_*math.cos(ang), cx+re_*math.cos(ang)],
                    [cy+ri_*math.sin(ang), cy+re_*math.sin(ang)],
                    color=GRIS_OSCURO, lw=0.8, zorder=4)
            if i % 3 == 0:
                rm = (ri_+re_)/2
                ax.text(cx+rm*math.cos(ang+math.radians(180/pasos)),
                        cy+rm*math.sin(ang+math.radians(180/pasos)),
                        str(i+1), ha='center', va='center',
                        fontsize=6, color=LINEA_CORTE, zorder=5)
        rm2 = (ri_+re_)*0.5
        ax.annotate("", xy=(cx+rm2*math.cos(math.radians(330)),
                             cy+rm2*math.sin(math.radians(330))),
                    xytext=(cx+rm2*math.cos(math.radians(310)),
                            cy+rm2*math.sin(math.radians(310))),
                    arrowprops=dict(arrowstyle="-|>", color=ROJO_ACENTO, lw=1.5, mutation_scale=14))
        ax.text(cx, cy-re_-0.08, "giro horario" if orientacion == "Derecha" else "giro antihorario",
                ha='center', fontsize=8, color=ROJO_ACENTO, fontweight='bold')
        _dibujar_cota(ax, cx, cy, cx+re_, cy, f"R={anc_cm/2:.0f} cm", offset=0.05, color=AZUL_COTA)
        _dibujar_cota(ax, cx-re_-0.14, cy-re_, cx-re_-0.14, cy+re_, f"D={anc_cm:.0f} cm", offset=0.06)
        ax.set_xlim(-0.30, 2*re_+0.25); ax.set_ylim(-0.35, 2*re_+0.15)

    ax.set_title(f"VISTA EN PLANTA — {tipo}", fontsize=11,
                 fontweight='bold', color=GRIS_OSCURO, pad=14)
    ax.set_aspect('equal'); ax.axis('off')
    if tipo != "Caracol" and orientacion == "Izquierda":
        ax.invert_xaxis()  # espeja el plano para reflejar el giro hacia la izquierda
    fig.text(0.98, 0.01, f"{APP_NAME} {APP_VERSION}", ha='right', va='bottom',
             fontsize=7, color='#BDBDBD')
    plt.tight_layout()
    return fig

def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    return buf.read()

# ── GENERADOR DE PDF ─────────────────────────────────────────
def generar_pdf(cliente, telefono, direccion, notas, tipo, res, costos, p, orientacion):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    azul   = colors.HexColor("#1565C0")
    gris   = colors.HexColor("#455A64")
    verde  = colors.HexColor("#00796B")

    st_titulo  = ParagraphStyle('t', parent=styles['Title'],
                                fontSize=18, textColor=azul, spaceAfter=2)
    st_sub     = ParagraphStyle('s', parent=styles['Normal'],
                                fontSize=10, textColor=gris, spaceAfter=4)
    st_bold    = ParagraphStyle('b', parent=styles['Normal'],
                                fontSize=10, fontName='Helvetica-Bold', spaceAfter=2)
    st_normal  = ParagraphStyle('n', parent=styles['Normal'],
                                fontSize=10, spaceAfter=2)
    st_center  = ParagraphStyle('c', parent=styles['Normal'],
                                fontSize=9, alignment=TA_CENTER, textColor=gris)
    st_precio  = ParagraphStyle('p', parent=styles['Normal'],
                                fontSize=16, fontName='Helvetica-Bold',
                                textColor=verde, alignment=TA_CENTER, spaceAfter=4)

    story = []
    emp   = p  # alias

    # ── ENCABEZADO EMPRESA ──
    header_data = []
    logo_cell   = ""
    if emp.get('empresa_logo'):
        try:
            logo_buf = io.BytesIO(emp['empresa_logo'])
            logo_img = RLImage(logo_buf, width=3*cm, height=3*cm)
            logo_cell = logo_img
        except Exception:
            logo_cell = ""

    nombre_emp = emp.get('empresa_nombre', APP_NAME) or APP_NAME
    tel_emp    = emp.get('empresa_tel', '')
    dir_emp    = emp.get('empresa_dir', '')

    info_emp = [
        Paragraph(f"<b>{nombre_emp}</b>", ParagraphStyle('emp', fontSize=14,
                  textColor=azul, fontName='Helvetica-Bold')),
    ]
    if tel_emp:
        info_emp.append(Paragraph(f"Tel: {tel_emp}", st_normal))
    if dir_emp:
        info_emp.append(Paragraph(f"Dir: {dir_emp}", st_normal))
    info_emp.append(Paragraph(
        f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", st_sub))

    if logo_cell:
        header_data = [[logo_cell, info_emp]]
        col_widths  = [3.5*cm, None]
    else:
        header_data = [[info_emp]]
        col_widths  = [None]

    header_tbl = Table(header_data, colWidths=col_widths)
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_tbl)
    story.append(HRFlowable(width="100%", thickness=1.5, color=azul, spaceAfter=10))

    # ── TÍTULO COTIZACIÓN ──
    story.append(Paragraph("COTIZACIÓN DE ESCALERA", st_titulo))
    story.append(Spacer(1, 6))

    # ── DATOS CLIENTE ──
    story.append(Paragraph("Datos del cliente", ParagraphStyle('h2', fontSize=11,
                 fontName='Helvetica-Bold', textColor=azul, spaceAfter=4)))
    cliente_data = [
        ["Nombre:",    cliente],
        ["Teléfono:",  telefono],
        ["Dirección:", direccion],
    ]
    ct = Table(cliente_data, colWidths=[3.5*cm, None])
    ct.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TEXTCOLOR', (0,0), (0,-1), gris),
    ]))
    story.append(ct)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=gris, spaceAfter=8))

    # ── DATOS TÉCNICOS ──
    story.append(Paragraph("Especificaciones técnicas", ParagraphStyle('h2', fontSize=11,
                 fontName='Helvetica-Bold', textColor=azul, spaceAfter=4)))

    ori_texto = ""
    if tipo != "Recta":
        ori_texto = f"   |   Orientación: {orientacion}"

    tec_data = [
        ["Tipo de escalera:", tipo],
    ]
    if tipo == "En U con abanico" and res.get('pasos_salida') is not None:
        tec_data += [
            ["Pasos salida / giro / llegada:",
             f"{res['pasos_salida']} + {res['pasos_giro']} + {res['pasos_llegada']} = {res['pasos']}"],
            ["Huella salida / giro / llegada:",
             f"{res['huella_salida']:.0f} / {res['huella_giro']:.0f} / {res['huella_llegada']:.0f} cm"],
        ]
    else:
        tec_data.append(["Número de escalones:", str(res['pasos'])])
        tec_data.append(["Huella (ancho del paso):", f"{res['huella']:.0f} cm"])
    tec_data += [
        ["Contrahuella (altura del paso):", f"{res['contrahuella']:.0f} cm"],
        ["Longitud inclinada:", f"{res['long_inclinada']} m"],
        ["Volumen de concreto:", f"{res['vol']} m³"],
    ]
    if tipo != "Recta":
        tec_data.append(["Orientación:", orientacion])

    tt = Table(tec_data, colWidths=[6*cm, None])
    tt.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TEXTCOLOR', (0,0), (0,-1), gris),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor("#F5F5F5")]),
    ]))
    story.append(tt)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=gris, spaceAfter=8))

    # ── PRECIO FINAL ──
    story.append(Paragraph("Precio de venta", ParagraphStyle('h2', fontSize=11,
                 fontName='Helvetica-Bold', textColor=azul, spaceAfter=6)))
    story.append(Paragraph(fmt(costos['precio_venta']), st_precio))
    story.append(Spacer(1, 6))

    # Cambio #2: Notas / Aclaraciones
    story.append(Paragraph("Notas y aclaraciones", ParagraphStyle('h2', fontSize=11,
                 fontName='Helvetica-Bold', textColor=azul, spaceAfter=4)))
    story.append(Paragraph(notas, st_normal))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=gris, spaceAfter=6))

    # Cambio #1: validez 15 días
    story.append(Paragraph(
        "⚠️ Esta cotización tiene validez de <b>15 días calendario</b> a partir de la fecha de emisión.",
        ParagraphStyle('validez', parent=styles['Normal'], fontSize=9,
                       textColor=colors.HexColor("#B71C1C"), spaceAfter=4)))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=gris, spaceAfter=4))
    story.append(Paragraph(f"Generado por {APP_NAME} {APP_VERSION}  —  {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                           st_center))

    doc.build(story)
    buf.seek(0)
    return buf.read()

# ══════════════════════════════════════════════════════════════
#  MENÚ PRINCIPAL
# ══════════════════════════════════════════════════════════════
st.sidebar.title(f"🏗️ {APP_NAME.upper()} {APP_VERSION}")
pestana = st.sidebar.radio("Sección:", [
    "🚀 Calculadora", "📐 Dibujo Técnico",
    "📋 Catálogo de Escaleras",
    "💰 Configuración de Costos", "📊 Historial"
])

# ══════════════════════════════════════════════════════════════
#  CALCULADORA
# ══════════════════════════════════════════════════════════════
if pestana == "🚀 Calculadora":
    st.title(f"🚀 {APP_NAME} — Presupuesto de Escalera Prefabricada")
    st.subheader("📐 Dimensiones de la Escalera")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tipo = st.selectbox("Diseño", ["Recta","En L con abanico","En U con abanico","Caracol"])
    with c2:
        alt  = st.number_input("Altura total (cm)", value=240.0, min_value=80.0, max_value=600.0)

    if tipo == "En U con abanico":
        with c3:
            st.caption("↓ Para escalera en U, detalla los 3 tramos y el hueco de giro abajo")
        with c4:
            anc  = st.number_input("Ancho (cm)", value=100.0, min_value=60.0, max_value=300.0, key="u_ancho")

        st.markdown("##### 🔁 Tramos de la escalera en U (lógica real de obra)")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            salida = st.number_input("Salida (cm)", value=185.0, min_value=60.0, max_value=500.0, key="u_salida")
        with d2:
            fondo = st.number_input("Fondo / giro (cm)", value=172.0, min_value=60.0, max_value=400.0, key="u_fondo")
        with d3:
            llegada = st.number_input("Llegada (cm)", value=155.0, min_value=60.0, max_value=500.0, key="u_llegada")
        with d4:
            hueco = st.number_input("Hueco del giro (cm)", value=80.0, min_value=40.0, max_value=150.0, key="u_hueco")
    else:
        with c3:
            fondo = st.number_input("Fondo / Largo (cm)", value=300.0, min_value=60.0, max_value=800.0)
        with c4:
            anc  = st.number_input("Ancho (cm)", value=100.0, min_value=60.0, max_value=300.0)

    # Cambio #10: cantidad de bloques en dimensiones
    b1_, b2_ = st.columns([1, 3])
    with b1_:
        bloque_cant_calc = st.number_input(
            "Cantidad de bloques estructurales",
            value=int(st.session_state.precios.get('bloque_cant', 0)),
            min_value=0, step=1
        )
        st.session_state.precios['bloque_cant'] = bloque_cant_calc

    # Orientación solo para escaleras no rectas
    orientacion = st.session_state.precios.get('orientacion', 'Derecha')
    if tipo != "Recta":
        ori_col, _ = st.columns([1, 3])
        with ori_col:
            orientacion = st.radio("Orientación", ["Derecha", "Izquierda"], horizontal=True,
                                    index=["Derecha", "Izquierda"].index(orientacion), key="calc_orientacion")
            st.session_state.precios['orientacion'] = orientacion

    # Guardar para Dibujo Técnico
    st.session_state['ultimo_tipo']  = tipo
    st.session_state['ultimo_alt']   = alt
    st.session_state['ultimo_fondo'] = fondo
    st.session_state['ultimo_anc']   = anc

    st.markdown("---")
    if tipo == "En U con abanico":
        res = calcular_escalera_u(salida, fondo, llegada, hueco, alt, anc)
    else:
        res = calcular_escalera(tipo, alt, fondo, anc)
    p   = st.session_state.precios

    # Advertencia / error si huella < 23 cm después del ajuste
    if not res['huella_ok']:
        if tipo == "En U con abanico":
            st.error(f"⛔ Con estas medidas, la salida o la llegada quedan con huella menor a 23 cm "
                     f"después de restar el hueco ({hueco:.0f} cm). Aumenta salida/llegada o reduce el hueco.")
        else:
            st.error(f"⛔ Con estas dimensiones la huella mínima posible es {res['huella']:.0f} cm "
                     f"(mínimo requerido: 23 cm). Por favor aumenta el fondo de la escalera.")
        st.stop()

    if tipo == "En U con abanico" and res.get('ajuste_relajado'):
        st.warning("⚠️ No fue posible cumplir a la vez la huella del giro (35–70 cm) y la contrahuella "
                   "(16–22 cm) con estas medidas. Se usó la combinación más cercana posible — revisa "
                   "salida / fondo / llegada / hueco si quieres ajustar el resultado.")
    elif tipo != "En U con abanico" and res['huella'] < 25:
        st.warning(f"⚠️ La huella ajustada es {res['huella']:.0f} cm. "
                   f"Se recomienda mínimo 25 cm para mayor comodidad.")

    costos = calcular_costos(res, p)

    # ── 2. SOLO PRECIO DE VENTA ──
    st.metric("💰 Precio de Venta", fmt(costos['precio_venta']))

    st.markdown("---")

    # ── 3. DATOS TÉCNICOS Y MATERIALES (SIN COSTOS) ──
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 📐 Datos Técnicos")
        if tipo == "En U con abanico":
            st.write(f"• Pasos: salida **{res['pasos_salida']}** + giro **{res['pasos_giro']}** "
                     f"+ llegada **{res['pasos_llegada']}** = **{res['pasos']}** total")
            st.write(f"• Huella salida: **{res['huella_salida']:.0f} cm** · "
                     f"giro: **{res['huella_giro']:.0f} cm** · llegada: **{res['huella_llegada']:.0f} cm**")
            st.write(f"• Contrahuella: **{res['contrahuella']:.0f} cm**")
        else:
            st.write(f"• Escalones: **{res['pasos']}**")
            st.write(f"• Contrahuella: **{res['contrahuella']:.0f} cm**")
            st.write(f"• Huella: **{res['huella']:.0f} cm**")
        st.write(f"• Long. inclinada: **{res['long_inclinada']} m**")
        st.write(f"• Volumen concreto: **{res['vol']} m³**")
        if tipo != "Recta":
            st.write(f"• Orientación: **{orientacion}**")
        if tipo == "En U con abanico":
            ok_contra = res['contrahuella_ok']
            ok_huella = res['huella_giro_ok']
        else:
            ok_contra = 16 <= res['contrahuella'] <= 22
            ok_huella = res['huella'] >= 25
        if ok_contra and ok_huella:
            st.success("✅ Medidas dentro de norma")
        else:
            msgs = []
            if not ok_contra:
                msgs.append(f"Contrahuella {res['contrahuella']:.0f} cm fuera de 16–22 cm")
            if not ok_huella:
                if tipo == "En U con abanico":
                    msgs.append(f"Huella del giro {res['huella_giro']:.0f} cm fuera de 35–70 cm")
                else:
                    msgs.append(f"Huella {res['huella']:.0f} cm < 25 cm recomendado")
            st.warning("⚠️ " + " | ".join(msgs))

    with col_b:
        st.markdown("#### 📦 Materiales")
        st.caption(f"📏 Varilla 3/8\": {res['pasos']} varillas de {res['long_varilla_cm']} cm "
                   f"= {res['v38_barras_reales']} barras de 6m → se compran {res['v38_barras']}")
        st.dataframe(pd.DataFrame({
            "Material": ["Cemento (bultos)", "Mixto (m³)",
                         'Varilla 3/8" (barras 6m)',
                         'Grafil 1/4" (barras)', "Alambre (kg)",
                         "Arena de Peña (bultos)", "Bloques estructurales"],
            "Cant.": [res['bls_cemento'], res['mix_m3'], res['v38_barras'],
                      res['grafil_cant'], p['alambre_kg'], p['cant_pena'], p['bloque_cant']],
        }), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── 4. GENERAR COTIZACIÓN (PDF) ──
    st.markdown("#### 📄 Generar Cotización PDF")
    with st.form("form_cotizacion"):
        fc1, fc2 = st.columns(2)
        with fc1:
            cli_nombre = st.text_input("Nombre del cliente")
            cli_tel    = st.text_input("Teléfono")
        with fc2:
            cli_dir    = st.text_input("Dirección / Nombre del conjunto")
        # Cambio #2: campo de notas obligatorio
        cli_notas = st.text_area(
            "📝 Notas / Aclaraciones (obligatorio)",
            placeholder="Ej: Incluye instalación, escalera sin acabados, material puesto en obra, etc.",
            height=100
        )
        generar = st.form_submit_button("📄 GENERAR PDF")

    if generar:
        if not cli_nombre.strip():
            st.warning("⚠️ Ingresa el nombre del cliente.")
        elif not cli_notas.strip():
            st.warning("⚠️ El campo de notas es obligatorio. Por favor agrega una aclaración.")
        else:
            pdf_bytes = generar_pdf(
                cliente=cli_nombre, telefono=cli_tel, direccion=cli_dir,
                notas=cli_notas,
                tipo=tipo, res=res, costos=costos, p=p, orientacion=orientacion
            )
            st.download_button(
                "⬇️ Descargar Cotización PDF",
                data=pdf_bytes,
                file_name=f"cotizacion_{cli_nombre.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

    st.markdown("---")

    # ── 5. TÉCNICOS CON VALOR TOTAL Y COSTO DE LA OBRA (DESGLOSE) ──
    st.markdown("#### 🔨 Costeo de la Obra")
    st.metric("🔨 Costo Total Obra", fmt(costos['costo_total']))

    col_c = st.container()
    with col_c:
        st.markdown("#### 💸 Desglose")
        st.write(f"• Materiales: **{fmt(costos['costo_materiales'])}**")
        st.write(f"• Mano de obra ({int(p['cantidad_personas'])} pers.): **{fmt(costos['costo_mo'])}**")
        st.write(f"• Acarreo: **{fmt(costos['costo_acarreo'])}**")
        st.write(f"• Costo Directo: **{fmt(costos['costo_directo'])}**")
        pct_i = int(p.get('gastos_indirectos_pct', 5))
        st.write(f"• G. Indirectos ({pct_i}%): **{fmt(costos['gastos_indirectos'])}**")
        st.markdown("---")
        st.success(f"**Costo Total: {fmt(costos['costo_total'])}**")
        st.info(f"**Precio Venta: {fmt(costos['precio_venta'])}**")

    st.markdown("---")

    # ── 6. GUARDAR EN HISTORIAL ──
    b1, b2 = st.columns([1, 3])
    with b1:
        if st.button("💾 GUARDAR EN HISTORIAL"):
            nuevo_registro = {
                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Tipo": tipo, "Alto (cm)": int(alt),
                "Fondo (cm)": int(fondo), "Ancho (cm)": int(anc),
                "Escalones": res['pasos'], "Vol. m³": res['vol'],
                "Costo Total": fmt(costos['costo_total']),
                "Precio Venta": fmt(costos['precio_venta']),
            }
            st.session_state.historial.append(nuevo_registro)
            guardar_historial_db(nuevo_registro)
            st.toast("✅ Guardado en historial")

# ══════════════════════════════════════════════════════════════
#  DIBUJO TÉCNICO
# ══════════════════════════════════════════════════════════════
elif pestana == "📐 Dibujo Técnico":
    st.title("📐 Dibujo Técnico de Escalera")
    st.info("💡 Los valores se sincronizan desde la Calculadora. También puedes cambiarlos aquí.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tipos_lista = ["Recta","En L con abanico","En U con abanico","Caracol"]
        tipo_d = st.selectbox("Diseño", tipos_lista,
                              index=tipos_lista.index(st.session_state.get('ultimo_tipo','Recta')))
    with c2:
        alt_d  = st.number_input("Altura total (cm)", value=st.session_state.get('ultimo_alt',240.0),
                                  min_value=80.0, max_value=600.0, key="d_alt")

    if tipo_d == "En U con abanico":
        with c3:
            st.caption("↓ Detalla los 3 tramos abajo")
        with c4:
            anc_d = st.number_input("Ancho (cm)", value=st.session_state.get('ultimo_anc',100.0),
                                     min_value=60.0, max_value=300.0, key="d_u_anc")
        du1, du2, du3, du4 = st.columns(4)
        with du1:
            salida_d  = st.number_input("Salida (cm)", value=185.0, min_value=60.0, max_value=500.0, key="d_u_salida")
        with du2:
            fond_d    = st.number_input("Fondo / giro (cm)", value=172.0, min_value=60.0, max_value=400.0, key="d_u_fondo")
        with du3:
            llegada_d = st.number_input("Llegada (cm)", value=155.0, min_value=60.0, max_value=500.0, key="d_u_llegada")
        with du4:
            hueco_d   = st.number_input("Hueco del giro (cm)", value=80.0, min_value=40.0, max_value=150.0, key="d_u_hueco")
    else:
        with c3:
            fond_d = st.number_input("Fondo / Largo (cm)", value=st.session_state.get('ultimo_fondo',300.0),
                                      min_value=60.0, max_value=800.0, key="d_fondo")
        with c4:
            anc_d  = st.number_input("Ancho (cm)", value=st.session_state.get('ultimo_anc',100.0),
                                      min_value=60.0, max_value=300.0, key="d_anc")

    orientacion_d = st.session_state.precios.get('orientacion', 'Derecha')
    if tipo_d != "Recta":
        orientacion_d = st.radio("Orientación", ["Derecha", "Izquierda"], horizontal=True,
                                  index=["Derecha", "Izquierda"].index(orientacion_d), key="d_orientacion")
        st.session_state.precios['orientacion'] = orientacion_d

    if tipo_d == "En U con abanico":
        res_d = calcular_escalera_u(salida_d, fond_d, llegada_d, hueco_d, alt_d, anc_d)
    else:
        res_d = calcular_escalera(tipo_d, alt_d, fond_d, anc_d)
    if not res_d['huella_ok']:
        st.error("⛔ La huella resultante es menor a 23 cm. Aumenta el fondo.")
        st.stop()

    if tipo_d == "En U con abanico":
        fondo_perfil_d = salida_d + fond_d + llegada_d  # recorrido horizontal total, para el perfil
        u_segmentos_d = {
            'pasos_salida': res_d['pasos_salida'], 'huella_salida': res_d['huella_salida'],
            'pasos_giro': res_d['pasos_giro'], 'huella_giro': res_d['huella_giro'],
            'pasos_llegada': res_d['pasos_llegada'], 'huella_llegada': res_d['huella_llegada'],
        }
    else:
        fondo_perfil_d = fond_d
        u_segmentos_d = None

    st.markdown("---")
    tab1, tab2 = st.tabs(["📏 Perfil Lateral", "🗺️ Vista en Planta"])

    with tab1:
        st.markdown(f"**{tipo_d}** · {res_d['pasos']} escalones · "
                    f"Huella {res_d['huella']:.0f} cm · Contrahuella {res_d['contrahuella']:.0f} cm")
        fig_lat = dibujo_perfil_lateral(tipo_d, alt_d, fondo_perfil_d, anc_d,
                                        res_d['pasos'], res_d['huella'], res_d['contrahuella'])
        try:
            st.pyplot(fig_lat, use_container_width=True)
            st.download_button("⬇️ Descargar Perfil Lateral (PNG)",
                               data=fig_to_bytes(fig_lat),
                               file_name=f"perfil_{tipo_d.replace(' ','_')}.png",
                               mime="image/png")
        finally:
            plt.close(fig_lat)

    with tab2:
        st.markdown(f"**{tipo_d}** · Ancho {anc_d:.0f} cm · {res_d['pasos']} escalones")
        fig_plan = dibujo_planta(tipo_d, alt_d, fond_d, anc_d, res_d['pasos'], res_d['huella'],
                                  orientacion_d, u_segmentos_d)
        try:
            st.pyplot(fig_plan, use_container_width=True)
            st.download_button("⬇️ Descargar Vista en Planta (PNG)",
                               data=fig_to_bytes(fig_plan),
                               file_name=f"planta_{tipo_d.replace(' ','_')}.png",
                               mime="image/png")
        finally:
            plt.close(fig_plan)

# ══════════════════════════════════════════════════════════════
#  CATÁLOGO DE ESCALERAS
# ══════════════════════════════════════════════════════════════
elif pestana == "📋 Catálogo de Escaleras":
    st.title("📋 Catálogo de Escaleras Prefabricadas")
    st.markdown("Referencia de los tipos de escalera disponibles con sus características principales.")
    st.markdown("---")

    catalogo = [
        {
            "tipo": "Recta",
            "icono": "📏",
            "descripcion": "Escalera en línea recta de un solo tramo. Ideal para espacios con fondo suficiente.",
            "ventajas": ["Fácil de fabricar e instalar", "Menor costo", "Estructura más sencilla"],
            "dimensiones": "Fondo mínimo recomendado: 240 cm | Ancho mínimo: 80 cm",
            "usos": "Casas, bodegas, locales comerciales",
        },
        {
            "tipo": "En L con abanico",
            "icono": "↩️",
            "descripcion": "Escalera con un giro de 90° usando peldaños en abanico en la esquina.",
            "ventajas": ["Ocupa menos fondo que la recta", "Giro suave con abanico", "Buena para espacios esquinados"],
            "dimensiones": "Dos tramos + zona de abanico | Ancho mínimo: 90 cm",
            "usos": "Casas de dos pisos, apartamentos",
        },
        {
            "tipo": "En U con abanico",
            "icono": "↪️",
            "descripcion": "Escalera con dos giros de 90° formando una U, con abanicos en ambas esquinas.",
            "ventajas": ["Compacta en planta", "Apta para espacios cuadrados", "Elegante apariencia"],
            "dimensiones": "Tres tramos + dos abanicos | Ancho mínimo: 90 cm",
            "usos": "Edificios, casas con poco fondo disponible",
        },
        {
            "tipo": "Caracol",
            "icono": "🌀",
            "descripcion": "Escalera circular con núcleo central. Peldaños en cuña alrededor del eje.",
            "ventajas": ["Mínimo espacio en planta", "Diseño arquitectónico llamativo", "Ideal para espacios reducidos"],
            "dimensiones": "Diámetro mínimo: 120 cm | El ancho del peldaño define el diámetro",
            "usos": "Acceso a terrazas, mezzanines, espacios de diseño",
        },
    ]

    for item in catalogo:
        with st.expander(f"{item['icono']} **{item['tipo']}**", expanded=True):
            ca, cb = st.columns([2, 1])
            with ca:
                st.markdown(f"**Descripción:** {item['descripcion']}")
                st.markdown(f"**📐 Dimensiones:** {item['dimensiones']}")
                st.markdown(f"**🏠 Usos típicos:** {item['usos']}")
                st.markdown("**✅ Ventajas:**")
                for v in item['ventajas']:
                    st.markdown(f"  - {v}")
            with cb:
                # Botón para ir directo a la calculadora con ese tipo
                if st.button(f"🚀 Cotizar {item['tipo']}", key=f"cat_{item['tipo']}"):
                    st.session_state['ultimo_tipo'] = item['tipo']
                    st.info(f"Ve a 🚀 Calculadora y selecciona **{item['tipo']}**")
        st.markdown("")

    st.markdown("---")
    st.info("💡 Selecciona un tipo y haz clic en **Cotizar** para ir directamente a la calculadora con ese diseño preseleccionado.")

# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE COSTOS
# ══════════════════════════════════════════════════════════════
elif pestana == "💰 Configuración de Costos":
    st.title("💰 Configuración de Precios e Insumos")

    with st.form("form_precios"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🧱 Materiales")
            cem       = st.number_input("Bulto Cemento (COP)",            value=float(st.session_state.precios['cemento']))
            mix       = st.number_input("Mixto m³ (COP)",                 value=float(st.session_state.precios['mixto']))
            var       = st.number_input('Varilla 3/8" barra 6m (COP)',    value=float(st.session_state.precios['varilla_38']))
            graf      = st.number_input('Grafil 1/4" barra (COP)',        value=float(st.session_state.precios['grafil_14']))
            graf_cant = st.number_input(
                'Cantidad Grafil 1/4" (barras)', value=int(st.session_state.precios['grafil_cant']),
                step=1, disabled=True,
                help='Este valor es solo de referencia: la cantidad real se recalcula '
                     'automáticamente en cada cotización (4 grafiles por cada varilla de 3/8").'
            )
            alam      = st.number_input("Alambre kg (COP)",               value=float(st.session_state.precios['alambre']))
            alam_kg   = st.number_input("Cantidad Alambre (kg)",          value=int(st.session_state.precios['alambre_kg']), step=1)
            pena      = st.number_input("Bulto Arena de Peña (COP)",      value=float(st.session_state.precios['bulto_pena']))
            cant_pena = st.number_input("Cantidad Bultos Peña",           value=int(st.session_state.precios['cant_pena']), step=1)
            st.markdown("---")
            blq_precio = st.number_input("Bloque estructural (COP/und)",  value=float(st.session_state.precios.get('bloque_precio', 5200)))
            blq_cant   = st.number_input("Cantidad de bloques",           value=int(st.session_state.precios.get('bloque_cant', 0)), step=1)

        with col2:
            st.subheader("👷 Mano de Obra y Logística")
            pago   = st.number_input("Pago por Persona/día (COP)", value=float(st.session_state.precios['pago_persona']))
            cant_p = st.number_input("Cantidad de Personas",       value=int(st.session_state.precios['cantidad_personas']), step=1)
            aca    = st.number_input("Costo de Acarreo (COP)",     value=float(st.session_state.precios['acarreo']))

            st.subheader("📉 Gastos Indirectos y Ganancia")
            gi_pct = st.number_input("Gastos Indirectos (%)", min_value=0.0, max_value=100.0,
                                     value=float(st.session_state.precios.get('gastos_indirectos_pct', 5.0)),
                                     step=0.5)
            gan_pct = st.slider("Ganancia deseada (%)", 10, 200,
                                int(st.session_state.precios.get('ganancia_pct', 50)))

            st.subheader("🏢 Datos de la Empresa")
            emp_nombre = st.text_input("Nombre de la empresa",
                                       value=st.session_state.precios.get('empresa_nombre',''))
            emp_tel    = st.text_input("Teléfono de la empresa",
                                       value=st.session_state.precios.get('empresa_tel',''))
            emp_dir    = st.text_input("Dirección de la empresa",
                                       value=st.session_state.precios.get('empresa_dir',''))
            emp_logo_f = st.file_uploader("Logo de la empresa (PNG/JPG)", type=["png","jpg","jpeg"])

        if st.form_submit_button("✅ GUARDAR CAMBIOS"):
            logo_bytes = None
            if emp_logo_f is not None:
                logo_bytes = emp_logo_f.read()
            elif st.session_state.precios.get('empresa_logo'):
                logo_bytes = st.session_state.precios['empresa_logo']

            st.session_state.precios.update({
                'cemento': cem, 'mixto': mix, 'varilla_38': var,
                'grafil_14': graf, 'grafil_cant': graf_cant,
                'alambre': alam, 'alambre_kg': alam_kg,
                'bulto_pena': pena, 'cant_pena': cant_pena,
                'bloque_precio': blq_precio, 'bloque_cant': blq_cant,
                'pago_persona': pago, 'cantidad_personas': cant_p,
                'acarreo': aca, 'gastos_indirectos_pct': gi_pct,
                'ganancia_pct': gan_pct,
                'empresa_nombre': emp_nombre, 'empresa_tel': emp_tel,
                'empresa_dir': emp_dir, 'empresa_logo': logo_bytes,
            })
            guardar_precios_db(st.session_state.precios)
            st.success("✅ Configuración actualizada correctamente y guardada en disco.")

# ══════════════════════════════════════════════════════════════
#  HISTORIAL
# ══════════════════════════════════════════════════════════════
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
            limpiar_historial_db()
            st.rerun()
    else:
        st.info("Aún no hay presupuestos guardados. Ve a la Calculadora y guarda uno.")
