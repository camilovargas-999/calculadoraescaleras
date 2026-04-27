import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V4.0", page_icon="🏗️", layout="wide")

# --- INICIALIZACIÓN DE PRECIOS ---
if 'precios' not in st.session_state:
    st.session_state['precios'] = {
        'cemento': 32000.0,
        'mixto': 190000.0,
        'varilla_38': 24000.0,
        'grafil_14': 5000.0,
        'alambre': 10000.0,
        'pago_persona': 90000.0,
        'cantidad_personas': 4,
        'bulto_pena': 10000.0,     # Nuevo
        'cant_pena': 2,            # Nuevo
        'acarreo': 100000.0        # Nuevo
    }

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

# --- MENÚ DE NAVEGACIÓN ---
st.sidebar.title("🛠️ MENÚ PRINCIPAL")
pestana = st.sidebar.radio(
    "Seleccione una sección:",
    ["🚀 Calculadora de Obra", "💰 Configuración de Costos", "📊 Historial"]
)

# --- SECCIÓN: CONFIGURACIÓN DE COSTOS ---
if pestana == "💰 Configuración de Costos":
    st.title("💰 Configuración de Precios e Insumos")
    
    with st.form("form_precios"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🧱 Materiales Base")
            cem = st.number_input("Bulto Cemento", value=st.session_state.precios['cemento'])
            mix = st.number_input("Mixto m3", value=st.session_state.precios['mixto'])
            var = st.number_input("Varilla 3/8", value=st.session_state.precios['varilla_38'])
            st.subheader("🚚 Otros Gastos")
            pena = st.number_input("Bulto Arena de Peña", value=st.session_state.precios['bulto_pena'])
            aca = st.number_input("Costo de Acarreo", value=st.session_state.precios['acarreo'])
        
        with col2:
            st.subheader("👷 Mano de Obra")
            pago = st.number_input("Pago por Persona", value=st.session_state.precios['pago_persona'])
            cant_p = st.number_input("Cantidad de Personas", value=st.session_state.precios['cantidad_personas'], step=1)
            st.subheader("📉 Gastos Fijos")
            st.write("Se aplica un **5%** para Arriendo y Servicios sobre el costo directo.")
        
        if st.form_submit_button("✅ GUARDAR CAMBIOS"):
            st.session_state.precios.update({
                'cemento': cem, 'mixto': mix, 'varilla_38': var,
                'bulto_pena': pena, 'acarreo': aca,
                'pago_persona': pago, 'cantidad_personas': cant_p
            })
            st.success("Configuración actualizada.")

# --- SECCIÓN: CALCULADORA ---
elif pestana == "🚀 Calculadora de Obra":
    st.title("🚀 Presupuesto de Escalera")
    
    with st.sidebar.form("diseno"):
        tipo = st.selectbox("Diseño", ["Recta", "En L con abanico", "En U con abanico", "Caracol"])
        alt = st.number_input("Altura (cm)", value=240.0)
        lar = st.number_input("Fondo (cm)", value=300.0)
        anc = st.number_input("Ancho (cm)", value=100.0)
        margen = st.slider("Ganancia Deseada %", 10, 200, 50) / 100
        st.form_submit_button("🔄 CALCULAR")

    # Lógica Técnica Rápida
    pasos = math.ceil(alt / 18)
    long_m = math.sqrt((lar/100)**2 + (alt/100)**2)
    vol = (long_m * (anc/100) * 0.11) * (1.2 if tipo != "Recta" else 1.0)
    
    # Cantidades de Material
    bls = math.ceil(vol * 7.5)
    mix_m3 = vol * 1.1
    v38 = math.ceil(((anc/15 + 1) * long_m * 1.1) / 6)
    
    # --- COSTOS DESDE SESIÓN ---
    p = st.session_state.precios
    
    costo_mat_base = (bls * p['cemento']) + (mix_m3 * p['mixto']) + (v38 * p['varilla_38'])
    costo_pena = p['bulto_pena'] * p['cant_pena']
    costo_mo = p['pago_persona'] * p['cantidad_personas']
    costo_acarreo = p['acarreo']
    
    # Costo Directo (Suma de todo lo anterior)
    costo_directo = costo_mat_base + costo_pena + costo_mo + costo_acarreo
    
    # 5% Arriendo y Servicios
    gastos_operativos = costo_directo * 0.05
    
    # Costo Total Final para el Constructor
    costo_total_obra = costo_directo + gastos_operativos
    
    # Precio de Venta Final
    precio_venta = costo_total_obra * (1 + margen)

    # --- RESULTADOS ---
    r1, r2, r3 = st.columns(3)
    r1.metric("PRECIO VENTA", formato_cop(precio_venta))
    r2.metric("Inversión Total Obra", formato_cop(costo_total_obra))
    r3.metric("Ganancia Neta", formato_cop(precio_venta - costo_total_obra))

    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("📦 **Detalle de Gastos**")
        st.write(f"• Materiales Base: {formato_cop(costo_mat_base)}")
        st.write(f"• Arena de Peña (2 bultos): {formato_cop(costo_pena)}")
        st.write(f"• Acarreo: {formato_cop(costo_acarreo)}")
        st.write(f"• Mano de Obra: {formato_cop(costo_mo)}")
    
    with col_b:
        st.warning("🏠 **Gastos Indirectos**")
        st.write(f"• Arriendo y Servicios (5%): **{formato_cop(gastos_operativos)}**")
        st.write("---")
        st.success(f"**Total Invertido: {formato_cop(costo_total_obra)}**")

    if st.button("💾 GUARDAR EN HISTORIAL"):
        st.session_state.historial.append({"Tipo": tipo, "Venta": precio_venta, "Costo": costo_total_obra})
        st.toast("Guardado con éxito")

else:
    st.title("📊 Historial")
    st.table(pd.DataFrame(st.session_state.historial))
