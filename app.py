import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V3.3 - Colombia", page_icon="🏗️", layout="wide")

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- BARRA LATERAL ---
st.sidebar.title("Configuración Profesional")
pestana = st.sidebar.radio("Navegación:", ["Calculadora", "Historial de Ventas"])

# Inicializamos la orientación por defecto
orientacion_sel = "N/A"

with st.sidebar.form("formulario_diseño"):
    st.header("📐 Parámetros de Diseño")
    
    tipo_escalera = st.selectbox(
        "Tipo de Diseño",
        ["Recta", "En L con abanico", "En U con abanico", "Caracol"]
    )

    if tipo_escalera != "Recta":
        orientacion_sel = st.radio("Orientación (Giro)", ["Derecha 👉", "Izquierda 👈"])
    else:
        orientacion_sel = "N/A"

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

if 30 <= angulo_deg <= 37:
    estado_angulo = "✅ Óptimo"
elif (26 <= angulo_deg < 30) or (37 < angulo_deg <= 42):
    estado_angulo = "⚠️ Aceptable"
else:
    estado_angulo = "🚨 Crítico"

# Materiales y Finanzas
recargo = 1.10 if "+" in estilo_construccion else 1.0
costo_mat = vol_total * precio_m3_concreto
costo_total = (costo_mat + (costo_mat * dificultad_base)) * recargo
precio_venta = costo_total * (1 + margen_utilidad)

vol_con_desperdicio = vol_total * 1.05
cemento_bultos = math.ceil(vol_con_desperdicio * 7.0)
arena_m3 = vol_con_desperdicio * 0.52
triturado_m3 = vol_con_desperdicio * 0.75
num_varillas_long = math.ceil((fondo_calc / 15) + 1)
metros_3_8 = num_varillas_long * longitud_desarrollo_m * 1.10
varillas_6m = math.ceil(metros_3_8 / 6)
num_grafiles_trans = math.ceil((longitud_desarrollo_m * 100 / 20) + 1)
grafiles_6m = math.ceil((num_grafiles_trans * (fondo_calc / 100) * 1.10) / 6)
alambre_kg = math.ceil((num_varillas_long * num_grafiles_trans) * 0.02)

# --- INTERFAZ DE RESULTADOS ---
if pestana == "Calculadora":
    st.title(f"🚀 Cotización: {tipo_escalera}")
    
    st.markdown("### 🪜 Datos de Construcción")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Cantidad de Pasos", int(num_peldaños))
    res_col2.metric("Tamaño de la Huella", f"{huella_calculada:.2f} cm")
    res_col3.metric("Altura Final de Paso", f"{ch_final:.2f} cm")

    st.markdown("### 💰 Resultado de la Operación")
    val_col1, val_col2, val_col3 = st.columns(3)
    val_col1.metric("VALOR TOTAL VENTA", formato_cop(precio_venta))
    val_col2.metric("Inclinación", f"{angulo_deg:.1f}°", delta=estado_angulo, delta_color="normal")
    val_col3.metric("Giro / Orientación", orientacion_sel)

    st.markdown("---")

    if tipo_escalera == "Recta" and huella_calculada < 24:
        st.error(f"🚨 ERROR TÉCNICO: La huella de {huella_calculada:.1f}cm es menor al mínimo de 24cm.")

    st.subheader("📦 Desglose de Materiales")
    mat_col1, mat_col2 = st.columns(2)
    # CORRECCIÓN DE IDENTACIÓN AQUÍ:
    with mat_col1:
        st.info("**Mezcla (3000 PSI)**")
        st.write(f"🔹 Cemento: {cemento_bultos} Bultos")
        st.write(f"🔹 Arena: {arena_m3:.2f} m³")
        st.write(f"🔹 Triturado: {triturado_m3:.2f} m³")
    
    with mat_col2:
        st.warning("**Refuerzo de Acero**")
        st.write(f"🔸 Varilla 3/8: {varillas_6m} unids")
        st.write(f"🔸 Grafil 1/4: {grafiles_6m} unids")
        st.write(f"🔸 Alambre Negro: {alambre_kg} kg")

    with st.expander("💾 Guardar"):
        proy = st.text_input("Nombre de la Obra")
        if st.button("CONFIRMAR"):
            st.session_state.historial.append({"Obra": proy, "Tipo": tipo_escalera, "Venta": precio_venta, "Orientacion": orientacion_sel})
            st.success("Guardado")
else:
    st.title("📊 Historial")
    st.table(pd.DataFrame(st.session_state.historial))
