import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, KeepTogether, Flowable)

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", F + "DejaVuSans-Bold.ttf"))
from reportlab.lib.fonts import addMapping
addMapping("Sans", 0, 0, "Sans")
addMapping("Sans", 1, 0, "Sans-Bold")

INK = colors.HexColor("#1b1f24")
MUTED = colors.HexColor("#5b6470")
ACCENT = colors.HexColor("#e8590c")
LINE = colors.HexColor("#c9ced6")
SOFT = colors.HexColor("#f4f5f7")

W, H = letter
M = 18 * mm

title = ParagraphStyle("t", fontName="Sans-Bold", fontSize=22, leading=27, textColor=INK)
sub = ParagraphStyle("s", fontName="Sans", fontSize=10.5, leading=15, textColor=MUTED)
body = ParagraphStyle("b", fontName="Sans", fontSize=10, leading=14.5, textColor=INK)
sec = ParagraphStyle("h", fontName="Sans-Bold", fontSize=13, leading=17, textColor=INK,
                     spaceBefore=4)
q = ParagraphStyle("q", fontName="Sans-Bold", fontSize=9.8, leading=13.5, textColor=INK)
hint = ParagraphStyle("hi", fontName="Sans", fontSize=8.6, leading=12, textColor=MUTED)
opt = ParagraphStyle("o", fontName="Sans", fontSize=9.4, leading=13, textColor=INK)


class Lines(Flowable):
    """Ruled lines for handwritten or typed answers."""
    def __init__(self, n=2, gap=7 * mm):
        super().__init__()
        self.n, self.gap = n, gap

    def wrap(self, aw, ah):
        self.w = aw
        return aw, self.n * self.gap + 2

    def draw(self):
        c = self.canv
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        for i in range(self.n):
            y = (self.n - i - 1) * self.gap + 1
            c.line(0, y, self.w, y)


