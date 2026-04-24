import sqlite3
import json
from pathlib import Path

DB_PATH = Path("ideahunter.db")

def populate_mock_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Insert a high-scoring idea
    idea_data = (
        "AI Content Guard",
        "A tool that detects AI-generated content in student essays with 99% accuracy.",
        "Students using ChatGPT to cheat on academic assignments.",
        "reddit",
        json.dumps(["AI detection", "academic integrity", "plagiarism checker"]),
        8.5, 90, 30, 85, 75,
        1 # saved
    )
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ideas 
        (name, description, pain_point, source, keywords, score_overall, score_demand, score_competition, score_trend, score_uniqueness, saved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, idea_data)
    idea_id = cursor.lastrowid
    
    # Insert Demand Metrics
    cursor.execute("""
        INSERT INTO demand_metrics (idea_id, search_volume, keyword_difficulty, cpc)
        VALUES (?, ?, ?, ?)
    """, (idea_id, 25000, 65, 4.50))
    
    # Insert GSC Metrics
    cursor.execute("""
        INSERT INTO gsc_metrics (idea_id, impressions, clicks, position, ctr)
        VALUES (?, ?, ?, ?, ?)
    """, (idea_id, 1200, 95, 12.4, 7.9))
    
    conn.commit()
    conn.close()
    print(f"Mock idea inserted with ID: {idea_id}")

if __name__ == "__main__":
    populate_mock_data()
