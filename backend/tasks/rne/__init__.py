import pandas as pd
from doit.tools import create_folder
from pandas._libs.tslibs.np_datetime import OutOfBoundsDatetime

from backend import SOURCE_DIR, PREPARE_DIR
from sources import SOURCES

__all__ = ["task_joindre_elus_municipaux_epci"]

MUN_FIELDS = [
    "code_dep",
    "_lib_dep",
    "code_commune",
    "_lib_commune",
    "nom",
    "prenom",
    "sexe",
    "date_naissance",
    "profession",
    "_lib_profession",
    "date_debut_mandat",
    "fonction",
    "date_debut_fonction",
    "nationalite",
]

EPCI_FIELDS = [
    "code_dep",
    "_siren",
    "_lib_dep",
    "code_commune",
    "_code_dep_com",
    "_lib_commune",
    "nom",
    "prenom",
    "sexe",
    "date_naissance",
    "_profession",
    "_lib_profession",
    "date_debut_mandat",
    "fonction",
    "date_debut_fonction",
]


corr_outremer = {
    "ZA": "97",
    "ZB": "97",
    "ZC": "97",
    "ZD": "97",
    "ZM": "97",
    "ZN": "NA",  # on ne gère pas ces outremers là pour le moment
    "ZP": "NA",
    "ZS": "NA",
    "ZW": "NA",
    "ZX": "NA",
}


def task_joindre_elus_municipaux_epci():
    RNE = SOURCES.interieur.rne
    rne_municipaux = SOURCE_DIR / RNE.municipaux.filename
    rne_epci = SOURCE_DIR / RNE.epci.filename
    dest = PREPARE_DIR / RNE.municipaux.filename

    return {
        "file_dep": [rne_municipaux, rne_epci],
        "targets": [dest],
        "actions": [
            (create_folder, [dest.parent]),
            (joindre_elus_municipaux_epci, [rne_municipaux, rne_epci, dest],),
        ],
    }


def parser_dates(df):
    for c in df.columns:
        if c.startswith("date_"):
            try:
                date_corrigee = df[c].str.replace(r"/00(\d{2})$", r"/20\1", regex=True)
                df[c] = pd.to_datetime(date_corrigee, format="%d/%m/%Y")
            except OutOfBoundsDatetime:
                raise ValueError(f"Colonne {c}")


def joindre_elus_municipaux_epci(municipaux_path, epci_path, dest):
    mun = pd.read_csv(
        municipaux_path,
        sep="\t",
        encoding="latin1",
        skiprows=2,
        names=MUN_FIELDS,
        na_values=[""],
        keep_default_na=False,
        usecols=[f for f in MUN_FIELDS if not f.startswith("_")],
        dtype={"code_dep": str, "code_commune": str, "profession": str},
    ).iloc[:-1]

    mun["code_dep"] = mun["code_dep"].map(corr_outremer).fillna(mun["code_dep"])
    mun = mun[mun["code_dep"] != "NA"].drop_duplicates(
        ["code_dep", "code_commune", "nom", "prenom", "date_naissance"]
    )

    mun["code"] = mun["code_dep"] + mun["code_commune"].str.slice(0, 3)
    del mun["code_dep"]
    del mun["code_commune"]
    parser_dates(mun)

    ep = pd.read_csv(
        epci_path,
        sep="\t",
        encoding="latin1",
        skiprows=2,
        names=EPCI_FIELDS,
        na_values=[""],
        keep_default_na=False,
        usecols=[f for f in EPCI_FIELDS if not f.startswith("_")],
        dtype={"code_dep": str, "siren": str, "code_commune": str, "profession": str},
    ).iloc[:-1]

    ep["code_dep"] = ep["code_dep"].map(corr_outremer).fillna(ep["code_dep"])
    ep = ep[ep["code_dep"] != "NA"]

    ep["code"] = ep["code_dep"] + ep["code_commune"].str.slice(0, 3)
    del ep["code_dep"]
    del ep["code_commune"]
    parser_dates(ep)

    res = pd.merge(
        mun,
        ep,
        how="left",
        on=["code", "nom", "prenom", "sexe", "date_naissance"],
        suffixes=["", "_epci"],
    )

    res.to_csv(dest, index=False)
