import contextlib
import csv
import lzma
import pandas as pd
from pathlib import Path

from backend import BASE_DIR, SOURCE_DIR
from tasks.admin_express import COMMUNES_GEOMETRY
from tasks.cog import COMMUNES_CSV, EPCI_CSV, COG_DIR

CODES_POSTAUX = SOURCE_DIR / "laposte" / "codes_postaux.csv"

REFERENCES_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data_france" / "data"
FINAL_REGIONS = DATA_DIR / "regions.csv.lzma"
FINAL_DEPARTEMENTS = DATA_DIR / "departements.csv.lzma"
FINAL_EPCI = DATA_DIR / "epci.csv.lzma"
FINAL_COMMUNES = DATA_DIR / "communes.csv.lzma"
FINAL_CODES_POSTAUX = DATA_DIR / "codes_postaux.csv.lzma"
FINAL_CORRESPONDANCES_CODE_POSTAUX = DATA_DIR / "codes_postaux_communes.csv.lzma"

NULL = r"\N"

__all__ = [
    "task_generer_fichier_regions",
    "task_generer_fichier_departements",
    "task_generer_fichier_epci",
    "task_generer_fichier_communes",
    "task_generer_fichier_codes_postaux",
]


ORDERING = ["COM", "ARM", "COMA", "COMD", None]


def _key(t):
    return (ORDERING.index(t["type"]), t["code"])


@contextlib.contextmanager
def id_from_file(path, read_only=False):
    reference = {}

    full_path = REFERENCES_DIR / path

    with open(full_path, "r") as f:
        r = csv.DictReader(f)
        columns = [c for c in r.fieldnames if c != "id"]

        for d in r:
            id = d.pop("id")
            reference[tuple(d[c] for c in columns)] = int(id)

    last_id = max(reference.values()) if reference else -1

    def get_id(**kwargs):
        nonlocal last_id
        key = tuple(kwargs[c] for c in columns)
        if key in reference:
            return reference[key]
        else:
            if read_only:
                raise KeyError(f"ID inconnue pour {kwargs!r} dans {path}")
            last_id += 1
            return reference.setdefault(key, last_id)

    yield get_id

    with open(full_path, "w") as f:
        w = csv.writer(f,)
        w.writerow(columns + ["id"])
        w.writerows([*t, id] for t, id in reference.items())


def task_generer_fichier_regions():
    src = COG_DIR / "regions.csv"
    return {
        "file_dep": [src],
        "targets": [FINAL_REGIONS],
        "actions": [(generer_fichier_regions, [src, FINAL_REGIONS])],
    }


def task_generer_fichier_departements():
    src = COG_DIR / "departements.csv"
    return {
        "file_dep": [src],
        "targets": [FINAL_DEPARTEMENTS],
        "actions": [(generer_fichier_departements, [src, FINAL_DEPARTEMENTS])],
    }


def task_generer_fichier_epci():
    return {
        "file_dep": [EPCI_CSV],
        "targets": [FINAL_EPCI],
        "actions": [(generer_fichier_epci, [EPCI_CSV, FINAL_EPCI]),],
    }


def task_generer_fichier_communes():
    return {
        "file_dep": [COMMUNES_CSV, COMMUNES_GEOMETRY],
        "targets": [FINAL_COMMUNES],
        "actions": [
            (
                generer_fichier_communes,
                [COMMUNES_CSV, COMMUNES_GEOMETRY, FINAL_COMMUNES],
            ),
        ],
    }


def task_generer_fichier_codes_postaux():
    return {
        "file_dep": [CODES_POSTAUX, REFERENCES_DIR / "communes.csv"],
        "targets": [FINAL_CODES_POSTAUX, FINAL_CORRESPONDANCES_CODE_POSTAUX],
        "actions": [
            (
                generer_fichiers_codes_postaux,
                [
                    CODES_POSTAUX,
                    REFERENCES_DIR / "communes.csv",
                    FINAL_CODES_POSTAUX,
                    FINAL_CORRESPONDANCES_CODE_POSTAUX,
                ],
            )
        ],
    }


def generer_fichier_regions(path, lzma_path):
    with open(path, "r") as f, lzma.open(lzma_path, "wt") as l, id_from_file(
        "regions.csv"
    ) as region_id, id_from_file("communes.csv", True) as commune_id:
        r = csv.DictReader(f)
        w = csv.DictWriter(
            l, fieldnames=["id", "code", "nom", "type_nom", "chef_lieu_id"]
        )
        w.writeheader()
        w.writerows(
            {
                "id": region_id(code=region["reg"]),
                "code": region["reg"],
                "nom": region["nccenr"],
                "type_nom": region["tncc"],
                "chef_lieu_id": commune_id(type="COM", code=region["cheflieu"]),
            }
            for region in r
        )


