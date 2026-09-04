"""
Création de la structure de la base de données
"""

import os
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as PGConnection


def connexion_bdd(nom_bdd: str) -> PGConnection:
    """
    Ouvre une connexion à une base PostgreSQL locale.

    Les paramètres de connexion sont définis dans la fonction,
    à l'exception du mot de passe récupéré depuis la variable
    d'environnement `POSTGRES_PASSWORD`.

    Args:
        nom_bdd:
            Nom de la base PostgreSQL à laquelle se connecter.

    Returns:
        PGConnection:
            Connexion PostgreSQL ouverte.

    Raises:
        KeyError:
            Si la variable d'environnement `POSTGRES_PASSWORD`
            n'est pas définie.
        psycopg2.Error:
            Si la connexion à PostgreSQL échoue.
    """
    connexion = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname=nom_bdd,
        user="postgres",
        password=os.environ["POSTGRES_PASSWORD"],
    )
    return connexion


def creer_bdd(connexion: PGConnection, nom_bdd: str) -> bool:
    """
    Crée une base PostgreSQL si elle n'existe pas encore.

    La connexion fournie doit pointer vers une autre base,
    généralement `postgres`. L'autocommit est activé car PostgreSQL
    interdit la création d'une base dans une transaction classique.

    La fonction ne ferme pas la connexion reçue en argument.

    Args:
        connexion:
            Connexion PostgreSQL utilisée pour créer la base.
        nom_bdd:
            Nom de la base à créer.

    Returns:
        bool:
            `True` si la base a été créée, `False` si elle existait déjà.
    """
    curseur = None
    try:
        connexion.autocommit = True
        curseur = connexion.cursor()
        curseur.execute(
            """
            SELECT 1
            FROM pg_database
            WHERE datname = %s;
            """,
            (nom_bdd,),
        )

        if curseur.fetchone() is not None:
            print(f"La base de données {nom_bdd!r} existe déjà.")
            return False

        requete = sql.SQL("CREATE DATABASE {};").format(
            sql.Identifier(nom_bdd)
        )
        curseur.execute(requete)

        print(f"La base de données {nom_bdd!r} a été créée.")
        return True

    finally:
        if curseur is not None:
            curseur.close()


def supprimer_bdd(connexion: PGConnection, nom_bdd: str) -> None:
    """
    Supprime une base PostgreSQL si elle existe.

    L'autocommit est activé car la suppression d'une base ne peut pas
    être exécutée dans une transaction classique.

    La connexion doit pointer vers une base différente de celle
    à supprimer et n'est pas fermée par cette fonction.

    Args:
        connexion:
            Connexion PostgreSQL utilisée pour effectuer la suppression.
        nom_bdd:
            Nom de la base à supprimer.
    """
    connexion.autocommit = True
    with connexion.cursor() as curseur:
        requete = sql.SQL("DROP DATABASE IF EXISTS {};").format(
            sql.Identifier(nom_bdd)
        )

        curseur.execute(requete)


def creer_schema(connexion: PGConnection, nom_schema: str) -> bool:
    """
    Crée un schéma PostgreSQL s'il n'existe pas encore.

    La transaction n'est pas validée dans cette fonction :
    le commit ou le rollback reste sous la responsabilité
    de l'orchestrateur appelant.

    Args:
        connexion:
            Connexion PostgreSQL active.
        nom_schema:
            Nom du schéma à créer.

    Returns:
        bool:
            `True` si le schéma a été créé,
            `False` s'il existait déjà.

    Raises:
        TypeError:
            Si le nom du schéma n'est pas une chaîne.
        ValueError:
            Si le nom du schéma est vide.
    """
    if not isinstance(nom_schema, str):
        raise TypeError("nom_schema doit être une chaîne de caractères.")

    nom_schema = nom_schema.strip()
    if not nom_schema:
        raise ValueError("Le nom du schéma ne peut pas être vide.")

    with connexion.cursor() as curseur:
        curseur.execute(
            """
            SELECT 1
            FROM information_schema.schemata
            WHERE schema_name = %s;
            """,
            (nom_schema,),
        )

        if curseur.fetchone() is not None:
            print(f"Le schéma {nom_schema!r} existe déjà.")
            return False

        requete = sql.SQL("CREATE SCHEMA {};").format(
            sql.Identifier(nom_schema)
        )

        curseur.execute(requete)

    print(f"Le schéma {nom_schema!r} a été créé.")
    return True


