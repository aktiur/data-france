import csv
import lzma

from doit.tools import create_folder

from backend import BASE_DIR
from tasks.admin_express import COMMUNES_GEOMETRY
from tasks.cog import COMMUNES_CSV, EPCI_CSV

DATA_DIR = BASE_DIR / "data_france" / "data"
FINAL_COMMUNES = DATA_DIR / "communes.csv.lzma"
FINAL_EPCI = DATA_DIR / "epci.csv.lzma"

NULL = r"\N"

__all__ = ["task_generer_fichier_communes", "task_generer_fichier_epci"]


ORDERING = ["COM", "ARM", "COMA", "COMD", None]


def _key(t):
    return (ORDERING.index(t["type"]), t["code"])


def task_generer_fichier_communes():
    return {
        "file_dep": [COMMUNES_CSV, COMMUNES_GEOMETRY, EPCI_CSV],
        "targets": [FINAL_COMMUNES],
        "actions": [
            (create_folder, [DATA_DIR]),
            (
                generer_fichier_communes,
                [COMMUNES_CSV, COMMUNES_GEOMETRY, EPCI_CSV, FINAL_COMMUNES],
            ),
        ],
    }


def task_generer_fichier_epci():
    return {
        "file_dep": [EPCI_CSV],
        "targets": [FINAL_EPCI],
        "actions": [
            (create_folder, [DATA_DIR]),
            (generer_fichier_epci, [EPCI_CSV, FINAL_EPCI]),
        ],
    }


def generer_fichier_epci(path, lzma_path):
    with open(path, "r") as f, lzma.open(lzma_path, "wt") as l:
        r = csv.DictReader(f)
        w = csv.DictWriter(l, fieldnames=["id", *r.fieldnames])
        w.writeheader()
        w.writerows({"id": i, **epci} for i, epci in enumerate(r))


COMMUNES_FIELDS = [
    "id",
    "code",
    "code_departement",
    "type",
    "nom",
    "type_nom",
    "population_municipale",
    "population_cap",
    "commune_parent_id",
    "epci_id",
    "geometry",
]


def generer_fichier_communes(communes, communes_geo, epci, dest):
    with open(epci) as f:
        epci_ids = {e["code"]: i for i, e in enumerate(csv.DictReader(f))}

    parent_ids = {}

    with open(communes, "r", newline="") as fc, open(
        communes_geo, "r", newline=""
    ) as fg, lzma.open(dest, "wt") as fl:
        rc = csv.DictReader(fc)
        rg = csv.DictReader(fg)

        w = csv.DictWriter(fl, fieldnames=COMMUNES_FIELDS)
        w.writeheader()

        geometry = next(rg)

        for i, commune in enumerate(rc):
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

            if commune["type"] == "COM":
                parent_ids[commune["code"]] = i

            w.writerow(
                {
                    "id": i,
                    "code": commune["code"],
                    "code_departement": commune["code_departement"],
                    "type": commune["type"],
                    "nom": commune["nom"],
                    "type_nom": commune["type_nom"],
                    "population_municipale": commune["population_municipale"] or NULL,
                    "population_cap": commune["population_cap"] or NULL,
                    "commune_parent_id": parent_ids[commune["commune_parent"]]
                    if commune["commune_parent"]
                    else NULL,
                    "epci_id": epci_ids[commune["epci"]] if commune["epci"] else NULL,
                    "geometry": commune["geometry"],
                }
            )