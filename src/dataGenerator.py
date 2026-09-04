"""
Génération des données synthétiques pour la visualisation BI
"""

from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def charger_configuration() -> dict[str, Any]:
    """
    Charge la configuration YAML du générateur de données.

    Le fichier attendu est `config/generation_config.yaml`,
    localisé relativement à la racine du projet.

    Returns:
        dict[str, Any]:
            Configuration complète du générateur.

    Raises:
        FileNotFoundError:
            Si le fichier de configuration est introuvable.
        ValueError:
            Si le contenu YAML ne correspond pas à un dictionnaire.
    """

    chemin_projet = Path(__file__).resolve().parent.parent
    chemin_config = chemin_projet / "config" / "generation_config.yaml"

    if not chemin_config.exists():
        raise FileNotFoundError(
            f"Le fichier de configuration est introuvable : {chemin_config}"
        )

    with chemin_config.open("r", encoding="utf-8") as fichier:
        config = yaml.safe_load(fichier)

    if not isinstance(config, dict):
        raise ValueError(
            "Le fichier de configuration YAML doit contenir un dictionnaire."
        )

    return config


def generer_magasins(
    rng: np.random.Generator, config: dict[str, Any]
) -> pd.DataFrame:
    """
    Génère le référentiel synthétique des magasins Drive.

    Les régions, zones géographiques, types de service et indices
    d'efficacité sont générés à partir de la configuration.

    L'indice d'efficacité est une variable interne de simulation :
    il est utilisé lors de la génération des commandes mais n'a pas
    vocation à être exporté dans le fichier brut des magasins.

    Args:
        rng:
            Générateur aléatoire NumPy partagé par le pipeline.
        config:
            Configuration complète de génération.

    Returns:
        pd.DataFrame:
            DataFrame contenant les magasins générés.
    """
    nb_magasin = config["volumetrie"]["nombre_magasins"]
    config_magasin = config["magasins"]

    region_magasin = config_magasin["regions"]["valeurs"]
    probabilites_region = config_magasin["regions"]["probabilites"]

    zone_magasin = config_magasin["zones_geographiques"]["valeurs"]
    probabilites_zone = config_magasin["zones_geographiques"]["probabilites"]

    service_magasin = config_magasin["type_service"]
    efficacite_magasin = config_magasin["indice_efficacite"]

    lignes = []
    for numero in range(1, nb_magasin + 1):
        region = rng.choice(region_magasin, p=probabilites_region)
        zone = rng.choice(zone_magasin, p=probabilites_zone)
        service = rng.choice(service_magasin)
        indice_efficacite = round(
            float(
                rng.uniform(
                    low=efficacite_magasin["minimum"],
                    high=efficacite_magasin["maximum"],
                )
            ),
            1,
        )

        ligne = {
            "id_magasin": f"MG{numero:03d}",
            "nom_magasin": f"Drive{numero:02d}",
            "region": region,
            "zone_geographique": zone,
            "type_service": service,
            "indice_efficacite": indice_efficacite,
        }

        lignes.append(ligne)
    return pd.DataFrame(lignes)


def choisir_magasin(
    rng: np.random.Generator, magasins: pd.DataFrame
) -> pd.Series:
    """
    Sélectionne aléatoirement un magasin dans le référentiel.

    Args:
        rng:
            Générateur aléatoire NumPy.
        magasins:
            DataFrame contenant les magasins disponibles.

    Returns:
        pd.Series:
            Ligne correspondant au magasin sélectionné.

    Raises:
        ValueError:
            Si le DataFrame des magasins est vide.
    """
    if magasins.empty:
        raise ValueError("Le DataFrame des magasins est vide.")

    position = int(rng.integers(low=0, high=len(magasins)))
    return magasins.iloc[position]