class SectionBar(Flowable):
    def __init__(self, num, text):
        super().__init__()
        self.num, self.text = num, text

    def wrap(self, aw, ah):
        self.w = aw
        return aw, 14 * mm

    def draw(self):
        c = self.canv
        c.setFillColor(ACCENT)
        c.roundRect(0, 4.5 * mm, 7 * mm, 7 * mm, 1.5 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Sans-Bold", 11)
        c.drawCentredString(3.5 * mm, 6.6 * mm, str(self.num))
        c.setFillColor(INK)
        c.setFont("Sans-Bold", 13)
        c.drawString(10 * mm, 6.4 * mm, self.text)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(0, 3 * mm, self.w, 3 * mm)
        c.translate(0, 0)


def checks(items, cols=2):
    box = "☐"
    cells = [Paragraph(f'<font size="12">{box}</font>&nbsp; {t}', opt) for t in items]
    while len(cells) % cols:
        cells.append("")
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    t = Table(rows, colWidths=[(W - 2 * M) / cols] * cols)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


PENDING = []


def question(text, help_=None, lines=2, options=None, cols=2, other=False):
    parts = PENDING[:] + [Paragraph(text, q)]
    PENDING.clear()
    if help_:
        parts += [Spacer(1, 1), Paragraph(help_, hint)]
    parts.append(Spacer(1, 4))
    if options:
        parts.append(checks(options + (["Otro: ________________"] if other else []), cols))
    if lines:
        parts.append(Lines(lines))
    parts.append(Spacer(1, 7))
    return KeepTogether(parts)


def section(story, n, text):
    PENDING.append(SectionBar(n, text))


def on_page(c, doc):
    c.saveState()
    c.setFillColor(ACCENT)
    c.rect(0, H - 5 * mm, W, 5 * mm, stroke=0, fill=1)
    c.setFont("Sans", 8)
    c.setFillColor(MUTED)
    c.drawString(M, 10 * mm, "Cuestionario para el sitio web de Publimax")
    c.drawRightString(W - M, 10 * mm, f"Página {doc.page}")
    c.restoreState()


def build(path):
    doc = BaseDocTemplate(path, pagesize=letter, leftMargin=M, rightMargin=M,
                          topMargin=16 * mm, bottomMargin=18 * mm,
                          title="Cuestionario para el sitio web de Publimax",
                          author="Publimax", subject="Información para el diseño del sitio web")
    frame = Frame(M, 18 * mm, W - 2 * M, H - 34 * mm, id="f", leftPadding=0,
                  rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])

    s = []
    s.append(Paragraph("Cuestionario para el sitio web", sub))
    s.append(Spacer(1, 2))
    s.append(Paragraph("Publimax · Tampico", title))
    s.append(Spacer(1, 8))
    s.append(Paragraph(
        "Gracias por su tiempo. Con estas respuestas diseñaremos un sitio web que presente "
        "su trabajo en anuncios para fachadas y espectaculares, y que facilite que nuevos "
        "clientes les pidan una cotización. Contesten lo que tengan a la mano; si alguna "
        "pregunta no aplica o no están seguros, déjenla en blanco y la resolvemos juntos.", body))
    s.append(Spacer(1, 8))

    info = Table([[Paragraph("<b>Nombre de quien responde:</b>", opt), Lines(1, 6 * mm),
                   Paragraph("<b>Fecha:</b>", opt), Lines(1, 6 * mm)]],
                 colWidths=[57 * mm, 61 * mm, 15 * mm, None])
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    s.append(info)

    section(s, 1, "Datos de contacto")
    s.append(question("Teléfono(s) de contacto", lines=1))
    s.append(question("Número de WhatsApp para cotizaciones",
                      "Podemos poner un botón de WhatsApp siempre visible en el sitio.",
                      lines=1, options=["Sí, quiero el botón de WhatsApp", "No por ahora"]))
    s.append(question("Correo electrónico", lines=1))
    s.append(question("Dirección del taller u oficina",
                      "Indiquen si desean mostrarla con un mapa de Google en el sitio.",
                      lines=2, options=["Mostrar con mapa", "Mostrar solo la dirección",
                                        "No mostrar la dirección"], cols=3))
    s.append(question("Horario de atención", lines=1))
    s.append(question("Zona que atienden",
                      options=["Tampico", "Ciudad Madero", "Altamira", "Resto de Tamaulipas",
                               "Norte de Veracruz", "Todo México"], cols=3, other=True, lines=0))

    section(s, 2, "Servicios")
    s.append(question("¿Qué servicios ofrecen? Marquen todos los que apliquen.",
                      options=["Anuncios para fachadas", "Anuncios espectaculares",
                               "Letras 3D / corpóreas", "Anuncios luminosos (LED, neón)",
                               "Cajas de luz", "Lonas y viniles",
                               "Rotulación de vehículos y flotillas", "Señalética",
                               "Diseño gráfico", "Instalación y montaje",
                               "Mantenimiento de anuncios", "Trámite de permisos"],
                      other=True, lines=0))
    s.append(question("¿Rentan espacios en espectaculares propios?",
                      "Si es así, indiquen cuántos tienen y en qué ubicaciones.",
                      options=["Sí", "No"], lines=3))
    s.append(question("¿Cuál es el servicio que más quieren promover?", lines=2))

    section(s, 3, "Sobre la empresa")
    s.append(question("¿En qué año empezaron o cuántos años llevan trabajando?", lines=1))
    s.append(question("¿Tienen cifras que quieran destacar?",
                      "Por ejemplo: número de proyectos realizados, clientes atendidos o "
                      "metros cuadrados instalados.", lines=2))
    s.append(question("¿Qué los distingue de la competencia?",
                      options=["Precio", "Rapidez de entrega", "Maquinaria propia",
                               "Garantía", "Calidad de materiales", "Atención personalizada"],
                      cols=3, other=True, lines=2))
    s.append(question("Breve historia o descripción de la empresa",
                      "Unas líneas sobre quiénes son; las usaremos en la sección «Nosotros».",
                      lines=4))
    s.append(question("Clientes que podamos mencionar o cuyo logotipo podamos mostrar",
                      "Solo los que hayan autorizado aparecer en el sitio.", lines=3))

    section(s, 4, "Material visual")
    s.append(question("¿Cuentan con su logotipo en buena calidad?",
                      "Idealmente en formato PNG con fondo transparente, SVG, AI o PDF.",
                      options=["Sí, lo enviaremos", "Solo en baja calidad", "No tenemos"],
                      cols=3, lines=0))
    s.append(question("Colores de su marca",
                      "Si los conocen, anoten los códigos de color; si no, descríbanlos.",
                      lines=1))
    s.append(question("Fotografías de trabajos terminados",
                      "Son lo más importante del sitio. Recomendamos de 10 a 30 fotos de "
                      "buena calidad, de día y de noche (anuncios iluminados), y si es posible "
                      "fotos del antes y después.",
                      options=["Tenemos fotos y las enviaremos", "Tenemos pocas fotos",
                               "Necesitamos una sesión de fotos"], cols=3, lines=0))

    section(s, 5, "Funcionamiento del sitio")
    s.append(question("¿Cómo prefieren que los contacten los clientes desde el sitio?",
                      options=["WhatsApp", "Formulario de cotización", "Llamada telefónica",
                               "Correo electrónico"], other=True, lines=0))
    s.append(question("Si hay formulario, ¿a qué correo deben llegar las solicitudes?", lines=1))
    s.append(question("Estructura del sitio",
                      options=["Una sola página con secciones (Inicio, Servicios, Portafolio, "
                               "Nosotros, Contacto)",
                               "Varias páginas independientes"], cols=1, lines=0))
    s.append(question("¿Tienen dominio y hosting?",
                      "Por ejemplo, publimax.com.mx.",
                      options=["Sí, ya tenemos dominio", "Sí, ya tenemos hosting",
                               "No tenemos ninguno", "No estoy seguro"], lines=1))

    section(s, 6, "Estilo y redes sociales")
    s.append(question("Estilo visual preferido",
                      options=["Moderno y oscuro (resalta los anuncios iluminados)",
                               "Claro y corporativo", "Colorido y llamativo",
                               "Lo dejamos a criterio del diseñador"], lines=0))
    s.append(question("Sitios web que les gusten como referencia",
                      "Pueden ser de su ramo o de cualquier otro; anoten qué les gusta de cada uno.",
                      lines=3))
    s.append(question("Redes sociales a enlazar",
                      options=["Facebook", "Instagram", "TikTok", "YouTube",
                               "Google Maps / Google Business", "LinkedIn"], cols=3, lines=0))
    s.append(question("Usuario o enlace de cada red social", lines=2))

    section(s, 7, "Comentarios adicionales")
    s.append(question("¿Algo más que quieran que aparezca en el sitio?",
                      "Promociones, certificaciones, garantías, preguntas frecuentes, etc.",
                      lines=5))

    s.append(Spacer(1, 6))
    note = Table([[Paragraph(
        "<b>Cómo enviar este cuestionario:</b> pueden llenarlo a mano y enviar una foto de "
        "cada página, o responder en un mensaje siguiendo la numeración de las secciones. "
        "Envíen el logotipo y las fotografías en su mejor calidad; por WhatsApp, de "
        "preferencia como «documento» para que no se compriman.", body)]],
        colWidths=[W - 2 * M])
    note.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT),
                              ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
                              ("LEFTPADDING", (0, 0), (-1, -1), 10),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                              ("TOPPADDING", (0, 0), (-1, -1), 8),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    s.append(KeepTogether([note]))

    doc.build(s)


build(sys.argv[1])
