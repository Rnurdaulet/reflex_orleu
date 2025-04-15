import csv
from django.core.management.base import BaseCommand
from apps.people.models import Person

class Command(BaseCommand):
    help = 'Импортирует пользователей в модель Person из CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Путь к CSV-файлу')

    def handle(self, *args, **options):
        path = options['csv_file']

        try:
            with open(path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                created_count = 0
                updated_count = 0

                for row in reader:
                    iin = row['iin'].strip()
                    full_name = row['full_name'].strip()
                    external_id = row['external_id'].strip()

                    person, created = Person.objects.update_or_create(
                        iin=iin,
                        defaults={
                            'full_name': full_name,
                            'external_id': external_id,
                        }
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(f"✅ Создан: {full_name} ({iin})")
                    else:
                        updated_count += 1
                        self.stdout.write(f"♻️ Обновлён: {full_name} ({iin})")

                self.stdout.write(self.style.SUCCESS(
                    f"Импорт завершён: {created_count} создано, {updated_count} обновлено."
                ))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка: {str(e)}"))