def generer_type_service(
    rng: np.random.Generator, config: dict[str, Any], magasin: pd.Series
) -> str:
    """
    Détermine le type de service associé à une commande.

    Pour un magasin spécialisé, le type de service du magasin est
    directement utilisé. Pour un magasin mixte, le service est tiré
    aléatoirement selon la répartition définie dans la configuration.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.
        magasin:
            Magasin auquel appartient la commande.

    Returns:
        str:
            Type de service de la commande.
    """
    commandes_config = config["commandes"]

    service_disponible = magasin["type_service"]
    if service_disponible == "mixte":
        return rng.choice(
            ["retrait_drive", "livraison_domicile"],
            p=[
                commandes_config["taux_retrait_drive"],
                commandes_config["taux_livraison"],
            ],
        )

    return service_disponible


def generer_date_heure_commande(
    rng: np.random.Generator, config: dict[str, Any]
) -> datetime:
    """
    Génère la date et l'heure de création d'une commande.

    La date est comprise dans la période définie dans la configuration
    et l'heure respecte la plage horaire de création des commandes.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.

    Returns:
        datetime:
            Date et heure synthétiques de création de la commande.
    """
    date_debut = datetime.fromisoformat(config["periode"]["date_debut"])
    date_fin = datetime.fromisoformat(config["periode"]["date_fin"])
    heure_commande_minimum = time.fromisoformat(
        config["commandes"]["heure_commande_minimum"]
    ).hour
    heure_commande_maximum = time.fromisoformat(
        config["commandes"]["heure_commande_maximum"]
    ).hour

    nombre_jours = (date_fin - date_debut).days
    decalage_jours = int(rng.integers(0, nombre_jours + 1))
    date_commande = date_debut + timedelta(days=decalage_jours)

    heure = int(
        rng.integers(heure_commande_minimum, heure_commande_maximum + 1)
    )
    minute = int(rng.integers(0, 60))
    seconde = int(rng.integers(0, 60))

    return date_commande.replace(hour=heure, minute=minute, second=seconde)


def generer_creneaux(
    rng: np.random.Generator,
    config: dict[str, Any],
    date_heure_commande: datetime,
) -> tuple[datetime, datetime]:
    """
    Génère un créneau promis admissible pour une commande.

    Le créneau respecte le délai minimum après la commande,
    les horaires des créneaux et l'horizon maximum configuré.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.
        date_heure_commande:
            Date et heure de création de la commande.

    Returns:
        tuple[datetime, datetime]:
            Date-heure de début et date-heure de fin du créneau promis.

    Raises:
        ValueError:
            Si aucun créneau admissible ne peut être généré.
    """
    creneaux_config = config["creneaux"]
    duree_creneau = creneaux_config["duree_minutes"]
    premier_creneau = time.fromisoformat(creneaux_config["premier_creneau"])
    dernier_creneau = time.fromisoformat(creneaux_config["dernier_creneau"])
    delai_minimum = creneaux_config["delai_minimum_commande_minutes"]
    horizon_maximum = creneaux_config["horizon_maximum_jours"]

    date_minimale = date_heure_commande + timedelta(minutes=delai_minimum)
    creneaux_possibles = []
    for decalage_jour in range(horizon_maximum + 1):
        jour = date_heure_commande.date() + timedelta(days=decalage_jour)
        debut = datetime.combine(jour, premier_creneau)
        dernier_creneau_jour = datetime.combine(jour, dernier_creneau)

        while debut <= dernier_creneau_jour:
            fin = debut + timedelta(minutes=duree_creneau)
            if debut >= date_minimale:
                creneaux_possibles.append((debut, fin))
            debut = fin

    if not creneaux_possibles:
        raise ValueError("Aucun créneau admissible n'a pu être généré.")

    index = int(rng.integers(0, len(creneaux_possibles)))

    return creneaux_possibles[index]


def generer_articles_panier(
    rng: np.random.Generator, config: dict[str, Any]
) -> int:
    """
    Génère le nombre d'articles d'une commande.

    Le nombre d'articles suit une distribution triangulaire définie
    par les valeurs minimale, moyenne et maximale de la configuration.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.

    Returns:
        int:
            Nombre d'articles commandés.
    """
    config_panier = config["paniers"]
    nombre_minimum = config_panier["nombre_articles_minimum"]
    nombre_moyen = config_panier["nombre_articles_moyen"]
    nombre_maximum = config_panier["nombre_articles_maximum"]

    valeur = rng.triangular(
        left=nombre_minimum, mode=nombre_moyen, right=nombre_maximum
    )

    return max(nombre_minimum, int(round(valeur)))


