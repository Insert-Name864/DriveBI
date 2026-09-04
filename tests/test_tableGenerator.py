"""
Tests des fonctions de création de la base de données
"""

from pathlib import Path
import pytest

from tableGenerator import connexion_bdd, creer_bdd, creer_table_depuis_csv, creer_schema, importer_csv_dans_table, executer_script_sql
from dataGenerator import charger_configuration

@pytest.fixture 
def config():
    return charger_configuration()

@pytest.fixture 
def database_name():
    return "temp_database"

@pytest.fixture 
def schema_staging():
    return "staging"

@pytest.fixture 
def nom_tables():
    return ["magasins_raw", "commandes_raw"]

@pytest.fixture 
def path_donnees_brutes():
    racine_projet = Path(__file__).resolve().parent.parent
    return racine_projet / "data" / "raw" 

@pytest.fixture 
def donnees_brutes():
    return ["magasins_raw.csv", "commandes_raw.csv"]

@pytest.fixture 
def path_script_clean_tables():
    racine_projet = Path(__file__).resolve().parent.parent
    return racine_projet / "sql" / "clean"    

@pytest.fixture 
def path_script_analytics_tables():
    racine_projet = Path(__file__).resolve().parent.parent
    return racine_projet / "sql" / "analytics"  


def test_creer_bdd(database_name):
    connexion = connexion_bdd("postgres")
    try:
        temp_database = creer_bdd(connexion, database_name)    
        
    finally:
        assert temp_database is True
    

def test_creer_schema(database_name, schema_staging):
    connexion = connexion_bdd(database_name)
    try:
        temp_schema = creer_schema(connexion, schema_staging)
    finally:
        assert temp_schema is True


def test_table_from_csv(config, database_name, schema_staging, nom_tables, path_donnees_brutes, donnees_brutes):
    connexion = connexion_bdd(database_name)
    
    for index in range(0, len(nom_tables), 1):
        donnees_csv = path_donnees_brutes / donnees_brutes[index]
        colonnes = creer_table_depuis_csv(config, connexion, schema_staging, nom_tables[index], donnees_csv)    
        assert isinstance(colonnes, list)
    
    
def test_importer_csv_dans_table(config, database_name, schema_staging, nom_tables, path_donnees_brutes, donnees_brutes):
    connexion = connexion_bdd(database_name)
    
    for index in range(0, len(nom_tables), 1):
        donnees_csv = path_donnees_brutes / donnees_brutes[index]
        nb_lignes = importer_csv_dans_table(config, connexion,  schema_staging, nom_tables[index], donnees_csv)
        assert isinstance(nb_lignes, int)
    
    
def test_script_clean_sql(database_name, path_script_clean_tables):
    connexion = connexion_bdd(database_name)
    chemin_create_clean_tables = path_script_clean_tables / "create_clean_tables.sql"
    chemin_load_clean_tables = path_script_clean_tables / "load_clean_tables.sql"
    
    try:
        executer_script_sql(connexion, chemin_create_clean_tables)
        executer_script_sql(connexion, chemin_load_clean_tables)
        connexion.commit()
        
    except Exception :
        connexion.rollback()
        raise
        
    finally:
        connexion.close()
        
        
def test_script_analytics_sql(config, database_name, path_script_analytics_tables):
    connexion = connexion_bdd(database_name)
    parametres_analytics = {
        "date_debut": config["periode"]["date_debut"],
        "date_fin": config["periode"]["date_fin"],
        }
    
    chemin_create_clean_tables = path_script_analytics_tables / "create_analytics_tables.sql"
    chemin_load_clean_tables = path_script_analytics_tables / "load_analytics_tables.sql"
    
    try:
        executer_script_sql(connexion, chemin_create_clean_tables)
        executer_script_sql(connexion, chemin_load_clean_tables, parametres_analytics)
        connexion.commit()
        
    except Exception :
        connexion.rollback()
        raise
        
    finally:
        connexion.close()    