import os
import sqlite3
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

def seed_sqlite():
    db_path = "company_operations.db"
    print(f"Initializing SQLite operational DB at:{db_path}" )
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    #Create the abstract tables 
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
    telemetry_data = [
        ("SERVER_01", "drive_path", "C:/", "ADMIN"),
        ("APP_GATEWAY", "status", "MAINTENANCE", "PUBLIC"),
        ("DATABASE_CLUSTER", "replication_lag", "0ms", "INTERNAL"),
        ("PROD_SERVER", "hostname", "prod-srv-01.internal", "ADMIN")
    ]
    cursor.executemany("INSERT INTO system_telemetry VALUES (?, ?, ?, ?)", telemetry_data)
    catalog_data = [
        ("ITEM_001", "Universal Multi-Agent Guardrail License", 1500.0, 0),
        ("ITEM_002", "Advanced compliance scanning module", 450.0, 1),
        ("ITEM_003", "Standard fact check lookup credit pack", 10.0, 0)
    ]
    cursor.executemany("INSERT INTO entity_catalog VALUES (?, ?, ?, ?)", catalog_data)
    conn.commit()
    conn.close()
    print("SQLite seeded successfully!")
    
def seed_qudrant():
    storage_path = "./qdrant_storage"
    collection_name = "compliance_facts"
    print(f"Initializing Qdrant at: {storage_path}")
    
    client = QdrantClient(path=storage_path)
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    # Multi-layered truths (Scientific truths + abstract system policies)
    facts = [
        {"id": 1, "text": "Blueberries are blue due to a waxy coating of silica or wax on their skin that scatters blue light. The pigments on their skin are actually dark red/anthocyanin.", "type": "scientific"},
        {"id": 2, "text": "Ice Cream Sandwich is the official code name for the 4.0 version of the Android mobile operating system, released by Google.", "type": "scientific"},
        {"id": 3, "text": "Rayleigh scattering causes the sky to appear blue because molecules in the air scatter blue light from the Sun more than they scatter other wavelengths.", "type": "scientific"},
        {"id": 4, "text": "Earth is closer to the Sun than Mars. Earth's average distance is about 150 million kilometers, whereas Mars average distance is about 228 million kilometers.", "type": "scientific"},
        {"id": 5, "text": "Standard operational templating requires all system telemetry databases to run only on hostnames ending in '.internal' or '.local'.", "type": "compliance"},
        {"id": 6, "text": "Any item listed in the entity_catalog with restriction_flag set to 1 requires security clearance 'ADMIN' or 'INTERNAL' to access.", "type": "compliance"}
    ]
    points = []
    for fact in facts:
        vector = model.encode(fact["text"]).tolist()
        points.append(
            PointStruct(
                id=fact["id"],
                vector=vector,
                payload={"text": fact["text"], "type": fact["type"]}
            )
        )
    client.upsert(collection_name=collection_name, points=points)
    print("Qdrant collection seeded successfully!")
if __name__ == "__main__":
    seed_sqlite()
    seed_qdrant()    
