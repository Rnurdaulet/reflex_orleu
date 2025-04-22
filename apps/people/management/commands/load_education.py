from django.core.management.base import BaseCommand
from apps.people.models import EducationLevel

class Command(BaseCommand):
    help = 'Load predefined education levels'

    def handle(self, *args, **options):
        items = [
            "Bachelor degree (a four-year degree)",
            "Specialist degree (a five-year degree)",
            "Master degree (1 year)",
            "Master degree (a two-year degree)",
            "Doctoral degree (3 years)",
            "Doctoral degree (a five-year program)",
        ]
        for idx, desc in enumerate(items, start=1):
            obj, created = EducationLevel.objects.get_or_create(
                external_id=idx,
                defaults={"description": desc}
            )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Exists'}: {obj}"
            ))
