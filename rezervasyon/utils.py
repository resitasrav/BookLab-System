import os
import logging
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)


def _find_font_path(filename):
    """Font dosyasını birden fazla konumda ara, bulunan ilk mutlak yolu döndür."""
    candidates = [
        os.path.join(settings.BASE_DIR, "static", "fonts", filename),
        os.path.join(settings.BASE_DIR, "staticfiles", "fonts", filename),
        os.path.join(settings.BASE_DIR, "rezervasyon", "static", "fonts", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def register_fonts():
    """
    DejaVuSans fontunu reportlab/pdfmetrics'e kaydeder.
    Hem normal hem bold için aynı dosyayı kullanır; bu sayede
    bold metinler de Türkçe karakter destekli kalır (fallback olmaz).
    """
    try:
        regular = _find_font_path("DejaVuSans.ttf")
        if not regular:
            logger.error("PDF Font Hatası: DejaVuSans.ttf bulunamadı.")
            return False

        pdfmetrics.registerFont(TTFont("DejaVuSans", regular))
        # Bold varyant yok — aynı dosyayı bold olarak da kaydet.
        # Böylece xhtml2pdf bold elementi render ederken Unicode-desteksiz
        # bir built-in font'a (Helvetica, Times) fallback yapmaz.
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", regular))
        pdfmetrics.registerFontFamily(
            "DejaVuSans",
            normal="DejaVuSans",
            bold="DejaVuSans-Bold",
        )
        return True
    except Exception as e:
        logger.error(f"Font Kayıt Hatası: {e}")
        return False


def link_callback(uri, rel):
    """
    xhtml2pdf'nin URL → filesystem yolu çeviri fonksiyonu.
    /static/ → static/ veya staticfiles/ (collectstatic hedefi)
    /media/  → media/
    """
    sUrl  = settings.STATIC_URL
    mUrl  = settings.MEDIA_URL
    sRoot  = str(settings.BASE_DIR / "static")
    sfRoot = str(settings.BASE_DIR / "staticfiles")
    mRoot  = str(settings.BASE_DIR / "media")

    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri[len(mUrl):])
        return path if os.path.isfile(path) else None

    if uri.startswith(sUrl):
        rel_path = uri[len(sUrl):]
        for root in (sRoot, sfRoot):
            candidate = os.path.join(root, rel_path)
            if os.path.isfile(candidate):
                return candidate
        return None

    return uri


def render_to_pdf(template_src="randevu_pdf.html", context_dict=None, filename="BookLab_rapor.pdf"):
    if context_dict is None:
        context_dict = {}

    import base64
    register_fonts()

    template = get_template(template_src)
    html = template.render(context_dict)

    # Fontu base64 olarak gömüyoruz — xhtml2pdf'de Windows yol sorunu yaşamamak için
    # link_callback üzerinden dosya yolu yerine data URI kullanıyoruz.
    font_path = _find_font_path("DejaVuSans.ttf")
    if font_path:
        with open(font_path, "rb") as f:
            font_b64 = base64.b64encode(f.read()).decode("ascii")
        font_css = (
            "<style>\n"
            "@font-face {\n"
            "    font-family: 'DejaVuSans';\n"
            f"    src: url(\"data:font/truetype;base64,{font_b64}\");\n"
            "    font-weight: normal;\n"
            "}\n"
            "@font-face {\n"
            "    font-family: 'DejaVuSans';\n"
            f"    src: url(\"data:font/truetype;base64,{font_b64}\");\n"
            "    font-weight: bold;\n"
            "}\n"
            "</style>"
        )
        html = html.replace("</head>", font_css + "\n</head>", 1)
    else:
        logger.warning("PDF Font: DejaVuSans.ttf bulunamadı, Türkçe karakterler bozuk görünebilir.")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    pisa_status = pisa.CreatePDF(
        src=html,
        dest=response,
        link_callback=link_callback,
        encoding="UTF-8",
    )

    if pisa_status.err:
        logger.error(f"PDF Üretim Hatası: {pisa_status.err}")
        return HttpResponse("PDF Üretilemedi, teknik bir hata oluştu.")

    return response
