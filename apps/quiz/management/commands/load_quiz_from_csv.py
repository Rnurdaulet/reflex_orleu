import csv
from django.core.management.base import BaseCommand
from apps.quiz.models import QuizQuestion, QuizAnswer


class Command(BaseCommand):
    help = "Load quiz questions and answers from CSV file"

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        filepath = options['filepath']
        with open(filepath, encoding='utf-8') as file:
            reader = csv.DictReader(file)
            created_q = 0
            created_a = 0

            for row in reader:
                q, created = QuizQuestion.objects.get_or_create(
                    external_id=row['question_id'],
                    defaults={
                        'name_ru': row['question_ru'],
                        'name_kk': row['question_kk'],
                        'name_en': row['question_en'],
                    }
                )
                if created:
                    created_q += 1

                # Удалим старые ответы, если вопрос уже был
                if not created:
                    q.answers.all().delete()

                # Создаём новые ответы
                for i in range(1, 4):
                    QuizAnswer.objects.create(
                        question=q,
                        external_id=row[f'answer_{i}_id'],
                        name_ru=row[f'answer_{i}_ru'],
                        name_kk=row[f'answer_{i}_kk'],
                        name_en=row[f'answer_{i}_en'],
                        is_correct=row[f'answer_{i}_correct'].strip().lower() == 'true'
                    )
                    created_a += 1

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {created_q} questions and {created_a} answers from {filepath}"
        ))
