"""Generador de datos FICTICIOS y reproducibles.

Los nombres de distritos y barrios de Barcelona se usan solo como referencia geográfica.
Códigos, superficies, poblaciones, hogares, fechas y distribuciones son inventados
y no corresponden a estadísticas reales ni oficiales.
"""

import random
from datetime import date
from decimal import Decimal

SOURCE_LABEL = "Fuente sintética de demostración – cifras ficticias"
DEFAULT_SEED = 20240101
YEARS = range(2015, 2025)

DISTRICTS = [
    ("Ciutat Vella", ["el Raval", "el Barri Gòtic", "la Barceloneta", "Sant Pere, Santa Caterina i la Ribera"]),
    ("Eixample", [
        "el Fort Pienc", "la Sagrada Família", "la Dreta de l'Eixample",
        "l'Antiga Esquerra de l'Eixample", "la Nova Esquerra de l'Eixample", "Sant Antoni",
    ]),
    ("Sants-Montjuïc", [
        "el Poble-sec", "la Marina del Prat Vermell", "la Marina de Port", "la Font de la Guatlla",
        "Hostafrancs", "la Bordeta", "Sants - Badal", "Sants",
    ]),
    ("Les Corts", ["les Corts", "la Maternitat i Sant Ramon", "Pedralbes"]),
    ("Sarrià-Sant Gervasi", [
        "Vallvidrera, el Tibidabo i les Planes", "Sarrià", "les Tres Torres",
        "Sant Gervasi - la Bonanova", "Sant Gervasi - Galvany", "el Putxet i el Farró",
    ]),
    ("Gràcia", [
        "Vallcarca i els Penitents", "el Coll", "la Salut", "la Vila de Gràcia",
        "el Camp d'en Grassot i Gràcia Nova",
    ]),
    ("Horta-Guinardó", [
        "el Baix Guinardó", "Can Baró", "el Guinardó", "la Font d'en Fargues", "el Carmel",
        "la Teixonera", "Sant Genís dels Agudells", "Montbau", "la Vall d'Hebron", "la Clota", "Horta",
    ]),
    ("Nou Barris", [
        "Vilapicina i la Torre Llobeta", "Porta", "el Turó de la Peira", "Can Peguera", "la Guineueta",
        "Canyelles", "les Roquetes", "Verdun", "la Prosperitat", "la Trinitat Nova", "Torre Baró",
        "Ciutat Meridiana", "Vallbona",
    ]),
    ("Sant Andreu", [
        "la Trinitat Vella", "Baró de Viver", "el Bon Pastor", "Sant Andreu", "la Sagrera",
        "el Congrés i els Indians", "Navas",
    ]),
    ("Sant Martí", [
        "el Camp de l'Arpa del Clot", "el Clot", "el Parc i la Llacuna del Poblenou",
        "la Vila Olímpica del Poblenou", "el Poblenou", "Diagonal Mar i el Front Marítim del Poblenou",
        "el Besòs i el Maresme", "Provençals del Poblenou", "Sant Martí de Provençals", "la Verneda i la Pau",
    ]),
]

AGE_GROUPS = [
    ("0 a 14 años", 0, 14),
    ("15 a 24 años", 15, 24),
    ("25 a 44 años", 25, 44),
    ("45 a 64 años", 45, 64),
    ("65 a 79 años", 65, 79),
    ("80 años o más", 80, None),
]


def split(total, weights):
    """Reparte un entero según pesos; el resto de redondeo va al último elemento."""
    s = sum(weights)
    parts = [int(total * w / s) for w in weights[:-1]]
    parts.append(total - sum(parts))
    return parts


def generate(seed=DEFAULT_SEED):
    """Devuelve estructuras Python con los datos ficticios (sin tocar la base)."""
    rng = random.Random(seed)
    districts, neighborhoods, populations, age_rows = [], [], [], []
    snapshots = [date(year, 1, 1) for year in YEARS]
    age_groups = AGE_GROUPS

    n_code = 0
    for d_index, (d_name, n_names) in enumerate(DISTRICTS, start=1):
        d_code = f"D{d_index:02d}"
        districts.append({"code": d_code, "name": d_name})
        for n_name in n_names:
            n_code += 1
            code = f"B{n_code:03d}"
            area = Decimal(str(round(rng.uniform(0.35, 9.5), 3)))
            neighborhoods.append({"code": code, "name": n_name, "district_code": d_code, "area_km2": area})

            pop = rng.randint(4_000, 55_000)
            trend = rng.uniform(-0.015, 0.02)
            persons_per_household = rng.uniform(2.1, 2.8)
            women_share = rng.uniform(0.49, 0.54)
            base_weights = [rng.uniform(0.6, 1.4) * w for w in (13, 9, 30, 27, 13, 8)]

            for snap in snapshots:
                pop = max(500, int(pop * (1 + trend + rng.uniform(-0.01, 0.01))))
                women = int(pop * women_share)
                populations.append({
                    "neighborhood_code": code,
                    "date": snap,
                    "total_population": pop,
                    "households": int(pop / persons_per_household),
                    "women": women,
                    "men": pop - women,
                })
                weights = [w * rng.uniform(0.95, 1.05) for w in base_weights]
                for (label, _, _), value in zip(age_groups, split(pop, weights)):
                    age_rows.append({"neighborhood_code": code, "date": snap, "age_label": label, "population": value})

    return {
        "districts": districts,
        "neighborhoods": neighborhoods,
        "snapshots": snapshots,
        "age_groups": age_groups,
        "populations": populations,
        "age_populations": age_rows,
    }
