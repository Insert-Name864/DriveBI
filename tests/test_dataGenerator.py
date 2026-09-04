"""
Tests des fonctions de génération de données
"""

from datetime import datetime, time, timedelta

import pytest
import numpy as np
import pandas as pd

from dataGenerator import (
    charger_configuration,
    generer_magasins,
    choisir_magasin,
    generer_type_service,
    generer_date_heure_commande,
    generer_creneaux,
    generer_articles_panier,
    generer_montant_panier,
    generer_preparation,
    generer_qualite_preparation,
    generer_statut_commande,
    generer_date_heure_remise,
    generer_commandes,
    df_to_csv,
)


@pytest.fixture(scope="module")
def config():
    config = charger_configuration()

    config["volumetrie"]["nombre_magasins"] = 10
    config["volumetrie"]["objectif_commandes"] = 200

    return config


@pytest.fixture
def rng(config):
    return np.random.default_rng(config["seed"])


@pytest.fixture(scope="module")
def dataframe_generes(config):
    rng_dataframe = np.random.default_rng(config["seed"])

    magasins = generer_magasins(rng_dataframe, config)
    commandes = generer_commandes(rng_dataframe, config, magasins)

    return magasins, commandes


@pytest.fixture(scope="module")
def dataframe_magasins(dataframe_generes):
    return dataframe_generes[0]


@pytest.fixture(scope="module")
def dataframe_commandes(dataframe_generes):
    return dataframe_generes[1]


def test_configuration_charge(config):
    assert isinstance(config, dict)
    assert config


def test_generer_bon_nombre_magasins(config, dataframe_magasins):
    assert len(dataframe_magasins) == config["volumetrie"]["nombre_magasins"]


def test_identifiants_magasins_uniques(dataframe_magasins):
    assert dataframe_magasins["id_magasin"].is_unique


def test_indice_efficacite_valide(config, dataframe_magasins):
    minimum = config["magasins"]["indice_efficacite"]["minimum"]
    maximum = config["magasins"]["indice_efficacite"]["maximum"]

    assert (
        dataframe_magasins["indice_efficacite"].between(minimum, maximum).all()
    )


def test_verifie_colonnes_magasins(dataframe_magasins):
    colonnes_attendues = [
        "id_magasin",
        "nom_magasin",
        "region",
        "zone_geographique",
        "type_service",
        "indice_efficacite",
    ]
    assert list(dataframe_magasins.columns) == colonnes_attendues


def test_choix_magasin(rng, dataframe_magasins):
    magasin = choisir_magasin(rng, dataframe_magasins)

    assert isinstance(magasin, pd.Series)
    assert magasin.name in dataframe_magasins.index
    assert magasin.equals(dataframe_magasins.loc[magasin.name])


def test_choisir_magasin_dataframe_vide(rng):
    dataframe_vide = pd.DataFrame()

    with pytest.raises(ValueError):
        choisir_magasin(rng, dataframe_vide)


def test_generer_service_valide(rng, config, dataframe_magasins):
    for _ in range(100):
        magasin = choisir_magasin(rng, dataframe_magasins)
        service = generer_type_service(rng, config, magasin)

        assert service in {"retrait_drive", "livraison_domicile"}


def test_date_commande_dans_intervalle(rng, config):
    date_debut = datetime.fromisoformat(config["periode"]["date_debut"]).date()
    date_fin = datetime.fromisoformat(config["periode"]["date_fin"]).date()

    for _ in range(100):
        date_heure_commande = generer_date_heure_commande(rng, config)

        assert isinstance(date_heure_commande, datetime)
        assert date_debut <= date_heure_commande.date() <= date_fin


def test_heure_commande_dans_intervalle(rng, config):
    heure_commande_minimum = time.fromisoformat(
        config["commandes"]["heure_commande_minimum"]
    ).hour
    heure_commande_maximum = time.fromisoformat(
        config["commandes"]["heure_commande_maximum"]
    ).hour

    for _ in range(100):
        date_heure_commande = generer_date_heure_commande(rng, config)
        assert (
            heure_commande_minimum
            <= date_heure_commande.hour
            <= heure_commande_maximum
        )