def generer_fichier_departements(path, lzma_path):
    with open(path, "r") as f, lzma.open(lzma_path, "wt") as l, id_from_file(
        "departements.csv"
    ) as departement_id, id_from_file("regions.csv", True) as region_id, id_from_file(
        "communes.csv", True
    ) as commune_id:
        r = csv.DictReader(f)
        w = csv.DictWriter(
            l, fieldnames=["id", "code", "nom", "type_nom", "chef_lieu_id", "region_id"]
        )
        w.writeheader()
        w.writerows(
            {
                "id": departement_id(code=d["dep"]),
                "code": d["dep"],
                "nom": d["nccenr"],
                "type_nom": d["tncc"],
                "chef_lieu_id": commune_id(type="COM", code=d["cheflieu"]),
                "region_id": region_id(code=d["reg"]),
            }
            for d in r
        )


def generer_fichier_epci(path, lzma_path):
    with open(path, "r") as f, lzma.open(lzma_path, "wt") as l, id_from_file(
        "epci.csv"
    ) as get_id:

        r = csv.DictReader(f)
        w = csv.DictWriter(l, fieldnames=["id", *r.fieldnames])
        w.writeheader()
        w.writerows({"id": get_id(code=epci["code"]), **epci} for epci in r)


COMMUNES_FIELDS = [
    "id",
    "code",
    "type",
    "nom",
    "type_nom",
    "population_municipale",
    "population_cap",
    "departement_id",
    "commune_parent_id",
    "epci_id",
    "geometry",
]


def generer_fichier_communes(communes, communes_geo, dest):
    csv.field_size_limit(2 * 131072)  # double default limit

    with open(communes, "r", newline="") as fc, open(
        communes_geo, "r", newline=""
    ) as fg, lzma.open(dest, "wt") as fl, id_from_file(
        "communes.csv"
    ) as commune_id, id_from_file(
        "epci.csv", True
    ) as epci_id, id_from_file(
        "departements.csv", True
    ) as departement_id:
        rc = csv.DictReader(fc)
        rg = csv.DictReader(fg)

        w = csv.DictWriter(fl, fieldnames=COMMUNES_FIELDS)
        w.writeheader()

        geometry = next(rg)

        for commune in rc:
            k = _key(commune)
            while k > _key(geometry):
                try:
                    geometry = next(rg)
                except StopIteration:
                    geometry = {"type": None, "code": ""}

            if k == _key(geometry):
                commune["geometry"] = geometry["geometry"]
            else:
                commune["geometry"] = NULL

            w.writerow(
                {
                    "id": commune_id(type=commune["type"], code=commune["code"]),
                    "code": commune["code"],
                    "type": commune["type"],
                    "nom": commune["nom"],
                    "type_nom": commune["type_nom"],
                    "population_municipale": commune["population_municipale"] or NULL,
                    "population_cap": commune["population_cap"] or NULL,
                    "departement_id": departement_id(code=commune["code_departement"])
                    if commune["code_departement"]
                    else NULL,
                    "commune_parent_id": commune_id(
                        type="COM", code=commune["commune_parent"]
                    )
                    if commune["commune_parent"]
                    else NULL,
                    "epci_id": epci_id(code=commune["epci"])
                    if commune["epci"]
                    else NULL,
                    "geometry": commune["geometry"],
                }
            )


def generer_fichiers_codes_postaux(
    codes_postaux, reference_communes, final_code_postal, final_corr
):
    communes = pd.read_csv(reference_communes, dtype={"code": str})
    communes["type"] = pd.Categorical(
        communes["type"], categories=["COM", "ARM", "COMA", "COMD"]
    )
    communes = (
        communes.sort_values(["type", "code"])
        .drop_duplicates(["code"])
        .set_index(["code"])["id"]
    )

    codes_postaux = pd.read_csv(
        codes_postaux,
        dtype={"Code_commune_INSEE": str, "Code_postal": str},
        usecols=["Code_commune_INSEE", "Code_postal"],
    ).drop_duplicates()

    with id_from_file("codes_postaux.csv") as id_code_postal:
        with lzma.open(final_code_postal, "wt", newline="") as fl:
            w = csv.DictWriter(fl, fieldnames=["id", "code"])
            w.writeheader()

            w.writerows(
                {"id": id_code_postal(code=code), "code": code}
                for code in codes_postaux["Code_postal"].unique()
            )

        with lzma.open(final_corr, "wt", newline="") as fl:
            w = csv.DictWriter(fl, fieldnames=["codepostal_id", "commune_id"])
            w.writeheader()

            w.writerows(
                {
                    "codepostal_id": id_code_postal(code=ligne.Code_postal),
                    "commune_id": communes.loc[ligne.Code_commune_INSEE],
                }
                for ligne in codes_postaux.itertuples()
                if ligne.Code_commune_INSEE in communes.index
            )
