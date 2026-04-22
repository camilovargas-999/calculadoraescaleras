import streamlit as st
import math

st.set_page_config(page_title="Calculadora de Escaleras Colombia", page_icon="🏗️")

# Configuración de formato de moneda local
def formato_cop(valor):
    return f"COP {:,.0f}".replace(",", ".")

st.title("🏗️ Diseñador de Escaleras y Presupuestador")
st.markdown("Cálculos técnicos y comerciales ajustados a **Pesos Colombianos (COP)**.")

# --- ENTRADAS LATERALES ---
st.sidebar.header("Parámetros de Diseño")
altura_total = st.sidebar.number_input("Altura a vencer (cm)", value=270.0, step=1.0)
largo_disponible = st.sidebar.number_input("Largo total de la escalera (cm)", value=400.0, step=1.0)
ancho_escalera = st.sidebar.number_input("Ancho de la escalera (cm)", value=100.0, step=1.0)

# Espesor fijo de 5 cm
ESPESOR_FIJO = 0.05 

st.sidebar.header("Costos y Negocio (COP)")
# Valor promedio m3 concreto premezclado en Colombia aprox. $450.000 - $600.000
precio_m3_concreto = st.sidebar.number_input("Precio m3 Concreto (COP)", value=550000.0, step=10000.0)
margen_utilidad = st.sidebar.slider("Margen de Utilidad (%)", 10, 100, 30) / 100

# --- LÓGICA DE CÁLCULO ---
# 1. Geometría
ch_ideal = 18.0
num_peldaños = math.ceil(altura_total / ch_ideal)
ch_final = altura_total / num_peldaños

if num_peldaños > 1:
    huella_calculada = largo_disponible / (num_peldaños - 1)
else:
    huella_calculada = 0

# 2. Materiales
longitud_rampa_m = math.sqrt((largo_disponible/100)**2 + (altura_total/100)**2)
vol_rampa = longitud_rampa_m * (ancho_escalera/100) * ESPESOR_FIJO
vol_peldaños = ((huella_calculada/100) * (ch_final/100) / 2) * (ancho_escalera/100) * num_peldaños
vol_total = vol_rampa + vol_peldaños

# 3. Finanzas en COP
costo_mat = vol_total * precio_m3_concreto
# En Colombia la mano de obra de una escalera suele ser un valor importante
mano_obra = costo_mat * 0.90 
costo_total = costo_mat + mano_obra
precio_venta = costo_total * (1 + margen_utilidad)

# --- VISUALIZACIÓN ---
col1, col2, col3 = st.columns(3)
col1.metric("N° Peldaños", num_peldaños)
col2.metric("Contrahuella", f"{ch_final:.2f} cm")
col3.metric("Huella", f"{huella_calculada:.2f} cm")

# Validación Técnica (Ley de Blondel)
blondel = (2 * ch_final) + huella_calculada
st.subheader("📏 Validación Técnica")
if 60 <= blondel <= 65:
    st.success(f"La escalera es cómoda (Ley de Blondel: {blondel:.2f} cm)")
else:
    st.warning(f"Revisar diseño: La escalera podría ser incómoda (Ley de Blondel: {blondel:.2f} cm)")

st.subheader("📊 Análisis de Costos (Pesos Colombianos)")
c1, c2 = st.columns(2)

with c1:
    st.info(f"**Volumen de Concreto:** {vol_total:.3f} m³")
    st.write(f"Costo Materiales: **{formato_cop(costo_mat)}**")
    st.write(f"Costo Mano de Obra: **{formato_cop(mano_obra)}**")

with c2:
    st.success(f"**Precio de Venta Sugerido:**")
    st.header(formato_cop(precio_venta))
    st.write(f"Ganancia estimada: {formato_cop(precio_venta - costo_total)}")

st.markdown("---")
st.caption("Cifras calculadas para el mercado de Colombia. Espesor de losa: 5cm fijo.")
