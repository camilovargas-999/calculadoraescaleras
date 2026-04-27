import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V2.9 - Colombia", page_icon="🏗️", layout="wide")

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
        largo_disponible = salida_escalera 
        fondo_escalera = hueco_salida
    else:
        altura_total = st.number_input("Altura Total (cm)", value=240.0)
        largo_disponible = st.number_input("Fondo (cm)", value=300.0) 
        fondo_escalera = st.number_input("Hueco (cm)", value=100.0)   
    
    st.markdown("---")
    precio_m3_concreto = st.number_input("Precio m3 Concreto (COP)", value=550000)
    margen_utilidad = st.slider("Margen de Ganancia %", 10, 100, 30) / 100
    
    submit_button = st.form_submit_button(label="🔄 CALCULAR Y ACTUALIZAR")

# --- LÓGICA DE CÁLCULO ---
ch_ideal = 18.0
num_peldaños = math.ceil(altura_total / ch_ideal)
ch_final = altura_total / num_peldaños

if tipo_escalera == "Recta":
    huella_calculada = largo_disponible / (num_peldaños - 1)
    angulo_rad = math.atan(altura_total / largo_disponible)
    angulo_deg = math.degrees(angulo_rad)
    vol_total = ((largo_disponible/100) * (fondo_escalera/100) * 0.05) + \
                (((huella_calculada/100)*(ch_final/100)/2)*(fondo_escalera/100)*num_peldaños)
    dificultad_base = 0.9

elif tipo_escalera == "En L con abanico":
    pasos_rectos = num_peldaños - 3
    huella_calculada = (salida_escalera - hueco_fondo) / (pasos_rectos) if pasos_rectos > 0 else 25
    angulo_rad = math.atan(ch_final / huella_calculada)
    angulo_deg = math.degrees(angulo_rad)
    vol_total = ((salida_escalera/100 * hueco_salida/100) + (llegada_fondo/100 * hueco_fondo/100)) * 0.12
    dificultad_base = 1.4

else: 
    huella_calculada = 28.0
    angulo_deg = 35.0
    vol_total = (altura_total/100 * fondo_escalera/100 * 0.15)
    dificultad_base = 1.5

recargo = 1.10 if "+" in estilo_construccion else 1.0
costo_mat = vol_total * precio_m3_concreto
costo_total = (costo_mat + (costo_mat * dificultad_base)) * recargo
precio_venta = costo_total * (1 + margen_utilidad)

# --- INTERFAZ DE RESULTADOS (ORDEN MODIFICADO) ---
if pestana == "Calculadora":
    st.title(f"🚀 Resultado de Cálculo: {tipo_escalera}")
    
    # 1. Cantidad de pasos (Métrica principal destacada)
    st.subheader("🪜 Especificaciones de Construcción")
    m1, m2, m3 = st.columns(3)
    m1.metric("Cantidad de Pasos", int(num_peldaños))
    m2.metric("Tamaño de la Huella", f"{huella_calculada:.2f} cm")
    m3.metric("Altura Final de cada Paso", f"{ch_final:.2f} cm")

    st.markdown("---")

    # 2. Valor Total
