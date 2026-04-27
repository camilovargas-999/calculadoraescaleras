import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V3.1 - Colombia", page_icon="🏗️", layout="wide")

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- BARRA LATERAL ---
st.sidebar.title("Configuración Profesional")
pestana = st.sidebar.radio("Navegación:", ["Calculadora", "Historial de Ventas"])

with st.sidebar.form("formulario_diseño"):
    st.header("📐 Parámetros de Diseño")
    
    tipo_escalera = st.selectbox(
        "Tipo de Diseño",
        ["Recta", "En L con abanico", "En U con abanico", "Caracol"]
    )

    orientacion = "N/A"
    if tipo_escalera != "Recta":
        orientacion = st.radio("Orientación (Giro)", ["Derecha 👉", "Izquierda 👈"])

    estilo_construccion = st.selectbox(
        "Tipo de estructura o acabado",
        ["Normal", "Sin espaldar (+10%)", "Con insoluz/claraboyas (+10%)"]
    )
    
    st.markdown("---")
    
    if tipo_escalera == "En L con abanico":
        altura_total = st.number_input("Altura Total (cm)", value=240.0)
        salida_escalera = st.number_input("Salida de la escalera (cm)", value=300.0)
        hueco_salida = st.number_input("Hueco de salida (cm)", value=100.0)
        llegada_fondo = st.number_input("Llegada (Fondo) (cm)", value=100.0)
        hueco_fondo = st.number_input("Hueco de fondo (cm)", value=100.0)
        largo_calc = salida_escalera 
        fondo_calc = hueco_salida
    else:
        altura_total = st.number_input("Altura Total (cm)", value=240.0)
        largo_calc = st.number_input("Fondo (cm)", value=300.0) 
        fondo_calc = st.number_input("Hueco (cm)", value=100.0)   
    
    st.markdown("---")
    precio_m3_concreto = st.number_input("Precio m3 Concreto (COP)", value=550000)
    margen_utilidad = st.slider("Margen de Ganancia %", 10, 100, 30) / 100
    
    submit_button = st.form_submit_button(label="🔄 CALCULAR AHORA")

# --- LÓGICA DE CÁLCULO ---
ch_ideal = 18.0
num_peldaños = math.ceil(altura_total / ch_ideal)
ch_final = altura_total / num_peldaños
longitud_desarrollo_m = math.sqrt((largo_calc/100)**2 + (altura_total/100)**2)

# Cálculo de Huella y Ángulo
if tipo_escalera == "Recta":
    huella_calculada = largo_calc / (num_peldaños - 1)
    angulo_rad = math.atan(altura_total / largo_calc)
    vol_total = (longitud_desarrollo_m * (fondo_calc/100) * 0.08) + \
                (((huella_calculada/100)*(ch_final/100)/2)*(fondo_calc/100)*num_peldaños)
    dificultad_base = 0.9
elif tipo_escalera == "En L con abanico":
    pasos_rectos = num_peldaños - 3
    huella_calculada = (largo_calc - 100) / pasos_rectos if pasos_rectos > 0 else 25
    angulo_rad = math.atan(ch_final / huella_calculada)
    vol_total = ((largo_calc/100 * fondo_calc/100) + (1.0 * 1.0)) * 0.12
    dificultad_base = 1.4
    longitud_desarrollo_m *= 1.2
else: 
    huella_calculada = 28.0
    angulo_rad = math.radians(35)
    vol_total = (altura_total/100 * fondo_calc/100 * 0.15)
    dificultad_base = 1.5

angulo_deg = math.degrees(angulo_rad)

# Determinación de Ángulo Óptimo
if 30 <= angulo_deg <= 37:
    estado_angulo = "✅ Óptimo"
elif 26 <= angulo_deg < 30 or 37 < angulo_deg