def test_generer_creneau_valide(rng, config):
    premier_creneau = time.fromisoformat(config["creneaux"]["premier_creneau"])
    dernier_creneau = time.fromisoformat(config["creneaux"]["dernier_creneau"])
    duree_minutes = config["creneaux"]["duree_minutes"]
    delai_minimum = config["creneaux"]["delai_minimum_commande_minutes"]
    horizon_maximum = config["creneaux"]["horizon_maximum_jours"]

    for _ in range(100):
        date_heure_commande = generer_date_heure_commande(rng, config)
        debut_creneau, fin_creneau = generer_creneaux(
            rng, config, date_heure_commande
        )

        assert isinstance(debut_creneau, datetime)
        assert isinstance(fin_creneau, datetime)

        assert premier_creneau <= debut_creneau.time() <= dernier_creneau
        assert fin_creneau - debut_creneau == timedelta(minutes=duree_minutes)
        assert debut_creneau >= date_heure_commande + timedelta(
            minutes=delai_minimum
        )
        assert (
            debut_creneau.date()
            <= (date_heure_commande + timedelta(days=horizon_maximum)).date()
        )


def test_generer_panier_valide(rng, config):
    nombre_minimum = config["paniers"]["nombre_articles_minimum"]
    nombre_maximum = config["paniers"]["nombre_articles_maximum"]

    for _ in range(100):
        panier = generer_articles_panier(rng, config)

        assert isinstance(panier, int)
        assert nombre_minimum <= panier <= nombre_maximum


def test_generer_montant_panier_valide(rng, config):
    montant_minimum = config["paniers"]["montant_minimum"]
    montant_maximum = config["paniers"]["montant_maximum"]

    for _ in range(100):
        nombre_articles = generer_articles_panier(rng, config)
        montant_panier = generer_montant_panier(rng, config, nombre_articles)

        assert isinstance(montant_panier, float)
        assert montant_minimum <= montant_panier <= montant_maximum


def test_generer_bon_typage_preparation(rng, config, dataframe_magasins):
    magasin = choisir_magasin(rng, dataframe_magasins)
    date_heure_commande = generer_date_heure_commande(rng, config)
    debut_creneau, _ = generer_creneaux(rng, config, date_heure_commande)
    nombre_articles = generer_articles_panier(rng, config)
    preparation = generer_preparation(
        rng,
        config,
        magasin,
        date_heure_commande,
        debut_creneau,
        nombre_articles,
    )

    assert isinstance(preparation, dict)
    assert set(preparation) == {"debut_preparation", "fin_preparation"}

    assert isinstance(preparation["debut_preparation"], datetime)
    assert isinstance(preparation["fin_preparation"], datetime)


def test_generer_preparation_valide(rng, config, dataframe_magasins):
    for _ in range(100):
        magasin = choisir_magasin(rng, dataframe_magasins)
        date_heure_commande = generer_date_heure_commande(rng, config)
        debut_creneau, _ = generer_creneaux(rng, config, date_heure_commande)
        nombre_articles = generer_articles_panier(rng, config)
        preparation = generer_preparation(
            rng,
            config,
            magasin,
            date_heure_commande,
            debut_creneau,
            nombre_articles,
        )

        assert (
            date_heure_commande
            <= preparation["debut_preparation"]
            < preparation["fin_preparation"]
        )


def test_generer_bon_typage_qualite_preparation(rng, config):
    nombre_articles = generer_articles_panier(rng, config)
    qualite_preparation = generer_qualite_preparation(
        rng, config, nombre_articles
    )

    assert isinstance(qualite_preparation, dict)
    assert set(qualite_preparation) == {
        "nombre_prepares",
        "nombre_manquants",
        "nombre_substitues",
    }

    assert isinstance(qualite_preparation["nombre_prepares"], int)
    assert isinstance(qualite_preparation["nombre_manquants"], int)
    assert isinstance(qualite_preparation["nombre_substitues"], int)


def test_generer_qualite_preparation_valide(rng, config):
    for _ in range(100):
        nombre_articles = generer_articles_panier(rng, config)

        qualite_preparation = generer_qualite_preparation(
            rng, config, nombre_articles
        )

        assert 0 <= qualite_preparation["nombre_prepares"] <= nombre_articles
        assert 0 <= qualite_preparation["nombre_manquants"] <= nombre_articles
        assert 0 <= qualite_preparation["nombre_substitues"] <= nombre_articles

        assert (
            qualite_preparation["nombre_prepares"]
            + qualite_preparation["nombre_manquants"]
            == nombre_articles
        )


