import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import date
import io

st.set_page_config(
    page_title="Cotizador Escaleras",
    page_icon="🏗️",
    layout="centered"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; }
    .stApp { background-color: #0f1117; }

    /* Botones grandes y fáciles de tocar */
    .stButton > button {
        font-size: 1.2rem !important;
        padding: 16px 32px !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        width: 100%;
    }
    .stTextInput > label, .stTextArea > label,
    .stNumberInput > label, .stSelectbox > label,
    .stDateInput > label {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        color: #ccc !important;
    }
    input, textarea, select {
        font-size: 1.1rem !important;
    }
    .card {
        background: #1a1d27;
        border-radius: 14px;
        padding: 24px;
        border: 1px solid #2a2d3a;
        margin-bottom: 16px;
    }
    .card-green  { border-left: 5px solid #00c9a7; }
    .card-blue   { border-left: 5px solid #4f8ef7; }
    .titulo-seccion {
        font-family: 'Syne', sans-serif;
        font-size: 1.1rem;
        color: #00c9a7;
        font-weight: 700;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .precio-grande {
        font-family: 'Syne', sans-serif;
        font-size: 2.4rem;
        font-weight: 800;
        color: #00c9a7;
    }
    hr { border-color: #2a2d3a; }
</style>
""", unsafe_allow_html=True)

# ─── DATOS EMPRESA (configurables) ───────────────────────────────────────────
EMPRESA = {
    "nombre":    "Escaleras La Esperanza",
    "nit":       "",
    "telefono":  "",
    "ciudad":    "Colombia",
    "vendedor":  "Vendedor",
}

def fmt(v):
    return "COP {:,.0f}".format(v).replace(",", ".")

def generar_pdf(datos):
    """Genera el PDF de la cotización y retorna bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    estilos = getSampleStyleSheet()
    azul    = colors.HexColor("#1565C0")
    verde   = colors.HexColor("#00695C")
    gris    = colors.HexColor("#BDBDBD")
    negro   = colors.HexColor("#212121")
    rojo    = colors.HexColor("#B71C1C")

    st_titulo = ParagraphStyle('titulo', fontSize=22, fontName='Helvetica-Bold',
                                textColor=azul, spaceAfter=4)
    st_sub    = ParagraphStyle('sub', fontSize=11, fontName='Helvetica',
                                textColor=gris, spaceAfter=2)
    st_bold   = ParagraphStyle('bold', fontSize=10, fontName='Helvetica-Bold',
                                textColor=negro, spaceAfter=3)
    st_normal = ParagraphStyle('normal', fontSize=10, fontName='Helvetica',
                                textColor=negro, spaceAfter=3)
    st_precio = ParagraphStyle('precio', fontSize=20, fontName='Helvetica-Bold',
                                textColor=verde, spaceAfter=4, alignment=2)
    st_aviso  = ParagraphStyle('aviso', fontSize=9, fontName='Helvetica',
                                textColor=rojo, spaceAfter=3)
    st_center = ParagraphStyle('center', fontSize=9, fontName='Helvetica',
                                textColor=gris, alignment=1)
    st_nota   = ParagraphStyle('nota', fontSize=10, fontName='Helvetica',
                                textColor=negro, spaceAfter=3, leading=15)

    story = []

    # ── Encabezado ──
    story.append(Paragraph(EMPRESA['nombre'], st_titulo))
    story.append(Paragraph(f"NIT: {EMPRESA['nit']}  |  Tel: {EMPRESA['telefono']}  |  {EMPRESA['ciudad']}", st_sub))
    story.append(HRFlowable(width="100%", thickness=1.5, color=azul, spaceAfter=10))

    # ── Info cotización ──
    story.append(Paragraph("COTIZACIÓN", ParagraphStyle('cot', fontSize=14,
                 fontName='Helvetica-Bold', textColor=azul, spaceAfter=6)))

    info_tabla = [
        ["Fecha:",        datos['fecha'].strftime("%d / %m / %Y"),
         "Cotización #:", datos['numero']],
        ["Cliente:",      datos['cliente'],
         "Teléfono:",     datos['telefono_cli']],
        ["Dirección:",    datos['direccion'],
         "Vendedor:",     datos['vendedor']],
    ]
    t_info = Table(info_tabla, colWidths=[3*cm, 7*cm, 3*cm, 4*cm])
    t_info.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME',  (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',  (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), azul),
        ('TEXTCOLOR', (2,0), (2,-1), azul),
        ('VALIGN',    (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor("#F5F5F5"), colors.white]),
        ('GRID',      (0,0), (-1,-1), 0.3, gris),
        ('PADDING',   (0,0), (-1,-1), 5),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 14))

    # ── Detalle de ítems ──
    story.append(Paragraph("DETALLE DE LA COTIZACIÓN", ParagraphStyle('det', fontSize=11,
                 fontName='Helvetica-Bold', textColor=azul, spaceAfter=6)))

    encabezado = [["#", "Descripción", "Valor"]]
    filas = encabezado.copy()
    total = 0
    for i, item in enumerate(datos['items'], 1):
        filas.append([
            str(i),
            Paragraph(item['descripcion'], ParagraphStyle('td', fontSize=9,
                      fontName='Helvetica', leading=13)),
            fmt(item['valor'])
        ])
        total += item['valor']

    t_items = Table(filas, colWidths=[1*cm, 13*cm, 3.5*cm])
    t_items.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND',  (0,0), (-1,0), azul),
        ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,0), 10),
        ('ALIGN',       (0,0), (-1,0), 'CENTER'),
        # Cuerpo
        ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',    (0,1), (-1,-1), 9),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F5F5F5")]),
        ('ALIGN',       (0,1), (0,-1), 'CENTER'),
        ('ALIGN',       (2,1), (2,-1), 'RIGHT'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',        (0,0), (-1,-1), 0.3, gris),
        ('PADDING',     (0,0), (-1,-1), 6),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    # ── Total ──
    t_total = Table([["", "TOTAL A PAGAR:", fmt(total)]],
                     colWidths=[1*cm, 13*cm, 3.5*cm])
    t_total.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), colors.HexColor("#E8F5E9")),
        ('FONTNAME',    (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,-1), 12),
        ('TEXTCOLOR',   (1,0), (-1,-1), verde),
        ('ALIGN',       (2,0), (2,0), 'RIGHT'),
        ('GRID',        (0,0), (-1,-1), 0.5, verde),
        ('PADDING',     (0,0), (-1,-1), 8),
    ]))
    story.append(t_total)
    story.append(Spacer(1, 14))

    # ── Notas ──
    if datos['notas'].strip():
        story.append(Paragraph("Notas y condiciones:", st_bold))
        story.append(Paragraph(datos['notas'], st_nota))
        story.append(Spacer(1, 8))

    # ── Validez ──
    story.append(HRFlowable(width="100%", thickness=0.5, color=gris, spaceAfter=6))
    story.append(Paragraph(
        "⚠ Esta cotización tiene validez de <b>15 días calendario</b> a partir de la fecha de emisión.",
        st_aviso))
    story.append(Spacer(1, 20))

    # ── Firma ──
    firma_tabla = [
        ["_______________________________", "   ", "_______________________________"],
        [f"Firma cliente: {datos['cliente']}", "   ", f"Vendedor: {datos['vendedor']}"],
    ]
    t_firma = Table(firma_tabla, colWidths=[7*cm, 2.5*cm, 7*cm])
    t_firma.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE',  (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), gris),
        ('ALIGN',     (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(t_firma)

    story.append(Spacer(1, 14))
    story.append(Paragraph(f"Generado por {EMPRESA['nombre']} · {EMPRESA['ciudad']}",
                            st_center))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ═════════════════════════════════════════════════════
#  INTERFAZ PRINCIPAL
# ═════════════════════════════════════════════════════

st.markdown("# 🏗️ Cotizador")
st.markdown(f"### {EMPRESA['nombre']}")
st.markdown("---")

# ── PASO 1: Datos del cliente ─────────────────────────────────────────────────
st.markdown('<div class="titulo-seccion">👤 Paso 1 — Datos del cliente</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    cliente = st.text_input("Nombre del cliente", placeholder="Ej: Juan Pérez")
    direccion = st.text_input("Dirección o conjunto", placeholder="Ej: Cra 5 # 10-20, Bogotá")
with col2:
    telefono_cli = st.text_input("Teléfono del cliente", placeholder="Ej: 300 123 4567")
    vendedor = st.text_input("Nombre del vendedor", value=EMPRESA['vendedor'],
                              placeholder="Ej: Don Carlos")

col3, col4 = st.columns(2)
with col3:
    fecha = st.date_input("Fecha de la cotización", value=date.today())
with col4:
    numero = st.text_input("Número de cotización", placeholder="Ej: 001",
                            value=date.today().strftime("%Y%m%d"))

st.markdown("---")

# ── PASO 2: Ítems ─────────────────────────────────────────────────────────────
st.markdown('<div class="titulo-seccion">🪜 Paso 2 — ¿Qué se va a cotizar?</div>', unsafe_allow_html=True)
st.caption("Agrega uno o varios ítems. Cada ítem es una escalera o servicio.")

if 'items' not in st.session_state:
    st.session_state['items'] = [{"descripcion": "", "valor": 0.0}]

# Mostrar ítems actuales
for i, item in enumerate(st.session_state['items']):
    st.markdown(f'<div class="card card-blue">', unsafe_allow_html=True)
    st.markdown(f"**Ítem {i+1}**")
    ia, ib = st.columns([3, 1])
    with ia:
        desc = st.text_area(
            "Descripción",
            value=item['descripcion'],
            height=100,
            placeholder="Ej: Escalera recta prefabricada en concreto, medidas 3 metros de fondo, 1 metro de ancho, altura 2.60 metros. Incluye instalación.",
            key=f"desc_{i}"
        )
        st.session_state['items'][i]['descripcion'] = desc
    with ib:
        val = st.number_input(
            "Valor (COP)",
            value=float(item['valor']),
            min_value=0.0,
            step=50000.0,
            format="%.0f",
            key=f"val_{i}"
        )
        st.session_state['items'][i]['valor'] = val
        if val > 0:
            st.markdown(f"<div style='color:#00c9a7; font-weight:700; font-size:1.1rem;'>{fmt(val)}</div>",
                        unsafe_allow_html=True)
        # Botón eliminar (solo si hay más de 1)
        if len(st.session_state['items']) > 1:
            if st.button(f"🗑️ Quitar", key=f"del_{i}"):
                st.session_state['items'].pop(i)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Botón agregar ítem
if st.button("➕  Agregar otro ítem"):
    st.session_state['items'].append({"descripcion": "", "valor": 0.0})
    st.rerun()

# ── Total en pantalla ─────────────────────────────────────────────────────────
total = sum(it['valor'] for it in st.session_state['items'])
st.markdown(
    f"<div class='card card-green' style='text-align:center;'>"
    f"<div style='color:#888; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px;'>TOTAL COTIZACIÓN</div>"
    f"<div class='precio-grande'>{fmt(total)}</div>"
    f"</div>",
    unsafe_allow_html=True
)

st.markdown("---")

# ── PASO 3: Notas ─────────────────────────────────────────────────────────────
st.markdown('<div class="titulo-seccion">📝 Paso 3 — Notas para el cliente</div>', unsafe_allow_html=True)
notas = st.text_area(
    "Condiciones, aclaraciones o mensajes para el cliente",
    height=120,
    placeholder="Ej: El precio incluye transporte dentro de Bogotá. No incluye acabados. Forma de pago: 50% anticipo y 50% contra entrega."
)

st.markdown("---")

# ── PASO 4: Generar PDF ───────────────────────────────────────────────────────
st.markdown('<div class="titulo-seccion">📄 Paso 4 — Generar cotización</div>', unsafe_allow_html=True)

errores = []
if not cliente.strip():
    errores.append("⚠️ Falta el nombre del cliente")
if not any(it['descripcion'].strip() for it in st.session_state['items']):
    errores.append("⚠️ Agrega al menos una descripción")
if total == 0:
    errores.append("⚠️ El valor total es cero")

if errores:
    for e in errores:
        st.warning(e)
else:
    datos = {
        "fecha":        fecha,
        "numero":       numero,
        "cliente":      cliente,
        "telefono_cli": telefono_cli,
        "direccion":    direccion,
        "vendedor":     vendedor,
        "items":        st.session_state['items'],
        "notas":        notas,
    }

    if st.button("📄  GENERAR COTIZACIÓN PDF", type="primary"):
        with st.spinner("Generando PDF..."):
            pdf_bytes = generar_pdf(datos)

        st.success("✅ ¡Cotización lista!")

        st.download_button(
            label="⬇️  DESCARGAR PDF",
            data=pdf_bytes,
            file_name=f"Cotizacion_{cliente.replace(' ','_')}_{fecha}.pdf",
            mime="application/pdf",
            type="primary"
        )

        st.info("💡 También puede imprimir el PDF directamente desde el navegador con Ctrl+P (o Cmd+P en Mac).")

st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#555; font-size:0.8rem;'>"
    f"{EMPRESA['nombre']} · Cotizador Manual</div>",
    unsafe_allow_html=True
)
