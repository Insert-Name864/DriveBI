"""
Orchestration du pipeline de génération de données et de création de la base de données
"""

from pathlib import Path

import numpy as np

from dataGenerator import (
    charger_configuration,
    generer_magasins,
    generer_commandes,
    df_to_csv,
)
from tableGenerator import (
    connexion_bdd,
    creer_bdd,
    creer_schema,
    creer_table_depuis_csv,
    importer_csv_dans_table,
    executer_script_sql,
)


def main() -> None:
    config = charger_configuration()

    # Génération des fichiers csv à partir du générateur
    chemin_projet = Path(__file__).resolve().parent.parent
    chemin_data = chemin_projet / "data" / "raw"
    chemin_data.mkdir(parents=True, exist_ok=True)

    chemin_magasins = chemin_data / "magasins_raw.csv"
    chemin_commandes = chemin_data / "commandes_raw.csv"
    fichiers_attendus = [chemin_magasins, chemin_commandes]

    fichiers_manquants = [
        fichier for fichier in fichiers_attendus if not fichier.is_file()
    ]
    if fichiers_manquants:
        rng = np.random.default_rng(config["seed"])

        magasins = generer_magasins(rng, config)
        commandes = generer_commandes(rng, config, magasins)

        magasins_export = magasins.drop(columns=["indice_efficacite"])
        df_to_csv(config, magasins_export, chemin_magasins)
        df_to_csv(config, commandes, chemin_commandes)

    # Initialisation de la base PostregreSQL
    nom_bdd = "DriveBI_database"
    connexion_postgres = connexion_bdd("postgres")
    try:
        creer_bdd(connexion_postgres, nom_bdd)
    finally:
        connexion_postgres.close()

    connexion_drive_bi = connexion_bdd(nom_bdd)
    try:
        # Création du schema staging de la base
        schema_name = "staging"
        try:
            schema_drive_bi = creer_schema(connexion_drive_bi, schema_name)
            connexion_drive_bi.commit()
        except Exception:
            connexion_drive_bi.rollback()
            raise

        # Création des tables de la base
        tables_bdd = {
            "magasins_raw": chemin_magasins,
            "commandes_raw": chemin_commandes,
        }
        try:
            for table, chemin_csv in tables_bdd.items():
                colonnes_tables = creer_table_depuis_csv(
                    config, connexion_drive_bi, schema_name, table, chemin_csv
                )
                lignes_tables = importer_csv_dans_table(
                    config, connexion_drive_bi, schema_name, table, chemin_csv
                )
            connexion_drive_bi.commit()
        except Exception:
            connexion_drive_bi.rollback()
            raise

        # Création du schema clean de la base
        chemin_script_sql = chemin_projet / "sql"
        chemin_create_clean_tables = (
            chemin_script_sql / "clean" / "create_clean_tables.sql"
        )
        chemin_load_clean_tables = (
            chemin_script_sql / "clean" / "load_clean_tables.sql"
        )
        try:
            executer_script_sql(connexion_drive_bi, chemin_create_clean_tables)
            executer_script_sql(connexion_drive_bi, chemin_load_clean_tables)
            connexion_drive_bi.commit()
        except Exception:
            connexion_drive_bi.rollback()
            raise

        # Création du schema analytics de la base
        parametres_analytics = {
            "date_debut": config["periode"]["date_debut"],
            "date_fin": config["periode"]["date_fin"],
        }
        chemin_create_analytics_tables = (
            chemin_script_sql / "analytics" / "create_analytics_tables.sql"
        )
        chemin_load_analytics_tables = (
            chemin_script_sql / "analytics" / "load_analytics_tables.sql"
        )
        try:
            executer_script_sql(
                connexion_drive_bi, chemin_create_analytics_tables
            )
            executer_script_sql(
                connexion_drive_bi,
                chemin_load_analytics_tables,
                parametres_analytics,
            )
            connexion_drive_bi.commit()
        except Exception:
            connexion_drive_bi.rollback()
            raise
    finally:
        connexion_drive_bi.close()


if __name__ == "__main__":
    main()
