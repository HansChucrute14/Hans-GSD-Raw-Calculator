#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_tempdb.py — Merge tempDB v3.2.0 files into main DB v3.1.1 format.

Reads 5 tempDB files from tempDB/, restructures to main DB format,
writes merged output to data/DB_ingredientes.json.

Usage:
    python tempDB/merge_tempdb.py
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent.parent.resolve()
TEMPDB_DIR = BASE_DIR / "tempDB"
MAIN_DB_PATH = BASE_DIR / "data" / "DB_ingredientes.json"

# tempDB files to merge (ordered by priority)
TEMPDB_FILES = [
    "DB_ingredientes_bovinos_v3.2.0.json",
    "DB_ingredientes_aves_v3.2.0.json",
    "DB_ingredientes_peixes_v3.2.0.json",
    "DB_ingredientes_suinos_v3.2.0.json",
    "DB_ingredientes_fat_sources_v3.2.0.json",
]


def load_tempdb_file(filepath):
    """Load a tempDB file and return (group_name, group_data)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    group_name = list(data.keys())[0]
    return group_name, data[group_name]


def load_main_db():
    """Load the main DB file."""
    with open(MAIN_DB_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_tempdb_into_maindb():
    """Merge all tempDB files into main DB format.

    Strategy: Replace each group in main DB with the corresponding tempDB version.
    tempDB v3.2.0 is newer and has more measured nutrients, so we prefer it.
    """
    main_db = load_main_db()

    temp_groups = {}
    for temp_file in TEMPDB_FILES:
        filepath = TEMPDB_DIR / temp_file
        if not filepath.exists():
            print(f"WARNING: {filepath} not found, skipping")
            continue
        group_name, group_data = load_tempdb_file(filepath)
        temp_groups[group_name] = group_data
        print(f"Loaded {group_name}: {group_data.get('ingredient_count', '?')} ingredients, status={group_data.get('status', '?')}")

    # Replace each group in main DB with tempDB version
    replaced_count = 0
    added_count = 0
    for group_name, group_data in temp_groups.items():
        if group_name in main_db['protein_sources']:
            main_db['protein_sources'][group_name] = group_data
            replaced_count += 1
        else:
            main_db['protein_sources'][group_name] = group_data
            added_count += 1

    print(f"\nReplaced {replaced_count} groups, added {added_count} new groups")

    # Update metadata
    main_db['_db_metadata']['version'] = '3.2.0'
    main_db['_db_metadata']['last_updated'] = datetime.now().strftime('%Y-%m-%d')

    # Update source status based on tempDB validation status
    validated_sources = []
    pending_sources = []
    partial_sources = []

    for group_name, group_data in main_db['protein_sources'].items():
        status = group_data.get('status', 'PARTIAL')
        if status == 'VALIDATED':
            validated_sources.append(group_name)
        elif status == 'PARTIAL':
            partial_sources.append(group_name)
        else:
            pending_sources.append(group_name)

    main_db['_db_metadata']['validated_sources'] = validated_sources
    main_db['_db_metadata']['pending_sources'] = pending_sources
    main_db['_db_metadata']['partial_sources'] = partial_sources

    # Recalculate total ingredients
    total = sum(g.get('ingredient_count', 0) for g in main_db['protein_sources'].values())
    main_db['_db_metadata']['total_ingredients'] = total

    return main_db


def write_merged_db(main_db):
    """Write merged DB to file with proper formatting."""
    with open(MAIN_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(main_db, f, indent=2, ensure_ascii=False)
    print(f"\nMerged DB written to: {MAIN_DB_PATH}")
    print(f"Version: {main_db['_db_metadata']['version']}")
    print(f"Total ingredients: {main_db['_db_metadata']['total_ingredients']}")


if __name__ == '__main__':
    print("=" * 60)
    print("tempDB v3.2.0 -> Main DB v3.1.1 Merge")
    print("=" * 60)
    print()

    merged_db = merge_tempdb_into_maindb()
    write_merged_db(merged_db)

    print()
    print("Merge complete.")