def test_generer_statut_commande_valide(rng, config, dataframe_magasins):
    statuts_valides = {
        "ANNULEE",
        "NON_RECUPEREE",
        "PARTIELLE",
        "RETIREE",
        "LIVREE",
    }
    for _ in range(100):
        magasin = choisir_magasin(rng, dataframe_magasins)
        service = generer_type_service(rng, config, magasin)
        nombre_articles = generer_articles_panier(rng, config)
        qualite_preparation = generer_qualite_preparation(
            rng, config, nombre_articles
        )
        statut_commande = generer_statut_commande(
            rng, config, service, qualite_preparation
        )

        assert isinstance(statut_commande, str)
        assert statut_commande in statuts_valides


def test_generer_date_heure_remise_valide(rng, config, dataframe_magasins):
    for _ in range(100):
        magasin = choisir_magasin(rng, dataframe_magasins)
        indice_efficacite = magasin["indice_efficacite"]

        service = generer_type_service(rng, config, magasin)
        date_heure_commande = generer_date_heure_commande(rng, config)
        debut_creneau, fin_creneau = generer_creneaux(
            rng, config, date_heure_commande
        )
        nombre_articles = generer_articles_panier(rng, config)

        preparation = generer_preparation(
            rng,
            config,
            magasin,
            date_heure_commande,
            debut_creneau,
            nombre_articles,
        )
        fin_preparation = preparation["fin_preparation"]

        qualite_preparation = generer_qualite_preparation(
            rng, config, nombre_articles
        )
        statut_commande = generer_statut_commande(
            rng, config, service, qualite_preparation
        )
        date_heure_remise = generer_date_heure_remise(
            rng,
            config,
            statut_commande,
            fin_preparation,
            debut_creneau,
            fin_creneau,
            indice_efficacite,
        )

        assert isinstance(date_heure_remise, (datetime, type(None)))

        if date_heure_remise is not None:
            assert date_heure_remise >= fin_preparation


@pytest.mark.parametrize("statut", ["ANNULEE", "NON_RECUPEREE"])
def test_commande_non_remise_sans_date_remise(rng, config, statut):
    fin_preparation = datetime(2025, 1, 1, 10, 0)
    debut_creneau = datetime(2025, 1, 1, 11, 0)
    fin_creneau = datetime(2025, 1, 1, 12, 0)

    date_heure_remise = generer_date_heure_remise(
        rng,
        config,
        statut,
        fin_preparation,
        debut_creneau,
        fin_creneau,
        1.0,
    )

    assert date_heure_remise is None


def test_generer_bon_nombre_commandes(config, dataframe_commandes):
    assert (
        len(dataframe_commandes) == config["volumetrie"]["objectif_commandes"]
    )


def test_identifiants_commandes_uniques(dataframe_commandes):
    assert dataframe_commandes["id_commande"].is_unique


def test_commandes_referencent_magasins_existants(
    dataframe_magasins, dataframe_commandes
):
    assert set(dataframe_commandes["id_magasin"]).issubset(
        set(dataframe_magasins["id_magasin"])
    )


def test_generer_colonnes_commandes_valides(dataframe_commandes):
    colonnes_attendues = [
        "id_commande",
        "id_magasin",
        "date_heure_commande",
        "type_service",
        "debut_creneau_promis",
        "fin_creneau_promis",
        "debut_preparation",
        "fin_preparation",
        "remise_commande",
        "statut_commande",
        "nombre_articles_commandes",
        "nombre_articles_prepares",
        "nombre_articles_manquants",
        "nombre_articles_substitues",
        "montant_commande",
    ]

    assert list(dataframe_commandes.columns) == colonnes_attendues


def test_magasins_csv_valide(config, dataframe_magasins, tmp_path):
    magasins_export = dataframe_magasins.drop(columns=["indice_efficacite"])

    chemin_csv = tmp_path / "magasins_raw.csv"
    df_to_csv(config, magasins_export, chemin_csv)

    dataframe_relu = pd.read_csv(
        chemin_csv,
        sep=config["exports"]["separateur_csv"],
        encoding=config["exports"]["encodage"],
    )

    assert len(dataframe_relu) == len(magasins_export)
    assert list(dataframe_relu.columns) == list(magasins_export.columns)
    assert "indice_efficacite" not in dataframe_relu.columns


def test_commandes_csv_valide(config, dataframe_commandes, tmp_path):
    chemin_csv = tmp_path / "commandes_raw.csv"
    df_to_csv(config, dataframe_commandes, chemin_csv)

    dataframe_relu = pd.read_csv(
        chemin_csv,
        sep=config["exports"]["separateur_csv"],
        encoding=config["exports"]["encodage"],
    )

    assert len(dataframe_relu) == len(dataframe_commandes)
    assert list(dataframe_relu.columns) == list(dataframe_commandes.columns)
