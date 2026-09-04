# -*- coding: utf-8 -*-
"""
Created on Thu May 29 17:55:21 2025

@author: Admin
"""

import logging

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Supprimer les handlers existants
    if logger.hasHandlers():
        logger.handlers.clear()

    # Ajouter un handler console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
