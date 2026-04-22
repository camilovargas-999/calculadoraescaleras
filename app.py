import streamlit as st
import math

st.set_page_config(page_title="Calculadora de Escaleras Colombia", page_icon="🏗️")

# Función de formato corregida
def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

st.title("🏗️ Diseñador de Escaleras y Presupuestador")
st.markdown("Cálculos técnicos y comerciales ajustados a **Pesos Colombianos (COP)**.")

# --- ENTRADAS LATERALES ---
st.sidebar.header("Parámetros de Diseño")
altura_total = st.sidebar.number_input("Altura a vencer (cm)", value=270.0, step=1.0)
largo_disponible = st.sidebar.number_input("Largo total de la escalera (cm)", value=400.0, step=1.0)
ancho_escalera = st.sidebar.number_input("Ancho de la escalera (cm)", value=100.0, step=1.0)

ESPESOR_FIJO = 0.05 

st.sidebar.header("Costos y Negocio (COP)")
precio_m3_concreto = st.sidebar.number_input("Precio m3 Concreto (COP)", value=550000.0, step=10000.0)
margen_utilidad = st.sidebar.slider("Margen de Utilidad (%)", 10, 100, 30) / 100

# --- LÓGICA DE CÁLCULO ---
ch_ideal = 18.0
num_peldaños = math.ceil(altura_total / ch_ideal)
ch_final = altura_total / num_peldaños

if num_peldaños > 1:
    huella_calculada = largo_disponible / (num_peldaños - 1)
else:
    huella_calculada = 0

longitud_rampa_m = math.sqrt((largo_disponible/100)**2 + (altura_total/100)**2)
vol_rampa = longitud_rampa_m * (ancho_escalera/100) * ESPESOR_FIJO
vol_peldaños = ((huella_calculada/100) * (ch_final/100) / 2) * (ancho_escalera/100) * num_peldaños
vol_total = vol_rampa + vol_peldaños

costo_mat = vol_total * precio_m3_concreto
mano_obra = costo_mat * 0.90 
costo_total = costo_mat + mano_obra
precio_venta = costo_total * (1 + margen_utilidad)

# --- VISUALIZACIÓN ---
col1, col2, col3 = st.columns(3)
col1.metric("N° Peldaños", num_peldaños)
col2.metric("Contrahuella", "{:.2f} cm".format(ch_final))
col3.metric("Huella", "{:.2f} cm".format(huella_calculada))

blondel = (2 * ch_final) + huella_calculada
st.subheader("📏 Validación Técnica")
if 60 <= blondel <= 65:
    st.success("La escalera es cómoda (Ley de Blondel: {:.2f} cm)".format(blondel))
else:
    st.warning("Revisar diseño: La escalera podría ser incómoda (Ley de Blondel: {:.2f} cm)".format(blondel))

st.subheader("📊 Análisis de Costos (Pesos Colombianos)")
c1, c2 = st.columns(2)

with c1:
    st.info("**Volumen de Concreto:** {:.3f} m³".format(vol_total))
    st.write("Costo Materiales: **{}**".format(formato_cop(costo_mat)))
    st.write("Costo Mano de Obra: **{}**".format(formato_cop(mano_obra)))

with c2:
    st.success("**Precio de Venta Sugerido:**")
    st.header(formato_cop(precio_venta))
    st.write("Ganancia estimada: {}".format(formato_cop(precio_venta - costo_total)))

st.markdown("---")
st.caption("Cifras calculadas para el mercado de Colombia. Espesor de losa: 5cm fijo.")
