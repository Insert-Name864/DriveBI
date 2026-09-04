TRUNCATE TABLE 
    analytics.dim_date,
    analytics.dim_magasins,
    analytics.fact_commandes;

INSERT INTO analytics.dim_date (
    date_jour,
    annee,
    trimestre,
    numero_mois,
    nom_mois,
    annee_mois,
    numero_semaine,
    numero_jour_semaine,
    nom_jour,
    est_weekend
)
SELECT
    date_generee::DATE,

    EXTRACT(
        YEAR FROM date_generee
    )::INTEGER AS annee,

    EXTRACT(
        QUARTER FROM date_generee
    )::INTEGER AS trimestre,

    EXTRACT(
        MONTH FROM date_generee
    )::INTEGER AS numero_mois,

    TO_CHAR(
        date_generee,
        'TMMonth'
    ) AS nom_mois,

    TO_CHAR(
        date_generee,
        'YYYY-MM'
    ) AS annee_mois,

    EXTRACT(
        WEEK FROM date_generee
    )::INTEGER AS numero_semaine,

    EXTRACT(
        ISODOW FROM date_generee
    )::INTEGER AS numero_jour_semaine,

    TO_CHAR(
        date_generee,
        'TMDay'
    ) AS nom_jour,

    EXTRACT(
        ISODOW FROM date_generee
    ) IN (6, 7) AS est_weekend

FROM generate_series(
    %(date_debut)s::DATE,
    %(date_fin)s::DATE,
    INTERVAL '1 day'
) AS calendrier(date_generee);

INSERT INTO analytics.dim_magasins (
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
FROM clean.magasins;

INSERT INTO analytics.fact_commandes (
    id_commande,
    id_magasin,
    date_heure_commande,
    date_commande,
    type_service,
    duree_preparation,
    commande_a_l_heure,
    duree_retard,
    nombre_articles_commandes,
    nombre_articles_manquants,
    nombre_articles_substitues,
    montant_commande
)
SELECT
    TRIM(id_commande),
    TRIM(id_magasin),
    date_heure_commande::TIMESTAMP,
    date_heure_commande::DATE AS date_commande,
    UPPER(TRIM(type_service)),

    EXTRACT(
        EPOCH FROM(
           fin_preparation - debut_preparation 
        )
    )/60.0,

    remise_commande <= fin_creneau_promis,

    GREATEST(
        EXTRACT(
            EPOCH FROM(
                remise_commande - fin_creneau_promis
            )
        )/60.0, 
        0
    ),
    nombre_articles_commandes INTEGER,
    nombre_articles_manquants INTEGER,
    nombre_articles_substitues INTEGER,
    montant_commande::NUMERIC(12, 2)
FROM clean.commandes;