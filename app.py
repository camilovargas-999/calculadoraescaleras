import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V2.3 - Colombia", page_icon="🏗️", layout="wide")

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- BARRA LATERAL ---
st.sidebar.title("Configuración Profesional")
pestana = st.sidebar.radio("Navegación:", ["Calculadora", "Historial de Ventas"])

# --- FORMULARIO DE ENTRADA (Para evitar recargas constantes) ---
with st.sidebar.form("formulario_diseño"):
    st.header("📐 Parámetros Técnicos")
    tipo_escalera = st.selectbox(
        "Tipo de Diseño",
        ["Recta", "En L (90° con descanso)", "En L Compensada (Abanico)", 
         "En U (con descanso)", "U Compensada (Abanico)", "Caracol"]
    )
    altura_total = st.number_input("Altura total a vencer (cm)", value=270.0)
    ancho_escalera = st.number_input("Ancho de rampa (cm)", value=100.0)
    largo_disponible = st.number_input("Largo disponible (cm)", value=300.0)
    
    st.markdown("---")
    precio_m3_concreto = st.number_input("Precio m3 Concreto (COP)", value=550000)
    margen_utilidad = st.slider("Margen de Ganancia %", 10, 100, 30) / 100
    
    # BOTÓN DE ACTUALIZACIÓN
    submit_button = st.form_submit_button(label="🔄 CALCULAR Y ACTUALIZAR")

# --- LÓGICA DE CÁLCULO (Solo se ejecuta al pulsar el botón o iniciar) ---
ch_ideal = 18.0
num_peldaños = math.ceil(altura_total / ch_ideal)
ch_final = altura_total / num_peldaños
ESPESOR_FIJO = 0.05

# Cálculos rápidos de volumen y huella
if tipo_escalera == "Recta":
    huella_calculada = largo_disponible / (num_peldaños - 1)
    long_rampa = math.sqrt((largo_disponible/100)**2 + (altura_total/100)**2)
    vol_total = (long_rampa * (ancho_escalera/100) * ESPESOR_FIJO) + \
                (((huella_calculada/100)*(ch_final/100)/2)*(ancho_escalera/100)*num_peldaños)
    dificultad = 0.9
else:
    # Lógica simplificada para otros tipos (puedes expandirla luego)
    huella_calculada = largo_disponible / (num_peldaños/2) if "U" in tipo_escalera else 25.0
    vol_total = (altura_total/100 * ancho_escalera/100 * ESPESOR_FIJO) * 1.5
    dificultad = 1.3

# FINANZAS
costo_mat = vol_total * precio_m3_concreto
costo_total = costo_mat * (1 + dificultad)
precio_venta = costo_total * (1 + margen_utilidad)

# --- INTERFAZ PRINCIPAL ---
if pestana == "Calculadora":
    st.title(f"🚀 Diseño de Escalera {tipo_escalera}")

    # VALIDACIÓN NSR-10 (Leyes Colombianas)
    # La norma colombiana NSR-10 sugiere huellas >= 25cm para mayor seguridad.
    if huella_calculada < 23:
        st.error(f"❌ ¡ALERTA DE SEGURIDAD! La huella es de {huella_calculada:.2f} cm. La ley colombiana exige un mínimo de 23-25 cm. La escalera será peligrosa.")
    elif 23 <= huella_calculada < 25:
        st.warning(f"⚠️ CUIDADO: La huella ({huella_calculada:.2f} cm) cumple lo mínimo legal, pero es incómoda para pies grandes.")
    else:
        st.success(f"✅ Diseño Cumple Norma: Huella de {huella_calculada:.2f} cm es segura.")

    # Mostrar métricas
    m1, m2, m3 = st.columns(3)
    m1.metric("Precio Venta", formato_cop(precio_venta))
    m2.metric("N° Pasos", num_peldaños)
    m3.metric("Contrahuella", f"{ch_final:.2f} cm")

    st.markdown("---")
    
    # Formulario para guardar
    with st.expander("📝 Guardar esta cotización"):
        cliente = st.text_input("Nombre del Proyecto")
        if st.button("💾 CONFIRMAR Y GUARDAR"):
            st.session_state.historial.append({
                "Cliente": cliente, "Tipo": tipo_escalera, "Venta": precio_venta, 
                "Huella": f"{huella_calculada:.1f} cm", "Estado": "Segura" if huella_calculada >= 25 else "Riesgosa"
            })
            st.toast("Cotización guardada exitosamente")

else:
    st.title("📊 Historial de Ventas")
    if st.session_state.historial:
        df = pd.DataFrame(st.session_state.historial)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay registros.")
