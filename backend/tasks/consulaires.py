import pandas as pd
import requests
from bs4 import BeautifulSoup
from doit.tools import create_folder, run_once

from sources import PREPARE_DIR
import csv


__all__ = [
    "task_recuperer_circonscriptions_consulaires",
    "task_recuperer_sous_circonscriptions_consulaires",
    "task_recuperer_liste_conseillers_consulaires",
    "task_recuperer_details_conseillers_consulaires",
]

CONSULAIRE_DIR = PREPARE_DIR / "consulaires"
LISTE_CIRCONSCRIPTIONS = CONSULAIRE_DIR / "circonscriptions.csv"
LISTE_SOUS_CIRCONSCRIPTIONS = CONSULAIRE_DIR / "sous_circonscriptions.csv"
LISTE_CONSEILLERS_TEMP = CONSULAIRE_DIR / "conseillers_temp.csv"
LISTE_CONSEILLERS = CONSULAIRE_DIR / "conseillers.csv"

AFE_DOMAIN = "https://www.assemblee-afe.fr/"
AFE_LISTE = f"{AFE_DOMAIN}-annuaire-des-conseillers-.html"
URL_CIRCONSCRIPTIONS = (
    "https://www.assemblee-afe.fr/spip.php?page=mots.json&id_groupe=16"
)
URL_SOUS_CIRCONSCRIPTIONS = "https://www.assemblee-afe.fr/spip.php?page=sous_mots.json&id_groupe=19&id_mot={id_afe}"
URL_CONSEILLERS = "https://www.assemblee-afe.fr/spip.php?page=conseillers.json&id_mot={id_sous_circonscription}"


correspondance = {
    "Profession ou qualité": "profession",
    "Élu(e) en": "dates_election",
    "Chef-lieu de circonscription": "circonscription_chef_lieu",
    "Circonscription": "circonscription",
    "Commission": "commission",
    "Groupe à l'assemblée": "groupe",
    "Email AFE": "email_principal",
    "Autre adresse email": "email_autre",
    "Courrier valise diplomatique": "adresse_diplomatique",
    "Adresse à l'étranger": "adresse_etranger",
    "Adresse en France": "adresse_france",
    "Courrier local": "adresse_locale",
    "Téléphone cellulaire à l'étranger": "telephone_mobile_etranger",
    "Téléphone cellulaire en France": "telephone_mobile_france",
    "Téléphone fixe à l'étranger": "telephone_fixe_etranger",
    "Téléphone fixe en France": "telephone_fixe_france",
    "Page web personnelle": "site_personnel",
    "Mandat particulier": "mandat_particulier",
}


def task_recuperer_circonscriptions_consulaires():
    return {
        "uptodate": [run_once],
        "targets": [LISTE_CIRCONSCRIPTIONS],
        "actions": [
            (create_folder, (CONSULAIRE_DIR,)),
            (recuperer_circonscriptions, (LISTE_CIRCONSCRIPTIONS,)),
        ],
    }


def task_recuperer_sous_circonscriptions_consulaires():
    return {
        "file_dep": [LISTE_CIRCONSCRIPTIONS],
        "targets": [LISTE_SOUS_CIRCONSCRIPTIONS],
        "actions": [
            (
                recuperer_sous_circonscriptions,
                (LISTE_CIRCONSCRIPTIONS, LISTE_SOUS_CIRCONSCRIPTIONS),
            )
        ],
    }


def task_recuperer_liste_conseillers_consulaires():
    return {
        "file_dep": [LISTE_SOUS_CIRCONSCRIPTIONS],
        "targets": [LISTE_CONSEILLERS_TEMP],
        "actions": [
            (
                recuperer_liste_conseillers_par_sous_circonscription,
                (LISTE_SOUS_CIRCONSCRIPTIONS, LISTE_CONSEILLERS_TEMP),
            )
        ],
    }


