import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V3.9", page_icon="🏗️", layout="wide")

# --- INICIALIZACIÓN DE PRECIOS ---
if 'precios' not in st.session_state:
    st.session_state['precios'] = {
        'cemento': 32000.0,
        'mixto': 190000.0,
        'varilla_38': 24000.0,
        'grafil_14': 5000.0,
        'alambre': 10000.0,
        'pago_persona': 90000.0,
        'cantidad_personas': 4
    }

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

# --- MENÚ DE NAVEGACIÓN (BOTONES VISIBLES) ---
st.sidebar.title("🛠️ MENÚ PRINCIPAL")
pestana = st.sidebar.radio(
    "Seleccione una sección:",
    ["🚀 Calculadora de Obra", "💰 Configuración de Costos", "📊 Historial de Ventas"]
)

# --- SECCIÓN 1: CONFIGURACIÓN DE COSTOS ---
if pestana == "💰 Configuración de Costos":
    st.title("💰 Ajuste de Precios de Materiales y Personal")
    st.write("Modifique los valores aquí. Estos cambios afectarán a todos los cálculos nuevos.")
    
    with st.form("form_precios"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🧱 Precios de Materiales")
            cem = st.number_input("Bulto Cemento (50kg)", value=st.session_state.precios['cemento'])
            mix = st.number_input("Mixto m3 (Arena+Gravilla)", value=st.session_state.precios['mixto'])
            var = st.number_input("Varilla 3/8 (6m)", value=st.session_state.precios['varilla_38'])
            gra = st.number_input("Grafil 1/4 (6m)", value=st.session_state.precios['grafil_14'])
            ala = st.number_input("Alambre Negro (kg)", value=st.session_state.precios['alambre'])
        
        with col2:
            st.subheader("👷 Mano de Obra")
            pago = st.number_input("Pago por cada persona ($)", value=st.session_state.precios['pago_persona'])
            cant = st.number_input("Número de trabajadores", value=st.session_state.precios['cantidad_personas'], step=1)
        
        if st.form_submit_button("✅ GUARDAR Y ACTUALIZAR PRECIOS"):
            st.session_state.precios.update({
                'cemento': cem, 'mixto': mix, 'varilla_38': var,
                'grafil_14': gra, 'alambre': ala, 'pago_persona': pago,
                'cantidad_personas': cant
            })
            st.success("¡Precios actualizados! Ya puedes ir a la Calculadora.")

# --- SECCIÓN 2: CALCULADORA ---
elif pestana == "🚀 Calculadora de Obra":
    st.title("🚀 Calculadora de Escaleras")
    
    with st.sidebar.form("diseno"):
        st.header("📐 Medidas")
        tipo = st.selectbox("Tipo de Diseño", ["Recta", "En L con abanico", "En U con abanico", "Caracol"])
        alt = st.number_input("Altura total (cm)", value=240.0)
        lar = st.number_input("Fondo/Desarrollo (cm)", value=300.0)
        anc = st.number_input("Ancho escalera (cm)", value=100.0)
        margen = st.slider("Tu Ganancia %", 10, 200, 50) / 100
        st.form_submit_button("🔄 CALCULAR")

    # --- LÓGICA ---
    pasos = math.ceil(alt / 18)
    ch = alt / pasos
    huella = lar / (pasos - 1) if tipo == "Recta" else 28.0
    long_m = math.sqrt((lar/100)**2 + (alt/100)**2)
    vol = (long_m * (anc/100) * 0.11) * (1.2 if tipo != "Recta" else 1.0)
    
    # Cantidades
    bls = math.ceil(vol * 7.5)
    mix_m3 = vol * 1.1
    v38 = math.ceil(((anc/15 + 1) * long_m * 1.1) / 6)
    g14 = math.ceil(((long_m*100/20 + 1) * (anc/100) * 1.1) / 6)
    ala_kg = math.ceil(vol * 8) # Estimación rápida kg/m3
    
    # Costos desde el estado de sesión
    p = st.session_state.precios
    c_mat = (bls * p['cemento']) + (mix_m3 * p['mixto']) + (v38 * p['varilla_38']) + (g14 * p['grafil_14']) + (ala_kg * p['alambre'])
    c_mo = p['pago_persona'] * p['cantidad_personas']
    c_total = c_mat + c_mo
    venta = c_total * (1 + margen)

    # --- RESULTADOS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Pasos", pasos)
    col2.metric("Huella", f"{huella:.1f} cm")
    col3.metric("Contrahuella", f"{ch:.1f} cm")

    st.subheader("💰 Resumen Comercial")
    m1, m2, m3 = st.columns(3)
    m1.metric("PRECIO VENTA", formato_cop(venta))
    m2.metric("Costo Directo", formato_cop(c_total))
    m3.metric("Utilidad Bruta", formato_cop(venta - c_total))

    st.markdown("---")
    st.info(f"🧱 **Materiales:** {bls} bultos de cemento, {mix_m3:.2f} m3 de mixto, {v38} varillas 3/8.")
    st.success(f"👷 **Mano de Obra:** {p['cantidad_personas']} personas / Total MO: {formato_cop(c_mo)}")

# --- SECCIÓN 3: HISTORIAL ---
else:
    st.title("📊 Historial de Cotizaciones")
    if st.session_state.historial:
        st.table(pd.DataFrame(st.session_state.historial))
    else:
        st.info("No hay proyectos guardados todavía.")
