import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "food_assistant.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def run_ddl():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS food_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT NOT NULL DEFAULT ''
            );
            
            CREATE TABLE IF NOT EXISTS food_log_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_log_id INTEGER NOT NULL,
                food_name TEXT NOT NULL,
                quantity_g REAL NOT NULL,
                calories REAL NOT NULL,
                protein_g REAL NOT NULL,
                carbs_g REAL NOT NULL,
                fat_g REAL NOT NULL,
                FOREIGN KEY (food_log_id)
                    REFERENCES food_logs(id)
            );
        """)

def save_meal_data(foods, notes=""):
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        cursor = conn.execute(
            "INSERT INTO food_logs (notes) VALUES (?)", (notes,),
        )
        log_id = cursor.lastrowid

        conn.executemany(
            """
        INSERT INTO food_log_items (
            food_log_id, food_name, quantity_g,
            calories, protein_g, carbs_g, fat_g
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            [
                (
                    log_id,
                    food.food_name,
                    food.quantity_g,
                    food.calories_g,
                    food.protein_g,
                    food.carbs_g,
                    food.fat_g,
                )
                for food in foods
            ],
        )
        return log_id

def get_meal_data(limit=20):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT
                l.id AS meal_id,
                l.logged_at,
                l.notes,
                SUM(i.calories) AS calories,
                SUM(i.protein_g) AS protein_g,
                SUM(i.carbs_g) AS carbs_g,
                SUM(i.fat_g) AS fat_g
            FROM food_logs l
            JOIN food_log_items i ON i.food_log_id = l.id
            GROUP BY l.id
            ORDER BY l.logged_at DESC, l.id DESC
            LIMIT ?
            """, (limit,),
        ).fetchall()