def task_recuperer_details_conseillers_consulaires():
    return {
        "file_dep": [LISTE_CONSEILLERS_TEMP],
        "targets": [LISTE_CONSEILLERS],
        "actions": [
            (
                recuperer_details_conseillers,
                (
                    LISTE_CONSEILLERS_TEMP,
                    LISTE_CONSEILLERS,
                ),
            ),
        ],
    }


def recuperer_circonscriptions(target):
    res = requests.get(URL_CIRCONSCRIPTIONS)
    res.raise_for_status()

    circonscriptions = res.json()

    with target.open("w") as fd:
        w = csv.writer(fd)
        w.writerow(["id", "nom"])
        w.writerows([c["id"], c["titre"]] for c in circonscriptions)


def recuperer_sous_circonscriptions(circonscriptions, target):
    with circonscriptions.open("r") as fd_cs, target.open("w") as fd_consulats:
        circos = csv.DictReader(fd_cs)
        w = csv.writer(fd_consulats)
        w.writerow(["id", "nom", "capitale", "id_afe"])

        for c in circos:
            res = requests.get(URL_SOUS_CIRCONSCRIPTIONS.format(id_afe=c["id"]))
            res.raise_for_status()
            w.writerows(
                [sc["id"], sc["titre"], sc["capitale"], c["id"]] for sc in res.json()
            )


def recuperer_liste_conseillers_par_sous_circonscription(sous_circonscriptions, target):
    with sous_circonscriptions.open("r") as fd_sc, target.open("w") as fd_cons:
        sous_circos = csv.DictReader(fd_sc)
        w = csv.DictWriter(
            fd_cons,
            fieldnames=["id", "prenom", "nom", "url", "id_sous_circonscription"],
            extrasaction="ignore",
        )
        w.writeheader()

        for sc in sous_circos:
            res = requests.get(URL_CONSEILLERS.format(id_sous_circonscription=sc["id"]))
            res.raise_for_status()
            w.writerows(
                {**cons, "id_sous_circonscription": sc["id"]} for cons in res.json()
            )


def recuperer_details_conseillers(liste_conseillers, dest):
    conseillers = pd.read_csv(liste_conseillers)

    with liste_conseillers.open("r") as fd_cons, dest.open("w") as fd_d:
        conseillers = csv.DictReader(fd_cons)
        w = csv.DictWriter(
            fd_d,
            fieldnames=[
                *conseillers.fieldnames,
                "date_naissance",
                "lieu_naissance",
                "titre",
                *correspondance.values(),
            ],
        )
        w.writeheader()
        w.writerows({**c, **recuperer_infos_conseiller(c["url"])} for c in conseillers)


def recuperer_listes_pages():
    res = requests.get(AFE_LISTE)
    res.raise_for_status()

    soup = BeautifulSoup(res.content, "lxml")
    return [a.attrs["href"] for a in soup("a", "tt-upp")]


def recuperer_infos_conseiller(url):
    res = requests.get(f"{AFE_DOMAIN}{url}")
    res.raise_for_status()

    soup = BeautifulSoup(res.content, "lxml")
    header = soup.article.header

    titre, *_ = header.h1.contents[0].strip().split(" ", 1)
    # on écarte le premier qui est traité à part (date et lieu de naissance)
    fields = [li for li in soup.article("li") if len(li.contents) == 2 and li.strong][
        1:
    ]

    infos = {
        correspondance[li.contents[0].text.strip(": ")]: li.contents[1] for li in fields
    }

    bloc_naissance = header.ul("li")[0]
    if len(bloc_naissance.contents) > 1:
        infos["date_naissance"], *lieu = bloc_naissance.contents[1].split(" à ")
        if lieu:
            infos["lieu_naissance"] = lieu[0]

    if "email_principal" in infos:
        infos["email_principal"] = infos["email_principal"].text.replace(" chez ", "@")
    if "email_autre" in infos:
        infos["email_autre"] = infos["email_autre"].text.replace(" chez ", "@")

    return {
        "titre": titre,
        **{
            k: v.strip() if isinstance(v, str) else v.text.strip()
            for k, v in infos.items()
        },
    }
