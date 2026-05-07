import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.platypus.flowables import Flowable
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import date
import io

st.set_page_config(page_title="Escalerapp", page_icon="🪜", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"], p, span, div, label, input, textarea, select, button {
        font-family: 'Poppins', sans-serif !important;
    }
    .stApp { background-color: #0f1117; }
    .stButton > button {
        font-size: 1.15rem !important; padding: 14px 28px !important;
        border-radius: 12px !important; font-weight: 700 !important; width: 100%;
    }
    .stTextInput > label, .stTextArea > label,
    .stNumberInput > label, .stDateInput > label {
        font-size: 1rem !important; font-weight: 600 !important; color: #ccc !important;
    }
    input, textarea { font-size: 1.05rem !important; }
    .card        { background:#1a1d27; border-radius:14px; padding:24px; border:1px solid #2a2d3a; margin-bottom:16px; }
    .card-green  { border-left: 5px solid #00c9a7; }
    .titulo-sec  { font-size:1.0rem; color:#00c9a7; font-weight:700; margin-bottom:8px;
                   text-transform:uppercase; letter-spacing:1px; }
    .precio-gde  { font-size:2.4rem; font-weight:800; color:#00c9a7; }
    .app-titulo  { font-size:2.6rem; font-weight:800; text-align:center; color:#ffffff; letter-spacing:-1px; }
    .app-sub     { font-size:1rem; text-align:center; color:#888; margin-bottom:24px; }
    hr           { border-color:#2a2d3a; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTES ───────────────────────────────────────────────────────────────
EMPRESA = {
    "nombre":    "Escaleras La Esperanza",
    "rut":       "101241921-1",
    "telefonos": ["3115630456", "3134487319", "3114430160"],
    "ciudad":    "Colombia",
    "slogan":    '"Construyendo Suenos que perduren"',
}

NOTAS_DEFAULT = (
    "El pago es contra entrega.\n"
    "La instalacion se realiza de 5 a 8 dias despues la confirmacion.\n"
    "No incluye acabados.\n"
    "Los muros se entregan con los bloques a la vista.\n"
    "Incluye todos los materiales anteriormente mencionados."
)

AZUL_OSCURO = colors.HexColor("#1a237e")
NARANJA     = colors.HexColor("#e65100")
DORADO      = colors.HexColor("#b8860b")
BLANCO      = colors.white
NEGRO       = colors.HexColor("#212121")
GRIS        = colors.HexColor("#9e9e9e")
AZUL_CLARO  = colors.HexColor("#e8eaf6")

def fmt(v):
    return "COP {:,.0f}".format(v).replace(",", ".")

# ─── BANNER ───────────────────────────────────────────────────────────────────
class HeaderBanner(Flowable):
    """Banner superior oscuro con título 'Cotizacion' en naranja."""
    def __init__(self, width, height=4.8*cm):
        Flowable.__init__(self)
        self.w = width
        self.h = height

    def draw(self):
        c = self.canv
        # Fondo oscuro
        c.setFillColor(colors.HexColor("#2c2c2c"))
        c.rect(0, 0, self.w, self.h, fill=1, stroke=0)
        # Franja naranja inferior
        c.setFillColor(colors.HexColor("#bf360c"))
        c.rect(0, 0, self.w, 0.35*cm, fill=1, stroke=0)
        # Título naranja
        c.setFillColor(NARANJA)
        c.setFont("Helvetica-Bold", 44)
        c.drawCentredString(self.w / 2, self.h / 2 - 0.6*cm, "Cotizacion")
        # Marco decorativo naranja
        c.setStrokeColor(NARANJA)
        c.setLineWidth(1.5)
        m = 0.35*cm
        c.rect(m, m, self.w - 2*m, self.h - 2*m, fill=0, stroke=1)

    def wrap(self, *args):
        return (self.w, self.h)


# ─── LOGO ESCALERA (SVG dibujado con ReportLab) ───────────────────────────────
class LogoEskalera(Flowable):
    """Logo pequeño de escalera estilo La Esperanza para el PDF."""
    def __init__(self, size=2.2*cm):
        Flowable.__init__(self)
        self.size = size

    def draw(self):
        c = self.canv
        s = self.size
        # Arco superior (semicírculo)
        c.setStrokeColor(AZUL_OSCURO)
        c.setFillColor(colors.transparent)
        c.setLineWidth(1.5)
        c.arc(s*0.1, s*0.3, s*0.9, s*1.0, startAng=0, extent=180)
        # Líneas radiales (peldaños)
        import math
        cx, cy = s*0.5, s*0.3
        r_ext = s*0.4
        r_int = s*0.1
        for ang in range(0, 181, 30):
            rad = math.radians(ang)
            c.line(cx + r_int*math.cos(rad), cy + r_int*math.sin(rad),
                   cx + r_ext*math.cos(rad), cy + r_ext*math.sin(rad))
        # Base
        c.setLineWidth(2)
        c.line(s*0.05, s*0.3, s*0.95, s*0.3)
        # Texto empresa
        c.setFillColor(AZUL_OSCURO)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(s*0.5, s*0.12, "Escaleras")
        c.setFont("Helvetica", 6)
        c.drawCentredString(s*0.5, s*0.03, "La Esperanza")

    def wrap(self, *args):
        return (self.size, self.size * 1.1)


# ─── GENERADOR PDF ────────────────────────────────────────────────────────────
def generar_pdf(datos):
    buf = io.BytesIO()
    PW, PH = letter
    MAR = 2*cm
    CW  = PW - 2*MAR   # ancho del contenido

    doc = SimpleDocTemplate(buf, pagesize=letter,
                             leftMargin=MAR, rightMargin=MAR,
                             topMargin=0.4*cm, bottomMargin=1.8*cm)

    # Estilos
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    st_normal  = ps('n',  fontSize=9,  fontName='Helvetica',      textColor=NEGRO, leading=14)
    st_bold    = ps('b',  fontSize=9,  fontName='Helvetica-Bold', textColor=NEGRO)
    st_label   = ps('l',  fontSize=10, fontName='Helvetica-Bold', textColor=NEGRO)
    st_fecha   = ps('f',  fontSize=11, fontName='Helvetica-Bold', textColor=NEGRO)
    st_rut     = ps('r',  fontSize=8,  fontName='Helvetica-Bold', textColor=NEGRO)
    st_cont    = ps('c',  fontSize=13, fontName='Helvetica-Bold', textColor=AZUL_OSCURO, alignment=TA_RIGHT)
    st_tels    = ps('t',  fontSize=11, fontName='Helvetica-Bold', textColor=NEGRO, alignment=TA_RIGHT, leading=17)
    st_seccion = ps('s',  fontSize=11, fontName='Helvetica-Bold', textColor=NEGRO)
    st_bullet  = ps('bu', fontSize=9,  fontName='Helvetica',      textColor=NEGRO, leading=14, leftIndent=10)
    st_gracias = ps('g',  fontSize=22, fontName='Helvetica-Bold', textColor=DORADO, alignment=TA_RIGHT, leading=26)
    st_slogan  = ps('sl', fontSize=10, fontName='Helvetica',      textColor=GRIS, alignment=TA_CENTER)
    st_pie     = ps('p',  fontSize=8,  fontName='Helvetica',      textColor=GRIS, alignment=TA_CENTER)
    st_pago    = ps('pa', fontSize=9,  fontName='Helvetica',      textColor=NEGRO, leading=14)
    # Estilos tabla
    st_th      = ps('th', fontSize=10, fontName='Helvetica-Bold', textColor=BLANCO, alignment=TA_CENTER)
    st_td      = ps('td', fontSize=9,  fontName='Helvetica',      textColor=NEGRO,  leading=13)
    st_td_c    = ps('tc', fontSize=9,  fontName='Helvetica',      textColor=NEGRO,  alignment=TA_CENTER)
    st_td_r    = ps('tr', fontSize=9,  fontName='Helvetica',      textColor=NEGRO,  alignment=TA_RIGHT)
    st_tot_lbl = ps('tl', fontSize=11, fontName='Helvetica-Bold', textColor=BLANCO, alignment=TA_RIGHT)
    st_tot_val = ps('tv', fontSize=11, fontName='Helvetica-Bold', textColor=BLANCO, alignment=TA_RIGHT)

    story = []

    # ── BANNER ─────────────────────────────────────────────────────────────────
    story.append(HeaderBanner(CW))
    story.append(Spacer(1, 0.35*cm))

    # ── RUT + FECHA + CONTACTO ─────────────────────────────────────────────────
    tels_str = "<br/>".join(EMPRESA['telefonos'])
    bloque_izq = Table([
        [Paragraph(f"RUT: {EMPRESA['rut']}", st_rut)],
        [Paragraph(f"<b>FECHA</b>   {datos['fecha'].strftime('%d/%m/%Y')}", st_fecha)],
        [Paragraph(f"Cotizacion No. {datos['numero']}", st_label)],
        [Paragraph(f"<b>Vendedor:</b> {datos['vendedor']}", st_normal)],
    ], colWidths=[CW * 0.55])
    bloque_izq.setStyle(TableStyle([('PADDING', (0,0), (-1,-1), 2)]))

    bloque_der = Table([
        [Paragraph("Contactanos!", st_cont)],
        [Paragraph("📞  💬", ps('ic', fontSize=13, alignment=TA_RIGHT))],
        [Paragraph(tels_str, st_tels)],
    ], colWidths=[CW * 0.45])
    bloque_der.setStyle(TableStyle([('PADDING', (0,0), (-1,-1), 2)]))

    t_top = Table([[bloque_izq, bloque_der]], colWidths=[CW*0.55, CW*0.45])
    t_top.setStyle(TableStyle([
        ('VALIGN',  (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_top)
    story.append(Spacer(1, 0.35*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS, spaceAfter=6))

    # ── SEÑORES ────────────────────────────────────────────────────────────────
    info_rows = [
        [Paragraph("<b>SENORES:</b>",   st_label), Paragraph(datos['cliente'],      st_normal)],
        [Paragraph("<b>Direccion:</b>", st_label), Paragraph(datos['direccion'],    st_normal)],
        [Paragraph("<b>Telefono:</b>",  st_label), Paragraph(datos['telefono_cli'], st_normal)],
    ]
    t_info = Table(info_rows, colWidths=[2.8*cm, CW - 2.8*cm])
    t_info.setStyle(TableStyle([
        ('VALIGN',  (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 0.4*cm))

    # ── PARA TENER EN CUENTA ───────────────────────────────────────────────────
    story.append(Paragraph("<b>PARA TENER EN CUENTA</b>", st_seccion))
    story.append(Spacer(1, 0.15*cm))
    for linea in datos['notas_lista']:
        linea = linea.strip()
        if linea:
            story.append(Paragraph(f"• {linea}", st_bullet))
    story.append(Spacer(1, 0.5*cm))

    # ── TABLA AZUL ─────────────────────────────────────────────────────────────
    c_desc  = CW * 0.50
    c_cant  = CW * 0.12
    c_prec  = CW * 0.19
    c_tot   = CW * 0.19

    filas = [[
        Paragraph("DESCRIPCION",   st_th),
        Paragraph("CANT.",         st_th),
        Paragraph("PRECIO UNIDAD", st_th),
        Paragraph("TOTAL",         st_th),
    ]]

    gran_total = 0
    for item in datos['items']:
        cant   = item.get('cantidad', 1)
        precio = item.get('valor', 0)
        subt   = cant * precio
        gran_total += subt
        filas.append([
            Paragraph(item['descripcion'], st_td),
            Paragraph(str(cant),           st_td_c),
            Paragraph(fmt(precio),         st_td_r),
            Paragraph(fmt(subt),           st_td_r),
        ])

    # Relleno mínimo para que la tabla se vea proporcional
    MIN_FILAS = 4
    while len(filas) < MIN_FILAS + 1:
        filas.append(["", "", "", ""])

    # Fila total (fondo azul oscuro)
    filas.append([
        "", "",
        Paragraph("<b>TOTAL</b>",      st_tot_lbl),
        Paragraph(f"<b>{fmt(gran_total)}</b>", st_tot_val),
    ])

    n = len(filas)
    t_items = Table(filas, colWidths=[c_desc, c_cant, c_prec, c_tot])
    t_items.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND',     (0,0), (-1,0),   AZUL_OSCURO),
        ('FONTNAME',       (0,0), (-1,0),   'Helvetica-Bold'),
        ('TEXTCOLOR',      (0,0), (-1,0),   BLANCO),
        ('ALIGN',          (0,0), (-1,0),   'CENTER'),
        # Cuerpo alternado
        ('ROWBACKGROUNDS', (0,1), (-1, n-2), [AZUL_CLARO, BLANCO]),
        ('FONTNAME',       (0,1), (-1, n-2), 'Helvetica'),
        ('FONTSIZE',       (0,1), (-1, n-2), 9),
        # Fila total
        ('BACKGROUND',     (0, n-1), (-1, n-1), AZUL_OSCURO),
        ('TEXTCOLOR',      (0, n-1), (-1, n-1), BLANCO),
        # General
        ('VALIGN',         (0,0),  (-1,-1), 'MIDDLE'),
        ('GRID',           (0,0),  (-1,-1), 0.4, colors.HexColor("#9fa8da")),
        ('LINEABOVE',      (0,1),  (-1,1),  1.5, BLANCO),
        ('PADDING',        (0,0),  (-1,-1), 7),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 0.6*cm))

    # ── PAGOS + LOGO + MUCHAS GRACIAS ──────────────────────────────────────────
    tels_pago = "<br/>".join(EMPRESA['telefonos'][:2])
    pago_p = Paragraph(
        f"Pagos por medio de:<br/>Nequi y Daviplata:<br/>{tels_pago}<br/>Efectivo.",
        st_pago
    )
    logo_p   = LogoEskalera(size=2.4*cm)
    nombre_p = Paragraph(f"<b>{EMPRESA['nombre']}</b>",
                          ps('nm', fontSize=9, fontName='Helvetica-Bold',
                             textColor=AZUL_OSCURO, alignment=TA_CENTER))
    logo_bloque = Table([[logo_p], [nombre_p]], colWidths=[3*cm])
    logo_bloque.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('PADDING', (0,0),(-1,-1),2)]))

    gracias_p = Paragraph("MUCHAS<br/>GRACIAS", st_gracias)

    t_footer = Table([[pago_p, logo_bloque, gracias_p]],
                      colWidths=[CW*0.38, CW*0.24, CW*0.38])
    t_footer.setStyle(TableStyle([
        ('VALIGN',  (0,0), (-1,-1), 'TOP'),
        ('ALIGN',   (2,0), (2,0),   'RIGHT'),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_footer)
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DORADO, spaceAfter=6))

    # ── SLOGAN + PIE ───────────────────────────────────────────────────────────
    story.append(Paragraph(EMPRESA['slogan'], st_slogan))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Escaleras prefabricadas La Esperanza  ·  RUT {EMPRESA['rut']}  ·  Escalerapp",
        st_pie))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ═══════════════════════════════════════════════════════
#  INTERFAZ STREAMLIT
# ═══════════════════════════════════════════════════════

# Logo + título
st.markdown("""
<div style="text-align:center; padding:24px 0 6px 0;">
  <svg width="88" height="88" viewBox="0 0 88 88" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="8"  y="68" width="20" height="14" rx="3" fill="#00c9a7"/>
    <rect x="28" y="52" width="20" height="30" rx="3" fill="#00c9a7" opacity="0.82"/>
    <rect x="48" y="36" width="20" height="46" rx="3" fill="#00c9a7" opacity="0.64"/>
    <rect x="68" y="20" width="14" height="62" rx="3" fill="#00c9a7" opacity="0.46"/>
    <rect x="8"  y="68" width="20" height="4" rx="1" fill="#ffffff" opacity="0.35"/>
    <rect x="28" y="52" width="20" height="4" rx="1" fill="#ffffff" opacity="0.35"/>
    <rect x="48" y="36" width="20" height="4" rx="1" fill="#ffffff" opacity="0.35"/>
    <rect x="68" y="20" width="14" height="4" rx="1" fill="#ffffff" opacity="0.35"/>
  </svg>
</div>
<div class="app-titulo">Escalerapp</div>
<div class="app-sub">Escaleras La Esperanza · Cotizador</div>
""", unsafe_allow_html=True)

st.markdown("---")

# PASO 1
st.markdown('<div class="titulo-sec">👤 Paso 1 — Datos del cliente</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    cliente      = st.text_input("Nombre del cliente", placeholder="Ej: Amparo Romero cc. 31037102")
    direccion    = st.text_input("Dirección / Conjunto", placeholder="Ej: Alameda de Tierra Grata")
with col2:
    telefono_cli = st.text_input("Teléfono del cliente", placeholder="Ej: 300 123 4567")
    vendedor     = st.text_input("Vendedor", value="Adonai Vargas")

col3, col4 = st.columns(2)
with col3:
    fecha  = st.date_input("Fecha", value=date.today())
with col4:
    numero = st.text_input("Número de cotización", value=date.today().strftime("%Y%m%d"))

st.markdown("---")

# PASO 2
st.markdown('<div class="titulo-sec">🪜 Paso 2 — ¿Qué se va a cotizar?</div>', unsafe_allow_html=True)
st.caption("Describe la escalera con tus palabras y agrega precio y cantidad.")

if 'items' not in st.session_state:
    st.session_state['items'] = [{"descripcion": "", "cantidad": 1, "valor": 0.0}]

for i, item in enumerate(st.session_state['items']):
    st.markdown(f"**Ítem {i+1}**")
    ia, ib, ic = st.columns([3, 1, 1])
    with ia:
        desc = st.text_area("Descripción", value=item['descripcion'], height=90,
                             placeholder="Ej: Escalera recta prefabricada en concreto, 3m de fondo, 1m de ancho, 2.60m de altura. Incluye instalación.",
                             key=f"desc_{i}")
        st.session_state['items'][i]['descripcion'] = desc
    with ib:
        cant = st.number_input("Cantidad", value=int(item.get('cantidad', 1)),
                                min_value=1, step=1, key=f"cant_{i}")
        st.session_state['items'][i]['cantidad'] = cant
    with ic:
        val = st.number_input("Valor unit. (COP)", value=float(item['valor']),
                               min_value=0.0, step=50000.0, format="%.0f", key=f"val_{i}")
        st.session_state['items'][i]['valor'] = val
        subtotal = cant * val
        if subtotal > 0:
            st.markdown(f"<div style='color:#00c9a7;font-weight:700;font-size:0.95rem;'>= {fmt(subtotal)}</div>",
                        unsafe_allow_html=True)
        if len(st.session_state['items']) > 1:
            if st.button("🗑️ Quitar", key=f"del_{i}"):
                st.session_state['items'].pop(i)
                st.rerun()
    st.markdown("<hr style='border-color:#2a2d3a;margin:8px 0;'>", unsafe_allow_html=True)

if st.button("➕  Agregar otro ítem"):
    st.session_state['items'].append({"descripcion": "", "cantidad": 1, "valor": 0.0})
    st.rerun()

total = sum(it['cantidad'] * it['valor'] for it in st.session_state['items'])
st.markdown(
    f"<div class='card card-green' style='text-align:center;margin-top:12px;'>"
    f"<div style='color:#888;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;'>TOTAL COTIZACIÓN</div>"
    f"<div class='precio-gde'>{fmt(total)}</div></div>",
    unsafe_allow_html=True
)

st.markdown("---")

# PASO 3
st.markdown('<div class="titulo-sec">📝 Paso 3 — Para tener en cuenta</div>', unsafe_allow_html=True)
st.caption("Cada línea será un punto en la cotización. Puedes editar o agregar condiciones.")
notas = st.text_area("Condiciones (una por línea)", value=NOTAS_DEFAULT, height=140)

st.markdown("---")

# PASO 4
st.markdown('<div class="titulo-sec">📄 Paso 4 — Generar cotización</div>', unsafe_allow_html=True)

errores = []
if not cliente.strip():
    errores.append("⚠️ Falta el nombre del cliente")
if not any(it['descripcion'].strip() for it in st.session_state['items']):
    errores.append("⚠️ Agrega al menos una descripción en el Paso 2")
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
        "notas_lista":  [l for l in notas.splitlines() if l.strip()],
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
        st.info("💡 Para imprimir: abre el PDF y presiona Ctrl+P (o Cmd+P en Mac).")

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#444;font-size:0.78rem;'>Escalerapp · Escaleras La Esperanza</div>",
    unsafe_allow_html=True
)
