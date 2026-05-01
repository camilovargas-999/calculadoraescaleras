import streamlit as st
import math
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Escaleras Pro V5.0", page_icon="🏗️", layout="wide")

# --- ESTILOS ---
st.markdown("""
<style>
    .metric-box {
        background: #1e2a3a;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        border-left: 4px solid #00c9a7;
    }
    .metric-label { color: #aaa; font-size: 13px; }
    .metric-value { color: #fff; font-size: 22px; font-weight: bold; }
    .alert-red { background: #3a1e1e; border-left: 4px solid #e74c3c; border-radius: 8px; padding: 12px; }
    .alert-green { background: #1e3a2a; border-left: 4px solid #00c9a7; border-radius: 8px; padding: 12px; }
    .section-title { font-size: 16px; font-weight: bold; color: #00c9a7; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADO ---
if 'precios' not in st.session_state:
    st.session_state['precios'] = {
        'cemento': 32000.0,
        'mixto': 190000.0,
        'varilla_38': 24000.0,
        'grafil_14': 5000.0,
        'alambre': 10000.0,
        'pago_persona': 90000.0,
        'cantidad_personas': 4,
        'bulto_pena': 10000.0,
        'cant_pena': 2,
        'acarreo': 100000.0,
        'grafil_cant': 2,
        'alambre_kg': 1,
    }

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

def calcular_escalera(tipo, alt_cm, fondo_cm, anc_cm):
    """Cálculo técnico mejorado por tipo de escalera."""
    alt = alt_cm / 100
    fondo = fondo_cm / 100
    anc = anc_cm / 100

    # Contrahuellas y longitud inclinada
    pasos = math.ceil(alt_cm / 18)
    contrahuella = alt_cm / pasos
    huella = fondo_cm / pasos if tipo == "Recta" else max(fondo_cm / pasos, 25)

    long_inclinada = math.sqrt(fondo**2 + alt**2)

    # Volumen base (losa inclinada de ~11 cm de espesor)
    espesor = 0.11
    vol_base = long_inclinada * anc * espesor

    # Factor por tipo de escalera
    if tipo == "Recta":
        factor_vol = 1.0
    elif tipo == "En L con abanico":
        factor_vol = 1.35   # ~35% más por descanso + abanico
    elif tipo == "En U con abanico":
        factor_vol = 1.70   # ~70% más por dos tramos + descansos + abanico
    elif tipo == "Caracol":
        factor_vol = 1.50   # 50% más por núcleo central y peldaños en cuña

    vol = vol_base * factor_vol

    # Materiales
    bls_cemento = math.ceil(vol * 7.5)
    mix_m3 = round(vol * 1.1, 2)

    # Varillas 3/8: barras longitudinales (cada 15 cm de ancho) + transversales
    num_long = math.ceil(anc / 0.15) + 1
    long_barra_long = long_inclinada * 1.1   # 10% desperdicio
    barras_long = math.ceil((num_long * long_barra_long) / 6)

    # Transversales cada 20 cm
    num_trans = math.ceil(long_inclinada / 0.20)
    barras_trans = math.ceil((num_trans * anc * 1.1) / 6)
    v38 = barras_long + barras_trans

    return {
        'pasos': pasos,
        'contrahuella': round(contrahuella, 1),
        'huella': round(huella, 1),
        'long_inclinada': round(long_inclinada, 2),
        'vol': round(vol, 3),
        'bls_cemento': bls_cemento,
        'mix_m3': mix_m3,
        'v38_barras': v38,
    }

# --- MENÚ ---
st.sidebar.title("🏗️ ESCALERAS PRO V5.0")
pestana = st.sidebar.radio(
    "Sección:",
    ["🚀 Calculadora", "💰 Configuración de Costos", "📊 Historial"]
)

# ════════════════════════════════════════
#  SECCIÓN: CALCULADORA
# ════════════════════════════════════════
if pestana == "🚀 Calculadora":
    st.title("🚀 Presupuesto de Escalera Prefabricada")

    # Inputs en columnas (no enterrados en sidebar)
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

    c5, c6 = st.columns([1, 3])
    with c5:
        margen = st.slider("Ganancia Deseada %", 10, 200, 50) / 100

    st.markdown("---")

    # ── Cálculo ──
    res = calcular_escalera(tipo, alt, fondo, anc)
    p = st.session_state.precios

    # Costos
    costo_cemento  = res['bls_cemento'] * p['cemento']
    costo_mixto    = res['mix_m3'] * p['mixto']
    costo_v38      = res['v38_barras'] * p['varilla_38']
    costo_grafil   = p['grafil_cant'] * p['grafil_14']
    costo_alambre  = p['alambre_kg'] * p['alambre']
    costo_pena     = p['cant_pena'] * p['bulto_pena']
    costo_mo       = p['pago_persona'] * p['cantidad_personas']
    costo_acarreo  = p['acarreo']

    costo_materiales = costo_cemento + costo_mixto + costo_v38 + costo_grafil + costo_alambre + costo_pena
    costo_directo    = costo_materiales + costo_mo + costo_acarreo
    gastos_indirectos = costo_directo * 0.05
    costo_total      = costo_directo + gastos_indirectos
    precio_venta     = costo_total * (1 + margen)
    ganancia_neta    = precio_venta - costo_total

    # ── Métricas principales ──
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Precio de Venta", formato_cop(precio_venta))
    m2.metric("🔨 Costo Total Obra", formato_cop(costo_total))
    m3.metric("📈 Ganancia Neta", formato_cop(ganancia_neta))
    m4.metric("📊 Margen real", f"{margen*100:.0f}%")

    st.markdown("---")

    # ── Detalles ──
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("#### 📐 Datos Técnicos")
        st.write(f"• Número de escalones: **{res['pasos']}**")
        st.write(f"• Contrahuella: **{res['contrahuella']} cm**")
        st.write(f"• Huella estimada: **{res['huella']} cm**")
        st.write(f"• Longitud inclinada: **{res['long_inclinada']} m**")
        st.write(f"• Volumen concreto: **{res['vol']} m³**")

        # Validación normativa básica (NSR-10 / práctica colombiana)
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
        data_mat = {
            "Material": [
                f"Cemento (bultos)",
                f"Mixto (m³)",
                f"Varilla 3/8\" (barras 6m)",
                f"Grafil 1/4\" (barras)",
                f"Alambre (kg)",
                f"Arena de Peña (bultos)",
            ],
            "Cantidad": [
                res['bls_cemento'],
                res['mix_m3'],
                res['v38_barras'],
                p['grafil_cant'],
                p['alambre_kg'],
                p['cant_pena'],
            ],
            "Costo": [
                formato_cop(costo_cemento),
                formato_cop(costo_mixto),
                formato_cop(costo_v38),
                formato_cop(costo_grafil),
                formato_cop(costo_alambre),
                formato_cop(costo_pena),
            ]
        }
        st.dataframe(pd.DataFrame(data_mat), use_container_width=True, hide_index=True)

    with col_c:
        st.markdown("#### 💸 Desglose de Costos")
        st.write(f"• Materiales: **{formato_cop(costo_materiales)}**")
        st.write(f"• Mano de obra ({int(p['cantidad_personas'])} pers.): **{formato_cop(costo_mo)}**")
        st.write(f"• Acarreo: **{formato_cop(costo_acarreo)}**")
        st.write(f"• Costo Directo: **{formato_cop(costo_directo)}**")
        st.write(f"• Gastos Indirectos (5%): **{formato_cop(gastos_indirectos)}**")
        st.markdown("---")
        st.success(f"**Costo Total: {formato_cop(costo_total)}**")
        st.info(f"**Precio Venta: {formato_cop(precio_venta)}**")

    st.markdown("---")
    if st.button("💾 GUARDAR EN HISTORIAL"):
        st.session_state.historial.append({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Tipo": tipo,
            "Alto (cm)": alt,
            "Fondo (cm)": fondo,
            "Ancho (cm)": anc,
            "Escalones": res['pasos'],
            "Vol. m³": res['vol'],
            "Costo Total": formato_cop(costo_total),
            "Precio Venta": formato_cop(precio_venta),
            "Ganancia": formato_cop(ganancia_neta),
        })
        st.toast("✅ Guardado en historial")

# ════════════════════════════════════════
#  SECCIÓN: CONFIGURACIÓN DE COSTOS
# ════════════════════════════════════════
elif pestana == "💰 Configuración de Costos":
    st.title("💰 Configuración de Precios e Insumos")

    with st.form("form_precios"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🧱 Materiales")
            cem  = st.number_input("Bulto Cemento (COP)", value=float(st.session_state.precios['cemento']))
            mix  = st.number_input("Mixto m³ (COP)", value=float(st.session_state.precios['mixto']))
            var  = st.number_input("Varilla 3/8\" barra 6m (COP)", value=float(st.session_state.precios['varilla_38']))
            graf = st.number_input("Grafil 1/4\" barra (COP)", value=float(st.session_state.precios['grafil_14']))
            graf_cant = st.number_input("Cantidad Grafil 1/4\" (barras)", value=int(st.session_state.precios['grafil_cant']), step=1)
            alam = st.number_input("Alambre kg (COP)", value=float(st.session_state.precios['alambre']))
            alam_kg = st.number_input("Cantidad Alambre (kg)", value=int(st.session_state.precios['alambre_kg']), step=1)
            pena = st.number_input("Bulto Arena de Peña (COP)", value=float(st.session_state.precios['bulto_pena']))
            cant_pena = st.number_input("Cantidad Bultos Peña", value=int(st.session_state.precios['cant_pena']), step=1)

        with col2:
            st.subheader("👷 Mano de Obra y Logística")
            pago   = st.number_input("Pago por Persona/día (COP)", value=float(st.session_state.precios['pago_persona']))
            cant_p = st.number_input("Cantidad de Personas", value=int(st.session_state.precios['cantidad_personas']), step=1)
            aca    = st.number_input("Costo de Acarreo (COP)", value=float(st.session_state.precios['acarreo']))
            st.subheader("📉 Gastos Indirectos")
            st.info("Se aplica un **5%** fijo sobre el costo directo para Arriendo y Servicios.")

        if st.form_submit_button("✅ GUARDAR CAMBIOS"):
            st.session_state.precios.update({
                'cemento': cem, 'mixto': mix, 'varilla_38': var,
                'grafil_14': graf, 'grafil_cant': graf_cant,
                'alambre': alam, 'alambre_kg': alam_kg,
                'bulto_pena': pena, 'cant_pena': cant_pena,
                'pago_persona': pago, 'cantidad_personas': cant_p,
                'acarreo': aca,
            })
            st.success("✅ Configuración actualizada correctamente.")

# ════════════════════════════════════════
#  SECCIÓN: HISTORIAL
# ════════════════════════════════════════
else:
    st.title("📊 Historial de Presupuestos")

    if st.session_state.historial:
        df = pd.DataFrame(st.session_state.historial)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Exportar CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Exportar CSV",
            data=csv,
            file_name=f"historial_escaleras_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
        )

        if st.button("🗑️ Limpiar Historial"):
            st.session_state.historial = []
            st.rerun()
    else:
        st.info("Aún no hay presupuestos guardados. Ve a la Calculadora y guarda uno.")
