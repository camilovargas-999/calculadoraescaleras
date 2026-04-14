import streamlit as st
import math

st.set_page_config(page_title="Calculadora de Escaleras", page_icon="🏗️")

st.title("🏗️ Diseñador de Escaleras y Presupuestador")
st.markdown("Calcula geometría, materiales y costos en tiempo real.")

# --- ENTRADAS LATERALES ---
st.sidebar.header("Parámetros de Diseño")
altura_total = st.sidebar.number_input("Altura a vencer (cm)", value=270.0, step=1.0)
ancho_escalera = st.sidebar.number_input("Ancho de escalera (cm)", value=100.0, step=1.0)
espesor_losa = st.sidebar.slider("Espesor de la losa (cm)", 10, 20, 15) / 100

st.sidebar.header("Costos y Negocio")
precio_m3_concreto = st.sidebar.number_input("Precio m3 Concreto ($)", value=150.0)
margen_utilidad = st.sidebar.slider("Margen de Utilidad (%)", 10, 100, 30) / 100

# --- LÓGICA DE CÁLCULO ---
ch_ideal = 18.0
num_peldaños = math.ceil(altura_total / ch_ideal)
ch_final = altura_total / num_peldaños
huella = 28.0 

# Geometría
longitud_planta = (huella * (num_peldaños - 1)) / 100 # en metros
hipotenusa = math.sqrt(longitud_planta**2 + (altura_total/100)**2)

# Materiales
vol_rampa = hipotenusa * (ancho_escalera/100) * espesor_losa
vol_peldaños = ((huella/100) * (ch_final/100) / 2) * (ancho_escalera/100) * num_peldaños
vol_total = vol_rampa + vol_peldaños

# Finanzas
costo_mat = vol_total * precio_m3_concreto
mano_obra = costo_mat * 0.85 # Factor estimado
costo_total = costo_mat + mano_obra
precio_venta = costo_total * (1 + margen_utilidad)

# --- VISUALIZACIÓN EN LA APP ---
col1, col2, col3 = st.columns(3)
col1.metric("N° Peldaños", num_peldaños)
col2.metric("Contrahuella", f"{ch_final:.2f} cm")
col3.metric("Huella", f"{huella} cm")

st.subheader("📊 Análisis de Materiales y Costos")
c1, c2 = st.columns(2)

with c1:
    st.info(f"**Volumen de Concreto:** {vol_total:.3f} m³")
    st.write(f"Costo Materiales: ${costo_mat:.2f}")
    st.write(f"Costo Mano de Obra: ${mano_obra:.2f}")

with c2:
    st.success(f"**Precio de Venta Sugerido:**")
    st.header(f"${precio_venta:.2f}")
    st.write(f"Ganancia neta: ${precio_venta - costo_total:.2f}")

st.warning("⚠️ Nota: Los cálculos de mano de obra son estimaciones basadas en el costo de materiales.")