def generer_montant_panier(
    rng: np.random.Generator, config: dict[str, Any], nombre_articles: int
) -> float:
    """
    Génère le montant d'une commande à partir de son nombre d'articles.

    Le prix moyen d'un article suit une distribution lognormale.
    Le montant final est borné par les valeurs minimale et maximale
    définies dans la configuration.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.
        nombre_articles:
            Nombre d'articles commandés.

    Returns:
        float:
            Montant synthétique de la commande, arrondi à deux décimales.
    """
    config_panier = config["paniers"]
    montant_minimum = config_panier["montant_minimum"]
    montant_maximum = config_panier["montant_maximum"]
    distribution = config_panier["distribution_mathematique"]

    prix_moyen_article = rng.lognormal(
        mean=distribution["mean"], sigma=distribution["sigma"]
    )
    montant = nombre_articles * prix_moyen_article

    montant = min(max(montant, montant_minimum), montant_maximum)

    return round(float(montant), 2)


def generer_preparation(
    rng: np.random.Generator,
    config: dict[str, Any],
    magasin: pd.Series,
    date_heure_commande: datetime,
    debut_creneau: datetime,
    nombre_articles: int,
) -> dict[str, datetime]:
    """
    Génère les dates de début et de fin de préparation d'une commande.

    La durée dépend notamment du nombre d'articles, de la variabilité
    configurée et de l'indice d'efficacité du magasin.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.
        magasin:
            Magasin chargé de préparer la commande.
        date_heure_commande:
            Date et heure de création de la commande.
        debut_creneau:
            Date et heure de début du créneau promis.
        nombre_articles:
            Nombre d'articles à préparer.

    Returns:
        dict[str, datetime]:
            Dictionnaire contenant `debut_preparation`
            et `fin_preparation`.
    """
    config_preparation = config["preparation"]
    temps_fixe = config_preparation["temps_fixe_minutes"]
    secondes_article = config_preparation["secondes_par_article"]
    variabilite = config_preparation["variabilite"]
    config_marge_creneau = config_preparation["marge_avant_creneau"]
    delai_avant_preparation = config_preparation["delai_avant_preparation"]

    duree_base_secondes = temps_fixe * 60 + nombre_articles * secondes_article
    facteur_aléatoire = rng.uniform(1 - variabilite, 1 + variabilite)

    indice_efficacite = magasin["indice_efficacite"]
    duree_reelle_secondes = round(
        duree_base_secondes * facteur_aléatoire / indice_efficacite
    )

    marge_avant_creneau = timedelta(
        minutes=int(
            rng.integers(
                config_marge_creneau["minimale"],
                config_marge_creneau["maximale"] + 1,
            )
        )
    )
    fin_preparation = debut_creneau - marge_avant_creneau
    debut_preparation = fin_preparation - timedelta(
        seconds=float(duree_reelle_secondes)
    )

    if debut_preparation < date_heure_commande:
        debut_preparation = date_heure_commande + timedelta(
            minutes=int(
                rng.integers(
                    delai_avant_preparation["minimum"],
                    delai_avant_preparation["maximum"] + 1,
                )
            )
        )
        fin_preparation = debut_preparation + timedelta(
            seconds=float(duree_reelle_secondes)
        )

    return {
        "debut_preparation": debut_preparation,
        "fin_preparation": fin_preparation,
    }


