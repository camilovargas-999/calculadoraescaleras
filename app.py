import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V2.5 - Colombia", page_icon="🏗️", layout="wide")

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- BARRA LATERAL ---
st.sidebar.title("Configuración Profesional")
pestana = st.sidebar.radio("Navegación:", ["Calculadora", "Historial de Ventas"])

with st.sidebar.form("formulario_diseño"):
    st.header("📐 Parámetros de Diseño")
    
    # 1. Tipo de Escalera (Nombres simplificados)
    tipo_escalera = st.selectbox(
        "Tipo de Diseño",
        ["Recta", "En L con abanico", "En U con abanico", "Caracol"]
    )

    # 2. Estilo de estructura (Ahora como lista desplegable dentro de parámetros)
    estilo_construccion = st.selectbox(
        "Tipo de estructura o acabado",
        ["Normal", "Sin espaldar (+10%)", "Con insoluz/claraboyas (+10%)"]
    )
    
    st.markdown("---")
    altura_total = st.number_input("Altura total a vencer (cm)", value=270.0)
    fondo_escalera = st.number_input("Fondo de la escalera (cm)", value=100.0)
    largo_disponible = st.number_input("Largo disponible (cm)", value=300.0)
    
    st.markdown("---")
    precio_m3_concreto = st.number_input("Precio m3 Concreto (COP)", value=550000)
    margen_utilidad = st.slider("Margen de Ganancia %", 10, 100, 30) / 100
    
    submit_button = st.form_submit_button(label="🔄 CALCULAR Y ACTUALIZAR")

# --- LÓGICA DE CÁLCULO ---
ch_ideal = 18.0
num_peldaños = math.ceil(altura_total / ch_ideal)
ch_final = altura_total / num_peldaños
ESPESOR_FIJO = 0.05

# Cálculo de Volumen y Dificultad según el nuevo listado
if tipo_escalera == "Recta":
    huella_calculada = largo_disponible / (num_peldaños - 1)
    long_rampa = math.sqrt((largo_disponible/100)**2 + (altura_total/100)**2)
    vol_total = (long_rampa * (fondo_escalera/100) * ESPESOR_FIJO) + \
                (((huella_calculada/100)*(ch_final/100)/2)*(fondo_escalera/100)*num_peldaños)
    dificultad_base = 0.9
elif tipo_escalera == "En L con abanico":
    pasos_rectos = num_peldaños - 3
    huella_calculada = largo_disponible / pasos_rectos if pasos_rectos > 0 else 25
    vol_total = ((fondo_escalera/100)**2 * 2.5) * ESPESOR_FIJO 
    dificultad_base = 1.4
elif tipo_escalera == "En U con abanico":
    huella_calculada = (largo_disponible - fondo_escalera) / (num_peldaños/2)
    vol_total = ((fondo_escalera/100)**2 * 3.5) * ESPESOR_FIJO
    dificultad_base = 1.5
else: # Caracol
    huella_calculada = 25.0
    vol_total = (math.pi * ((fondo_escalera/1.5/100)**2) * (altura_total/100)) * 0.4
    dificultad_base = 1.6

# Aplicación de recargos por estructura/acabado
recargo = 1.10 if "+" in estilo_construccion else 1.0

# FINANZAS
costo_mat = vol_total * precio_m3_concreto
costo_base_mano_obra = costo_mat * dificultad_base
costo_total = (costo_mat + costo_base_mano_obra) * recargo
precio_venta = costo_total * (1 + margen_utilidad)

# --- INTERFAZ PRINCIPAL ---
if pestana == "Calculadora":
    st.title(f"🚀 Cotizador: {tipo_escalera}")
    st.subheader(f"Estructura: {estilo_construccion}")

    # Validación NSR-10 (Huella mínima)
    if huella_calculada < 23:
        st.error(f"❌ ALERTA: Huella de {huella_calculada:.2f} cm es menor al mínimo legal (23 cm).")
    elif huella_calculada < 25:
        st.warning(f"⚠️ Huella de {huella_calculada:.2f} cm cumple el mínimo pero es reducida.")
    else:
        st.success(f"✅ Huella de {huella_calculada:.2f} cm cumple con la norma de seguridad.")

    # Métricas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precio Venta", formato_cop(precio_venta))
    m2.metric("N° Pasos", num_peldaños)
    m3.metric("Contrahuella", f"{ch_final:.2f} cm")
    m4.metric("Fondo", f"{fondo_escalera} cm")

    st.markdown("---")
    
    with st.expander("📝 Registrar esta Obra"):
        cliente = st.text_input("Nombre del Proyecto/Cliente")
        if st.button("💾 CONFIRMAR GUARDADO"):
            st.session_state.historial.append({
                "Cliente": cliente, 
                "Diseño": tipo_escalera, 
                "Estructura": estilo_construccion,
                "Venta": precio_venta, 
                "Fondo": fondo_escalera
            })
            st.toast("Datos guardados en el historial.")

else:
    st.title("📊 Control de Ventas y Proyectos")
    if st.session_state.historial:
        df = pd.DataFrame(st.session_state.historial)
        st.dataframe(df, use_container_width=True)
        st.metric("Total Cotizado Acumulado", formato_cop(df["Venta"].sum()))
    else:
        st.info("No hay registros guardados en esta sesión.")
