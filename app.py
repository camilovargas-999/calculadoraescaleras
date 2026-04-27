import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V3.7 - Mano de Obra Fija", page_icon="🏗️", layout="wide")

# --- VALORES CONFIGURADOS ---
PRECIO_CEMENTO = 32000
PRECIO_MIXTO = 190000
PRECIO_VARILLA_38 = 24000
PRECIO_GRAFIL_14 = 5000
PRECIO_ALAMBRE = 10000
PAGO_POR_PERSONA = 90000  
CANTIDAD_PERSONAS = 4

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- BARRA LATERAL ---
st.sidebar.title("Configuración Profesional")
pestana = st.sidebar.radio("Navegación:", ["Calculadora", "Historial de Ventas"])

orientacion_sel = "N/A"

with st.sidebar.form("formulario_diseño"):
    st.header("📐 Parámetros de Diseño")
    tipo_escalera = st.selectbox("Tipo de Diseño", ["Recta", "En L con abanico", "En U con abanico", "Caracol"])
    
    if tipo_escalera != "Recta":
        orientacion_sel = st.radio("Orientación (Giro)", ["Derecha 👉", "Izquierda 👈"])
    
    estilo_construccion = st.selectbox("Acabado", ["Normal", "Sin espaldar (+10%)", "Con insoluz (+10%)"])
    
    st.markdown("---")
    altura_total = st.number_input("Altura Total (cm)", value=240.0)
    largo_calc = st.number_input("Fondo/Desarrollo (cm)", value=300.0) 
    fondo_calc = st.number_input("Ancho Escalera (cm)", value=100.0)   
    
    st.markdown("---")
    margen_utilidad = st.slider("Margen de Ganancia %", 10, 100, 50) / 100
    submit_button = st.form_submit_button(label="🔄 CALCULAR TODO")

# --- LÓGICA TÉCNICA ---
ch_ideal = 18.0
num_peldaños = math.ceil(altura_total / ch_ideal)
ch_final = altura_total / num_peldaños
longitud_desarrollo_m = math.sqrt((largo_calc/100)**2 + (altura_total/100)**2)

if tipo_escalera == "Recta":
    huella_calculada = largo_calc / (num_peldaños - 1)
    vol_total = (longitud_desarrollo_m * (fondo_calc/100) * 0.10) + \
                (((huella_calculada/100)*(ch_final/100)/2)*(fondo_calc/100)*num_peldaños)
else:
    huella_calculada = 28.0
    vol_total = (longitud_desarrollo_m * (fondo_calc/100) * 0.12) * 1.2

# --- CANTIDADES ---
vol_con_desperdicio = vol_total * 1.05
cemento_bultos = math.ceil(vol_con_desperdicio * 7.5)
mixto_m3 = vol_con_desperdicio * 1.1
num_varillas_long = math.ceil((fondo_calc / 15) + 1)
varillas_38_unid = math.ceil((num_varillas_long * longitud_desarrollo_m * 1.10) / 6)
num_grafiles = math.ceil((longitud_desarrollo_m * 100 / 20) + 1)
grafiles_unid = math.ceil((num_grafiles * (fondo_calc / 100) * 1.10) / 6)
alambre_kg = math.ceil((num_varillas_long * num_grafiles) * 0.015)

# --- COSTOS ---
costo_cemento = cemento_bultos * PRECIO_CEMENTO
costo_mixto = mixto_m3 * PRECIO_MIXTO
costo_acero = (varillas_38_unid * PRECIO_VARILLA_38) + (grafiles_unid * PRECIO_GRAFIL_14) + (alambre_kg * PRECIO_ALAMBRE)
costo_materiales_total = costo_cemento + costo_mixto + costo_acero

# NUEVA LÓGICA DE MANO DE OBRA: COSTO FIJO
costo_mano_obra_total = PAGO_POR_PERSONA * CANTIDAD_PERSONAS # $360.000

costo_directo_total = (costo_materiales_total + costo_mano_obra_total) * (1.10 if "+" in estilo_construccion else 1.0)
precio_venta_final = costo_directo_total * (1 + margen_utilidad)

# --- INTERFAZ ---
if pestana == "Calculadora":
    st.title(f"🚀 Cotización: {tipo_escalera}")
    
    st.subheader("🪜 Datos de Construcción")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pasos", int(num_peldaños))
    c2.metric("Huella", f"{huella_calculada:.2f} cm")
    c3.metric("Contrahuella", f"{ch_final:.2f} cm")

    st.subheader("💰 Resultado de la Operación")
    v1, v2, v3 = st.columns(3)
    v1.metric("VENTA TOTAL", formato_cop(precio_venta_final))
    v2.metric("Inversión (Mat+MO)", formato_cop(costo_directo_total))
    v3.metric("Ganancia Neta", formato_cop(precio_venta_final - costo_directo_total))

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.success(f"👷 **Mano de Obra (Fija)**")
        st.write(f"• Personal: **{CANTIDAD_PERSONAS} personas**")
        st.write(f"• Pago por persona: **{formato_cop(PAGO_POR_PERSONA)}**")
        st.write(f"• Total Mano de Obra: **{formato_cop(costo_mano_obra_total)}**")
    
    with col2:
        st.info("🧱 **Materiales**")
        st.write(f"• Cemento: {cemento_bultos} bls / Mixto: {mixto_m3:.2f} m³")
        st.write(f"• Costo Total Materiales: **{formato_cop(costo_materiales_total)}**")

    st.markdown("---")
    
    with st.expander("💾 Guardar"):
        proy = st.text_input("Nombre de la Obra")
        if st.button("CONFIRMAR"):
            st.session_state.historial.append({"Obra": proy, "Venta": precio_venta_final})
            st.success("Guardado")