def generer_qualite_preparation(
    rng: np.random.Generator, config: dict[str, Any], nombre_articles: int
) -> dict[str, int]:
    """
    Génère les indicateurs de qualité de préparation d'une commande.

    La fonction simule les articles manquants et les substitutions
    selon les probabilités définies dans la configuration.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.
        nombre_articles:
            Nombre total d'articles commandés.

    Returns:
        dict[str, int]:
            Nombre d'articles préparés, manquants et substitués.
    """
    qualite_config = config["qualite_preparation"]

    commande_avec_manquant = (
        rng.random() < qualite_config["taux_commande_avec_manquant"]
    )

    nombre_manquants = 0
    nombre_substitues = 0

    if commande_avec_manquant:
        nombre_manquants_bruts = int(
            rng.binomial(
                n=nombre_articles, p=qualite_config["taux_article_manquant"]
            )
        )
        nombre_manquants_bruts = max(1, nombre_manquants_bruts)

        nombre_substitues = int(
            rng.binomial(
                n=nombre_manquants_bruts,
                p=qualite_config["taux_substitution_si_manquant"],
            )
        )

        nombre_manquants = nombre_manquants_bruts - nombre_substitues

    nombre_prepares = nombre_articles - nombre_manquants

    return {
        "nombre_prepares": nombre_prepares,
        "nombre_manquants": nombre_manquants,
        "nombre_substitues": nombre_substitues,
    }


def generer_statut_commande(
    rng: np.random.Generator,
    config: dict[str, Any],
    type_service: str,
    donnees_qualite: dict[str, int],
) -> str:
    """
    Détermine le statut final d'une commande.

    Le statut tient compte de l'annulation, de la non-récupération
    éventuelle d'une commande Drive, des articles manquants et du
    type de service.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.
        type_service:
            Type de service de la commande.
        donnees_qualite:
            Résultat de la génération de qualité de préparation.

    Returns:
        str:
            Statut final de la commande.
    """
    commandes_config = config["commandes"]

    tirage = rng.random()

    seuil_annulation = commandes_config["taux_annulation"]
    seuil_non_recuperee = (
        seuil_annulation + commandes_config["taux_non_recuperee"]
    )

    if tirage < seuil_annulation:
        return "ANNULEE"

    if type_service == "retrait_drive" and tirage < seuil_non_recuperee:
        return "NON_RECUPEREE"

    if donnees_qualite["nombre_manquants"] > 0:
        return "PARTIELLE"

    if type_service == "retrait_drive":
        return "RETIREE"

    return "LIVREE"


def generer_date_heure_remise(
    rng: np.random.Generator,
    config: dict[str, Any],
    statut: str,
    fin_preparation: datetime,
    debut_creneau: datetime,
    fin_creneau: datetime,
    indice_efficacite: float,
) -> datetime | None:
    """
    Génère la date et l'heure de remise effective d'une commande.

    La ponctualité dépend du taux de ponctualité configuré et de
    l'indice d'efficacité du magasin. Une commande annulée ou non
    récupérée ne possède pas de date de remise.

    Args:
        rng:
            Générateur aléatoire NumPy.
        config:
            Configuration complète de génération.
        statut:
            Statut final de la commande.
        fin_preparation:
            Date et heure de fin de préparation.
        debut_creneau:
            Début du créneau promis.
        fin_creneau:
            Fin du créneau promis.
        indice_efficacite:
            Indice d'efficacité du magasin.

    Returns:
        datetime | None:
            Date et heure de remise, ou `None` si aucune remise
            n'a effectivement eu lieu.
    """
    if statut in {"ANNULEE", "NON_RECUPEREE"}:
        return None

    ponctualite_config = config["ponctualite"]
    taux_a_heure = ponctualite_config["taux_base_a_heure"]

    taux_a_heure = min(max(taux_a_heure * indice_efficacite, 0.50), 0.99)
    est_a_heure = (
        fin_preparation <= fin_creneau and rng.random() < taux_a_heure
    )

    if est_a_heure:
        debut_possible = max(debut_creneau, fin_preparation)
        secondes_disponibles = max(
            int((fin_creneau - debut_possible).total_seconds()), 0
        )

        return debut_possible + timedelta(
            seconds=int(rng.integers(0, secondes_disponibles + 1))
        )

    retard_moyen = ponctualite_config["retard_moyen_minutes"]
    retard_maximum = ponctualite_config["retard_maximum_minutes"]

    retard = min(rng.exponential(retard_moyen), retard_maximum)
    remise_retardee = fin_creneau + timedelta(minutes=float(retard))

    return max(fin_preparation, remise_retardee)


