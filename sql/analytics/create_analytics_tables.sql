CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.dim_date (
    date_jour DATE PRIMARY KEY,
    annee INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    numero_mois INTEGER NOT NULL,
    nom_mois VARCHAR(20) NOT NULL,
    annee_mois VARCHAR(7) NOT NULL,
    numero_semaine INTEGER NOT NULL,
    numero_jour_semaine INTEGER NOT NULL,
    nom_jour VARCHAR(20) NOT NULL,
    est_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics.dim_magasins (
    id_magasin VARCHAR(20) PRIMARY KEY,
    nom_magasin VARCHAR(100) NOT NULL,
    region VARCHAR(100),
    zone_geographique VARCHAR(20),
    type_service VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS analytics.fact_commandes (
    id_commande VARCHAR(20) PRIMARY KEY,
    id_magasin VARCHAR(20) NOT NULL,
    date_heure_commande TIMESTAMP NOT NULL,
    date_commande DATE,
    type_service VARCHAR(20),
    duree_preparation NUMERIC(10, 2),
    commande_a_l_heure BOOLEAN,
    duree_retard NUMERIC(10, 2),
    nombre_articles_commandes INTEGER,
    nombre_articles_manquants INTEGER,
    nombre_articles_substitues INTEGER,
    montant_commande NUMERIC(12, 2)
);