CREATE SCHEMA IF NOT EXISTS clean;

CREATE TABLE IF NOT EXISTS clean.magasins (
    id_magasin VARCHAR(20) PRIMARY KEY,
    nom_magasin VARCHAR(100) NOT NULL,
    region VARCHAR(100),
    zone_geographique VARCHAR(20),
    type_service VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS clean.commandes (
    id_commande VARCHAR(20) PRIMARY KEY,
    id_magasin VARCHAR(20) NOT NULL,
    date_heure_commande TIMESTAMP NOT NULL,
    type_service VARCHAR(20),
    debut_creneau_promis TIMESTAMP,
    fin_creneau_promis TIMESTAMP,
    debut_preparation TIMESTAMP,
    fin_preparation TIMESTAMP,
    remise_commande TIMESTAMP,
    nombre_articles_commandes INTEGER,
    nombre_articles_manquants INTEGER,
    nombre_articles_substitues INTEGER,
    montant_commande NUMERIC(12, 2),
    statut_commande VARCHAR(30),

    CONSTRAINT fk_commandes_magasin
        FOREIGN KEY (id_magasin)
        REFERENCES clean.magasins(id_magasin)
);