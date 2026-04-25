import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Escaleras Pro V2.7 - Colombia", page_icon="🏗️", layout="wide")

def formato_cop(valor):
    return "COP {:,.0f}".format(valor).replace(",", ".")

if 'historial' not in st.session_state:
    st.session_state['historial'] = []

# --- BARRA LATERAL ---
st.sidebar.title("Configuración Profesional")
pestana = st.sidebar.radio("Navegación:", ["Calculadora", "Historial de Ventas"])

with st.sidebar.form("formulario_diseño"):
    st.header("📐 Parámetros de Diseño")
    tipo_escalera = st.selectbox("Tipo de Diseño", ["Recta", "En L con abanico", "En U con abanico", "Caracol"])
    estilo_construccion = st.selectbox("Tipo de estructura o acabado", ["Normal", "Sin espaldar (+10%)", "Con insoluz/claraboyas (+10%)"])
    
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

# Longitud aproximada de la rampa para acero
longitud_desarrollo_m = math.sqrt((largo_disponible/100)**2 + (altura_total/100)**2)

if tipo_escalera == "Recta":
    huella_calculada = largo_disponible / (num_peldaños - 1)
    vol_total = (longitud_desarrollo_m * (fondo_escalera/100) * ESPESOR_FIJO) + \
                (((huella_calculada/100)*(ch_final/100)/2)*(fondo_escalera/100)*num_peldaños)
    dificultad_base = 0.9
elif tipo_escalera == "En L con abanico":
    huella_calculada = largo_disponible / (num_peldaños - 3) if num_peldaños > 3 else 25
    vol_total = ((fondo_escalera/100)**2 * 2.5) * ESPESOR_FIJO 
    dificultad_base = 1.4
    longitud_desarrollo_m *= 1.2 # Factor por giro
elif tipo_escalera == "En U con abanico":
    huella_calculada = (largo_disponible - fondo_escalera) / (num_peldaños/2)
    vol_total = ((fondo_escalera/100)**2 * 3.5) * ESPESOR_FIJO
    dificultad_base = 1.5
    longitud_desarrollo_m *= 1.4 # Factor por doble tramo
else: # Caracol
    huella_calculada = 25.0
    vol_total = (math.pi * ((fondo_escalera/1.5/100)**2) * (altura_total/100)) * 0.4
    dificultad_base = 1.6
    longitud_desarrollo_m = (altura_total/100) * 1.5

# --- DESGLOSE DE MEZCLA (3000 PSI) ---
vol_con_desperdicio = vol_total * 1.05
cemento_bultos = math.ceil(vol_con_desperdicio * 7.0)
arena_m3 = vol_con_desperdicio * 0.52
triturado_m3 = vol_con_desperdicio * 0.75

# --- DESGLOSE DE ACERO (Refuerzo) ---
# Varilla 3/8 principal (cada 15cm a lo ancho)
num_varillas_long = math.ceil((fondo_escalera / 15) + 1)
metros_3_8 = num_varillas_long * longitud_desarrollo_m * 1.10 # 10% traslapos/ganchos
varillas_6m = math.ceil(metros_3_8 / 6)

# Grafiles 1/4 repartición (cada 20cm a lo largo)
num_grafiles_trans = math.ceil((longitud_desarrollo_m * 100 / 20) + 1)
metros_1_4 = num_grafiles_trans * (fondo_escalera / 100) * 1.10
grafiles_6m = math.ceil(metros_1_4 / 6)

# Alambre negro (estimación por amarres)
alambre_kg = math.ceil((num_varillas_long * num_grafiles_trans) * 0.02) # 20g por amarre

# --- FINANZAS ---
recargo = 1.10 if "+" in estilo_construccion else 1.0
costo_mat = vol_total * precio_m3_concreto
costo_base_mano_obra = costo_mat * dificultad_base
costo_total = (costo_mat + costo_base_mano_obra) * recargo
precio_venta = costo_total * (1 + margen_utilidad)

# --- INTERFAZ ---
if pestana == "Calculadora":
    st.title(f"🚀 Cotizador Pro: {tipo_escalera}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("PRECIO DE VENTA", formato_cop(precio_venta))
    m2.metric("GANANCIA", formato_cop(precio_venta - costo_total))
    m3.metric("VOLUMEN", f"{vol_total:.3f} m³")

    st.markdown("---")

    # Fila 1: Mezcla
    st.subheader("🧱 Materiales de Mezcla")
    c1, c2, c3 = st.columns(3)
    c1.write(f"**Cemento:** {cemento_bultos} Bultos")
    c2.write(f"**Arena:** {arena_m3:.2f} m³")
    c3.write(f"**Triturado:** {triturado_m3:.2f} m³")

    # Fila 2: Acero
    st.subheader("⛓️ Refuerzo de Acero")
    a1, a2, a3 = st.columns(3)
    a1.warning(f"**Varilla 3/8:** {varillas_6m} unidades (6m)")
    a2.warning(f"**Grafil 1/4:** {grafiles_6m} unidades (6m)")
    a3.warning(f"**Alambre Negro:** {alambre_kg} kg")

    st.markdown("---")
    
    with st.expander("📝 Guardar Proyecto"):
        cliente = st.text_input("Nombre Cliente")
        if st.button("CONFIRMAR"):
            st.session_state.historial.append({"Cliente": cliente, "Venta": precio_venta, "Varillas": varillas_6m})
            st.success("Guardado")
else:
    st.title("📊 Historial")
    st.table(pd.DataFrame(st.session_state.historial))
