from django.core.management.base import BaseCommand
from apps.people.models import Region

class Command(BaseCommand):
    help = 'Load predefined regions'

    def handle(self, *args, **options):
        items = [
            "Representative office in Zhetisu region, Taldykorgan city",
            "Institute of Professional Development in Akmola Region, Kokshetau",
            "Institute of Professional Development for Aktobe Region, Aktobe city",
            "Institute of Professional Development for Almaty Region, Almaty city",
            "Institute of Professional Development for Atyrau Region, Atyrau city",
            "Institute of Professional Development for the East Kazakhstan Region, Ust-Kamenogorsk",
            "Institute of Professional Development in Almaty",
            "Institute of Professional Development in Zhambyl Region, Taraz city",
            "Institute of Professional Development for the West Kazakhstan Region, Uralsk",
            "Institute of Professional Development for the Karaganda Region, Karaganda city",
            "Institute of Professional Development for Kostanay region, Kostanay city",
            "Institute of Professional Development in Kyzylorda region, Kyzylorda city",
            "Institute of Professional Development for Mangistau Region, Aktau city",
            "Institute of Professional Development for Pavlodar Region, Pavlodar city",
            "Institute of Professional Development for the North Kazakhstan Region, Petropavlovsk",
            "Institute of Professional Development for the Turkestan region",
            "Institute of Professional Development in Shymkent",
            "Central administration (trainers)",
            "Central administration (managers)",
        ]
        for idx, desc in enumerate(items, start=1):
            obj, created = Region.objects.get_or_create(
                external_id=idx,
                defaults={"description": desc}
            )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Exists'}: {obj}"
            ))
