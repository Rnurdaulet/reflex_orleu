import os
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from xhtml2pdf.files import pisaFileObject
from django.conf import settings

def generate_survey_pdf(survey):
    """
    Генерирует PDF и сохраняет его в MEDIA_ROOT/surveys/.
    """
    context = {
        'survey': survey,
        'title': "Анкета участника",
        'note': "Подпись заверяет подлинность данных. Спасибо за участие!",
    }

    html = render_to_string('survey/survey_pdf_template.html', context)

    # Путь к MEDIA_ROOT/surveys/
    output_dir = os.path.join(settings.MEDIA_ROOT, 'surveys')
    os.makedirs(output_dir, exist_ok=True)

    filename = f"survey_{survey.id}.pdf"
    full_path = os.path.join(output_dir, filename)

    with open(full_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html, dest=pdf_file, encoding='utf-8', link_callback=link_callback)

    if pisa_status.err:
        return None

    # Относительный путь для FileField
    relative_path = f"surveys/{filename}"
    survey.pdf_file.name = relative_path
    survey.save(update_fields=["pdf_file"])

    return full_path



def link_callback(uri, rel):
    sUrl = settings.STATIC_URL
    sRoot = settings.STATICFILES_DIRS[0]
    mUrl = settings.MEDIA_URL
    mRoot = settings.MEDIA_ROOT

    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else:
        path = uri

    pisaFileObject.getNamedFile = lambda self: path

    if not os.path.isfile(path):
        raise Exception('media URI must start with %s or %s' % (sUrl, mUrl))

    return path
