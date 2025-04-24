import os
import re
import pdfplumber

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from apps.people.models import Person
from apps.survey.models import SurveyResponse

class Command(BaseCommand):
    help = "Импортирует ответы из PDF в SurveyResponse"

    # Правильный путь к папке с 100 PDF
    PDF_DIR = os.path.join(settings.BASE_DIR, "static", "pdf")

    EXTERNAL_ID_RE = re.compile(r"External ID:\s*(\S+)")
    FULL_NAME_RE   = re.compile(r"Full Name:\s*(.+)")
    GENDER_RE      = re.compile(r"Gender:\s*(Male|Female)", re.IGNORECASE)
    AGE_RE         = re.compile(r"Age:\s*(\d+)")
    SIGNATURE_RE   = re.compile(r"Digital Signature.*", re.DOTALL)

    @staticmethod
    def answer_pattern(n):
        # ловим текст после "1. " до следующего числа или конца текста
        return re.compile(
            fr"{n}\.\s*(.+?)(?=\n\d+\.|\Z)",
            re.DOTALL
        )

    def handle(self, *args, **options):
        for fname in os.listdir(self.PDF_DIR):
            if not fname.lower().endswith(".pdf"):
                continue
            path = os.path.join(self.PDF_DIR, fname)
            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"

            ext_id   = self.EXTERNAL_ID_RE.search(text).group(1).strip()
            full_nm  = self.FULL_NAME_RE.search(text).group(1).strip()
            gender   = self.GENDER_RE.search(text).group(1).lower()
            age      = int(self.AGE_RE.search(text).group(1))
            sig_m    = self.SIGNATURE_RE.search(text)
            signature= sig_m.group(0).strip() if sig_m else ""

            # Сбор ответов 1–5
            answers = {}
            for i in range(1, 6):
                m = self.answer_pattern(i).search(text)
                answers[f"answer_{i}"] = m.group(1).strip() if m else ""

            person, _ = Person.objects.get_or_create(
                external_id=ext_id,
                defaults={"full_name": full_nm, "gender": gender, "age": age},
            )

            with open(path, "rb") as f:
                SurveyResponse.objects.create(
                    person=person,
                    external_id=ext_id,
                    full_name=full_nm,
                    gender=gender,
                    age=age,
                    is_submitted=True,
                    pdf_file=File(f, name=fname),
                    signature=signature,
                    **answers
                )
            self.stdout.write(self.style.SUCCESS(f"Импортирован: {full_nm} ({ext_id})"))
