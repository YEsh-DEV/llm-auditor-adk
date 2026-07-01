import os
import json
import sqlite3
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

def ensure_seed_directories():
    """Create directory structure and write sample files if empty."""
    # Create the config and knowledge base folders
    Path("seed_data/kb").mkdir(parents=True, exist_ok=True)
    
    # Write a default JSON template for the SQLite tables
    sqlite_config_path = Path("seed_data/sqlite_data.json")
    if not sqlite_config_path.exists():
        sample_sqlite_data = {
            "system_telemetry": [
                {"entity_id": "SERVER_01", "metric_name": "drive_path", "current_state": "C:/", "security_clearance": "ADMIN"},
                {"entity_id": "APP_GATEWAY", "metric_name": "status", "current_state": "MAINTENANCE", "security_clearance": "PUBLIC"},
                {"entity_id": "DATABASE_CLUSTER", "metric_name": "replication_lag", "current_state": "0ms", "security_clearance": "INTERNAL"},
                {"entity_id": "PROD_SERVER", "metric_name": "hostname", "current_state": "prod-srv-01.internal", "security_clearance": "ADMIN"}
            ],
            "entity_catalog": [
                {"item_code": "ITEM_001", "display_name": "Universal Multi-Agent Guardrail License", "numerical_value": 1500.0, "restriction_flag": 0},
                {"item_code": "ITEM_002", "display_name": "Advanced compliance scanning module", "numerical_value": 450.0, "restriction_flag": 1},
                {"item_code": "ITEM_003", "display_name": "Standard fact check lookup credit pack", "numerical_value": 10.0, "restriction_flag": 0}
            ]
        }
        with open(sqlite_config_path, "w") as f:
            json.dump(sample_sqlite_data, f, indent=4)
            
    # Write default fact sheets to verify Android and physics offline
    kb_dir = Path("seed_data/kb")
    sample_facts = {
        "blueberries_fact.txt": "Blueberries are blue due to a waxy coating of silica or wax on their skin that scatters blue light. The pigments on their skin are actually dark red/anthocyanin.",
        "android_fact.txt": "Ice Cream Sandwich is the official code name for the 4.0 version of the Android mobile operating system, released by Google.",
        "sky_fact.txt": "Rayleigh scattering causes the sky to appear blue because molecules in the air scatter blue light from the Sun more than they scatter other wavelengths.",
        "mars_fact.txt": "Earth is closer to the Sun than Mars. Earth's average distance is about 150 million kilometers, whereas Mars average distance is about 228 million kilometers.",
        "telemetry_rule.txt": "Standard operational templating requires all system telemetry databases to run only on hostnames ending in '.internal' or '.local'.",
        "catalog_rule.txt": "Any item listed in the entity_catalog with restriction_flag set to 1 requires security clearance 'ADMIN' or 'INTERNAL' to access."
    }
    for filename, text in sample_facts.items():
        fact_path = kb_dir / filename
        if not fact_path.exists():
            with open(fact_path, "w") as f:
                f.write(text)


def seed_sqlite():
    db_path = "company_operations.db"
    config_path = "seed_data/sqlite_data.json"
    
    print(f"Initializing SQLite operational DB at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Setup abstract generic schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_telemetry (
            entity_id TEXT PRIMARY KEY,
            metric_name TEXT,
            current_state TEXT,
            security_clearance TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_catalog (
            item_code TEXT PRIMARY KEY,
            display_name TEXT,
            numerical_value REAL,
            restriction_flag INTEGER
        )
    """)

    cursor.execute("DELETE FROM system_telemetry")
    cursor.execute("DELETE FROM entity_catalog")

    # Load from dynamic config json
    with open(config_path, "r") as f:
        data = json.load(f)

    telemetry_rows = [
        (row["entity_id"], row["metric_name"], row["current_state"], row["security_clearance"])
        for row in data.get("system_telemetry", [])
    ]
    cursor.executemany("INSERT INTO system_telemetry VALUES (?, ?, ?, ?)", telemetry_rows)

    catalog_rows = [
        (row["item_code"], row["display_name"], row["numerical_value"], row["restriction_flag"])
        for row in data.get("entity_catalog", [])
    ]
    cursor.executemany("INSERT INTO entity_catalog VALUES (?, ?, ?, ?)", catalog_rows)

    conn.commit()
    conn.close()
    print("SQLite seeded successfully!")


def seed_qdrant():
    storage_path = "./qdrant_storage"
    collection_name = "compliance_facts"
    kb_dir = Path("seed_data/kb")
    
    print(f"Initializing local Qdrant collection '{collection_name}' at: {storage_path}")
    client = QdrantClient(path=storage_path)

    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    points = []
    point_id = 1
    
    # Dynamically scan the kb folder and compute vectors for each text file
    for txt_file in kb_dir.glob("*.txt"):
        with open(txt_file, "r", encoding="utf-8") as f:
            fact_text = f.read().strip()
            
        if not fact_text:
            continue
            
        print(f"Embedding and indexing fact: {txt_file.name}")
        vector = model.encode(fact_text).tolist()
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={"text": fact_text, "source": txt_file.name}
            )
        )
        point_id += 1

    if points:
        client.upsert(collection_name=collection_name, points=points)
        print(f"Qdrant collection seeded with {len(points)} facts successfully!")
    else:
        print("No facts found to seed in Qdrant.")


if __name__ == "__main__":
    ensure_seed_directories()
    seed_sqlite()
    seed_qdrant()
