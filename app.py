import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V2.4 - Colombia", page_icon="🏗️", layout="wide")

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- BARRA LATERAL ---
st.sidebar.title("Configuración Profesional")
pestana = st.sidebar.radio("Navegación:", ["Calculadora", "Historial de Ventas"])

with st.sidebar.form("formulario_diseño"):
    st.header("💎 Tipo de Acabado/Estructura")
    # --- NUEVA OPCIÓN DE TIPO DE CONSTRUCCIÓN ---
    estilo_construccion = st.radio(
        "Estilo de construcción:",
        ["Normal", "Sin espaldar (+10%)", "Con insoluz/claraboyas (+10%)"]
    )
    
    st.header("📐 Parámetros Técnicos")
    tipo_escalera = st.selectbox(
        "Tipo de Diseño",
        ["Recta", "En L (90° con descanso)", "En L Compensada (Abanico)", 
         "En U (con descanso)", "U Compensada (Abanico)", "Caracol"]
    )
    altura_total = st.number_input("Altura total (cm)", value=270.0)
    ancho_escalera = st.number_input("Ancho rampa (cm)", value=100.0)
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

# Cálculo de Volumen y Dificultad Base
if tipo_escalera == "Recta":
    huella_calculada = largo_disponible / (num_peldaños - 1)
    long_rampa = math.sqrt((largo_disponible/100)**2 + (altura_total/100)**2)
    vol_total = (long_rampa * (ancho_escalera/100) * ESPESOR_FIJO) + \
                (((huella_calculada/100)*(ch_final/100)/2)*(ancho_escalera/100)*num_peldaños)
    dificultad_base = 0.9
else:
    huella_calculada = largo_disponible / (num_peldaños/2) if "U" in tipo_escalera else 25.0
    vol_total = (altura_total/100 * ancho_escalera/100 * ESPESOR_FIJO) * 1.5
    dificultad_base = 1.3

# --- APLICACIÓN DE RECARGOS ESPECIALES ---
recargo = 1.0
if estilo_construccion == "Sin espaldar (+10%)":
    recargo = 1.10
elif estilo_construccion == "Con insoluz/claraboyas (+10%)":
    recargo = 1.10

# FINANZAS CON RECARGOS
costo_mat = vol_total * precio_m3_concreto
costo_base_mano_obra = costo_mat * dificultad_base
# Aplicamos el recargo al valor total de producción
costo_total = (costo_mat + costo_base_mano_obra) * recargo
precio_venta = costo_total * (1 + margen_utilidad)

# --- INTERFAZ PRINCIPAL ---
if pestana == "Calculadora":
    st.title(f"🚀 Cotizador: {tipo_escalera} ({estilo_construccion})")

    # Validación NSR-10
    if huella_calculada < 23:
        st.error(f"❌ ¡ALERTA! Huella de {huella_calculada:.2f} cm (Mínimo legal 23cm).")
    elif huella_calculada < 25:
        st.warning(f"⚠️ Huella de {huella_calculada:.2f} cm es legal pero poco cómoda.")
    else:
        st.success(f"✅ Diseño Seguro: Huella de {huella_calculada:.2f} cm.")

    # Métricas principales
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precio Venta", formato_cop(precio_venta))
    m2.metric("N° Pasos", num_peldaños)
    m3.metric("Contrahuella", f"{ch_final:.2f} cm")
    m4.metric("Recargo", f"{int((recargo-1)*100)}%")

    st.markdown("---")
    
    with st.expander("📝 Detalles de la Cotización"):
        st.write(f"**Estilo:** {estilo_construccion}")
        st.write(f"**Costo de Producción:** {formato_cop(costo_total)}")
        st.write(f"**Ganancia Neta:** {formato_cop(precio_venta - costo_total)}")
        
        cliente = st.text_input("Nombre del Proyecto")
        if st.button("💾 GUARDAR EN HISTORIAL"):
            st.session_state.historial.append({
                "Cliente": cliente, "Estilo": estilo_construccion, 
                "Tipo": tipo_escalera, "Venta": precio_venta, 
                "Estado": "Segura" if huella_calculada >= 25 else "Riesgosa"
            })
            st.toast("¡Guardado!")

else:
    st.title("📊 Historial de Ventas")
    if st.session_state.historial:
        df = pd.DataFrame(st.session_state.historial)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay registros en esta sesión.")
