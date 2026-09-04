TRUNCATE TABLE 
    clean.magasins,
    clean.commandes;

INSERT INTO clean.magasins (
    id_magasin,
    nom_magasin,
    region,
    zone_geographique,
    type_service
)
SELECT
    TRIM(id_magasin),
    TRIM(nom_magasin),
    UPPER(TRIM(region)),
    TRIM(zone_geographique),
    UPPER(TRIM(type_service))
FROM staging.magasins_raw;

INSERT INTO clean.commandes (
    id_commande,
    id_magasin,
    date_heure_commande,
    type_service,
    debut_creneau_promis,
    fin_creneau_promis,
    debut_preparation,
    fin_preparation,
    remise_commande,
    nombre_articles_commandes,
    nombre_articles_manquants,
    nombre_articles_substitues,
    montant_commande,
    statut_commande 
)
SELECT
    TRIM(id_commande),
    TRIM(id_magasin),
    date_heure_commande::TIMESTAMP,
    UPPER(TRIM(type_service)),
    debut_creneau_promis::TIMESTAMP,
    fin_creneau_promis::TIMESTAMP,
    debut_preparation::TIMESTAMP,
    fin_preparation::TIMESTAMP,
    remise_commande::TIMESTAMP,
    nombre_articles_commandes::INTEGER,
    nombre_articles_manquants::INTEGER,
    nombre_articles_substitues::INTEGER,
    montant_commande::NUMERIC(12, 2),
    UPPER(TRIM(statut_commande))
FROM staging.commandes_raw;