def generer_commandes(
    rng: np.random.Generator, config: dict[str, Any], magasins: pd.DataFrame
) -> pd.DataFrame:
    """
    Génère l'ensemble des commandes synthétiques.

    La fonction orchestre pour chaque commande la sélection du magasin,
    la date, le type de service, le créneau, le panier, la préparation,
    la qualité, le statut et la remise effective.

    Args:
        rng:
            Générateur aléatoire NumPy partagé par la génération.
        config:
            Configuration complète de génération.
        magasins:
            Référentiel des magasins générés.

    Returns:
        pd.DataFrame:
            DataFrame contenant toutes les commandes synthétiques.
    """
    nombre_commande = config["volumetrie"]["objectif_commandes"]

    lignes = []
    for numero in range(1, nombre_commande + 1):
        magasin = choisir_magasin(rng, magasins)
        id_magasin = magasin["id_magasin"]
        efficacite_magasin = magasin["indice_efficacite"]

        date_heure_commande = generer_date_heure_commande(rng, config)
        type_service = generer_type_service(rng, config, magasin)

        creneau = generer_creneaux(rng, config, date_heure_commande)
        debut_creneau = creneau[0]
        fin_creneau = creneau[1]

        panier = generer_articles_panier(rng, config)
        montant_panier = generer_montant_panier(rng, config, panier)

        preparation = generer_preparation(
            rng, config, magasin, date_heure_commande, debut_creneau, panier
        )
        debut_preparation = preparation["debut_preparation"]
        fin_preparation = preparation["fin_preparation"]

        qualite_preparation = generer_qualite_preparation(rng, config, panier)
        statut_commande = generer_statut_commande(
            rng, config, type_service, qualite_preparation
        )

        date_heure_remise = generer_date_heure_remise(
            rng,
            config,
            statut_commande,
            fin_preparation,
            debut_creneau,
            fin_creneau,
            efficacite_magasin,
        )

        ligne = {
            "id_commande": f"CMD{numero:06d}",
            "id_magasin": id_magasin,
            "date_heure_commande": date_heure_commande,
            "type_service": type_service,
            "debut_creneau_promis": debut_creneau,
            "fin_creneau_promis": fin_creneau,
            "debut_preparation": debut_preparation,
            "fin_preparation": fin_preparation,
            "remise_commande": date_heure_remise,
            "statut_commande": statut_commande,
            "nombre_articles_commandes": panier,
            "nombre_articles_prepares": qualite_preparation["nombre_prepares"],
            "nombre_articles_manquants": qualite_preparation[
                "nombre_manquants"
            ],
            "nombre_articles_substitues": qualite_preparation[
                "nombre_substitues"
            ],
            "montant_commande": montant_panier,
        }

        lignes.append(ligne)
    return pd.DataFrame(lignes)


def df_to_csv(
    config: dict[str, Any], dataframe: pd.DataFrame, chemin_csv: Path | str
) -> None:
    """
    Exporte un DataFrame dans un fichier CSV.

    Le séparateur, l'encodage et le format des dates sont issus
    de la configuration.

    Le répertoire de destination est créé automatiquement
    s'il n'existe pas.

    Args:
        config:
            Configuration complète de génération.
        dataframe:
            DataFrame à exporter.
        chemin_csv:
            Chemin du fichier CSV de destination.
    """
    config_exports = config["exports"]
    separateur = config_exports["separateur_csv"]
    encodage = config_exports["encodage"]
    format_datetime = config_exports["format_datetime"]

    chemin_csv = Path(chemin_csv)
    chemin_csv.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(
        chemin_csv,
        sep=separateur,
        index=False,
        encoding=encodage,
        date_format=format_datetime,
    )
