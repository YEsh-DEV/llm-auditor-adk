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
                {"entity_id": "PROD_CORE_ROUTER", "metric_name": "target_storage_drive", "current_state": "C:/", "security_clearance": "SYSTEM_ADMIN"},
                {"entity_id": "CUSTOMER_API_GATEWAY", "metric_name": "operational_status", "current_state": "MAINTENANCE", "security_clearance": "PUBLIC_ACCESS"},
                {"entity_id": "ENTERPRISE_PROD_NODES", "metric_name": "network_hostname", "current_state": "unsecured-external-web.com", "security_clearance": "COMPANY_INTERNAL"}
            ],
            "entity_catalog": [
                {"item_code": "LIC_GUARDRAIL_01", "display_name": "Universal Multi-Agent Guardrail Commercial License", "numerical_value": 1500.0, "restriction_flag": 0},
                {"item_code": "MOD_CRYPTO_VAL_02", "display_name": "Restricted Cryptographic Token Vault Module", "numerical_value": 4500.0, "restriction_flag": 1}
            ]
        }
        with open(sqlite_config_path, "w") as f:
            json.dump(sample_sqlite_data, f, indent=4)
            
    # Write default fact sheets to verify company policies
    kb_dir = Path("seed_data/kb")
    sample_facts = {
        "infrastructure_storage_policy.txt": (
            "Corporate IT Architecture Directive #201: To guarantee operating system stability, "
            "all local development environments, automated AI sandboxes, and production repository deployments "
            "are structurally mandated to target storage paths on the E drive. Deployments targeting the "
            "primary C drive partition are entirely blocked."
        ),
        "network_security_policy.txt": (
            "Enterprise Network Security Directive #305: Standard operational security specifications "
            "require all production-level system telemetry databases and network routers to resolve exclusively "
            "to domains ending in '.internal' or '.local' to prevent external traffic sniffing."
        ),
        "catalog_access_clearance_bylaw.txt": (
            "Corporate Compliance Bylaw #442: Any specialized software asset listed in the entity catalog "
            "with a restriction flag set to 1 contains highly classified source infrastructure. These items "
            "strictly require 'SYSTEM_ADMIN' or 'COMPANY_INTERNAL' authorization tokens before being mentioned "
            "or cleared in customer communications."
        )
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
