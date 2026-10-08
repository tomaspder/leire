from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core.safety import ensure_demo_database
from demografia import demo_seed
from demografia.models import (
    AgeGroup,
    District,
    Neighborhood,
    NeighborhoodAgePopulation,
    NeighborhoodPopulation,
    PopulationSnapshot,
)

MODELS_DELETE_ORDER = [
    NeighborhoodAgePopulation,
    NeighborhoodPopulation,
    Neighborhood,
    District,
    PopulationSnapshot,
    AgeGroup,
]


class Command(BaseCommand):
    help = (
        "Carga datos FICTICIOS de demostración. Solo se ejecuta con APP_DB_MODE=demo, "
        "contra una base local cuyo nombre contenga 'demo'."
    )

    def add_arguments(self, parser):
        parser.add_argument("--reemplazar", action="store_true",
                            help="Borra los datos de demostración existentes antes de cargar.")
        parser.add_argument("--semilla", type=int, default=demo_seed.DEFAULT_SEED,
                            help="Semilla para generar datos reproducibles.")

    def handle(self, *args, **options):
        ensure_demo_database(connection)

        has_data = any(model.objects.exists() for model in MODELS_DELETE_ORDER)
        if has_data and not options["reemplazar"]:
            raise CommandError("La base ya contiene datos. Use --reemplazar para borrarlos y volver a cargar.")

        data = demo_seed.generate(options["semilla"])
        with transaction.atomic():
            if has_data:
                for model in MODELS_DELETE_ORDER:
                    model.objects.all().delete()
            self._load(data)

        self.stdout.write(self.style.SUCCESS(
            f"Datos ficticios cargados: {len(data['districts'])} distritos, "
            f"{len(data['neighborhoods'])} barrios, {len(data['snapshots'])} períodos, "
            f"{len(data['populations'])} registros de población, "
            f"{len(data['age_populations'])} registros por edad."
        ))

    def _load(self, data):
        districts = {
            obj.code: obj
            for obj in District.objects.bulk_create(
                District(code=d["code"], name=d["name"]) for d in data["districts"]
            )
        }
        neighborhoods = {
            obj.code: obj
            for obj in Neighborhood.objects.bulk_create(
                Neighborhood(code=n["code"], name=n["name"], area_km2=n["area_km2"],
                             district=districts[n["district_code"]])
                for n in data["neighborhoods"]
            )
        }
        snapshots = {
            obj.reference_date: obj
            for obj in PopulationSnapshot.objects.bulk_create(
                PopulationSnapshot(reference_date=d, source_label=demo_seed.SOURCE_LABEL) for d in data["snapshots"]
            )
        }
        age_groups = {
            obj.label: obj
            for obj in AgeGroup.objects.bulk_create(
                AgeGroup(label=label, min_age=lo, max_age=hi) for label, lo, hi in data["age_groups"]
            )
        }
        NeighborhoodPopulation.objects.bulk_create(
            (
                NeighborhoodPopulation(
                    neighborhood=neighborhoods[p["neighborhood_code"]],
                    snapshot=snapshots[p["date"]],
                    total_population=p["total_population"],
                    households=p["households"],
                    women=p["women"],
                    men=p["men"],
                )
                for p in data["populations"]
            ),
            batch_size=1000,
        )
        NeighborhoodAgePopulation.objects.bulk_create(
            (
                NeighborhoodAgePopulation(
                    neighborhood=neighborhoods[a["neighborhood_code"]],
                    snapshot=snapshots[a["date"]],
                    age_group=age_groups[a["age_label"]],
                    population=a["population"],
                )
                for a in data["age_populations"]
            ),
            batch_size=1000,
        )