def creer_table_depuis_csv(
    config: dict[str, Any],
    connexion: PGConnection,
    nom_schema: str,
    nom_table: str,
    chemin_csv: Path | str,
) -> list[str]:
    """
    Recrée une table PostgreSQL à partir de l'en-tête d'un fichier CSV.

    La table existante est supprimée puis recréée.
    Toutes les colonnes du fichier sont créées en type PostgreSQL TEXT,
    conformément au rôle du schéma staging.

    Aucun commit ou rollback n'est exécuté dans cette fonction.

    Args:
        config:
            Configuration du projet, notamment le séparateur
            et l'encodage du CSV.
        connexion:
            Connexion PostgreSQL active.
        nom_schema:
            Nom du schéma contenant la table.
        nom_table:
            Nom de la table à créer.
        chemin_csv:
            Chemin du fichier CSV servant à déterminer les colonnes.

    Returns:
        list[str]:
            Liste des noms de colonnes créées.

    Raises:
        FileNotFoundError:
            Si le fichier CSV est introuvable.
        ValueError:
            Si l'en-tête est vide ou contient des noms de colonnes
            invalides ou en doublon.
    """

    chemin_csv = Path(chemin_csv)
    if not chemin_csv.is_file():
        raise FileNotFoundError(f"Fichier CSV introuvable : {chemin_csv}")

    separateur = config["exports"]["separateur_csv"]
    encodage = config["exports"]["encodage"]
    colonnes = pd.read_csv(
        chemin_csv,
        sep=separateur,
        encoding=encodage,
        nrows=0,
    ).columns.tolist()

    colonnes = [str(colonne).strip() for colonne in colonnes]

    if not colonnes:
        raise ValueError("Le fichier ne contient aucune colonne.")

    if any(not colonne for colonne in colonnes):
        raise ValueError("Une colonne du CSV possède un nom vide.")

    if len(colonnes) != len(set(colonnes)):
        raise ValueError("Le CSV contient des noms de colonnes en doublon.")

    requete_drop = sql.SQL("""
        DROP TABLE IF EXISTS {}.{};
        """).format(sql.Identifier(nom_schema), sql.Identifier(nom_table))

    definitions = sql.SQL(", ").join(
        sql.SQL("{} TEXT").format(sql.Identifier(colonne))
        for colonne in colonnes
    )
    requete_create = sql.SQL("""
        CREATE TABLE {}.{} (
            {}
        );
        """).format(
        sql.Identifier(nom_schema),
        sql.Identifier(nom_table),
        definitions,
    )

    with connexion.cursor() as curseur:
        curseur.execute(requete_drop)
        curseur.execute(requete_create)

    return colonnes


def importer_csv_dans_table(
    config: dict[str, Any],
    connexion: PGConnection,
    nom_schema: str,
    nom_table: str,
    chemin_csv: Path | str,
) -> int:
    """
    Importe les données d'un fichier CSV dans une table PostgreSQL.

    L'import utilise la commande PostgreSQL COPY.
    La première ligne du fichier est considérée comme l'en-tête.

    Aucun commit ou rollback n'est effectué dans cette fonction.

    Args:
        config:
            Configuration du projet, notamment le séparateur
            et l'encodage du CSV.
        connexion:
            Connexion PostgreSQL active.
        nom_schema:
            Nom du schéma cible.
        nom_table:
            Nom de la table cible.
        chemin_csv:
            Chemin du fichier CSV à importer.

    Returns:
        int:
            Nombre de lignes de données contenues dans le CSV,
            hors ligne d'en-tête.

    Raises:
        FileNotFoundError:
            Si le fichier CSV est introuvable.
    """
    chemin_csv = Path(chemin_csv)
    if not chemin_csv.is_file():
        raise FileNotFoundError(f"Fichier CSV introuvable : {chemin_csv}")

    separateur = config["exports"]["separateur_csv"]
    encodage = config["exports"]["encodage"]
    requete_copy = sql.SQL("""
        COPY {}.{}
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            DELIMITER {},
            ENCODING 'UTF8'
        );
        """).format(
        sql.Identifier(nom_schema),
        sql.Identifier(nom_table),
        sql.Literal(separateur),
    )

    with chemin_csv.open(
        mode="r",
        encoding=encodage,
        newline="",
    ) as fichier:
        with connexion.cursor() as curseur:
            curseur.copy_expert(
                requete_copy.as_string(connexion),
                fichier,
            )

    # Nombre de lignes de données, sans compter l'en-tête.
    with chemin_csv.open(
        mode="r",
        encoding=encodage,
    ) as fichier:
        nombre_lignes = max(
            sum(1 for _ in fichier) - 1,
            0,
        )

    return nombre_lignes


def executer_script_sql(
    connexion: PGConnection,
    chemin_script: Path,
    parametres: dict[str, Any] | None = None,
) -> None:
    """
    Lit et exécute un script SQL sur une connexion PostgreSQL.

    Des paramètres nommés peuvent être transmis au script.
    La fonction ne réalise aucun commit ni rollback afin de laisser
    la gestion de la transaction à l'orchestrateur appelant.

    Args:
        connexion:
            Connexion PostgreSQL active.
        chemin_script:
            Chemin du fichier SQL à exécuter.
        parametres:
            Paramètres optionnels transmis à la requête SQL.
    """
    script_sql = chemin_script.read_text(encoding="utf-8")

    with connexion.cursor() as curseur:
        curseur.execute(script_sql, parametres)
