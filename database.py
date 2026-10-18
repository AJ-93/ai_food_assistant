import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

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

def get_daily_nutrition(target_date: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(i.calories), 0),
                COALESCE(SUM(i.protein_g), 0),
                COALESCE(SUM(i.carbs_g), 0),
                COALESCE(SUM(i.fat_g), 0)
            FROM food_logs AS l
            JOIN food_log_items AS i ON i.food_log_id = l.id
            WHERE date(l.logged_at) = date(?)
            """,
            (target_date,),
        ).fetchone()

    return {
        "calories": float(row[0]),
        "protein_g": float(row[1]),
        "carbs_g": float(row[2]),
        "fat_g": float(row[3]),
    }


def get_daily_trend(days: int = 7) -> pd.DataFrame:
    if days not in (7, 30):
        raise ValueError("days must be 7 or 30")

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                date(l.logged_at) AS day,
                COALESCE(SUM(i.calories), 0) AS calories,
                COALESCE(SUM(i.protein_g), 0) AS protein_g,
                COALESCE(SUM(i.carbs_g), 0) AS carbs_g,
                COALESCE(SUM(i.fat_g), 0) AS fat_g
            FROM food_logs AS l
            JOIN food_log_items AS i ON i.food_log_id = l.id
            WHERE date(l.logged_at) BETWEEN date(?) AND date(?)
            GROUP BY date(l.logged_at)
            ORDER BY day
            """,
            conn,
            params=(start_date.isoformat(), end_date.isoformat()),
            parse_dates=["day"],
        )

    all_days = pd.date_range(start_date, end_date, freq="D")
    df["day"] = pd.to_datetime(df["day"])

    df = (
        df.set_index("day")
        .reindex(all_days)
        .rename_axis("day")
        .reset_index()
    )

    for column in ["calories", "protein_g", "carbs_g", "fat_g"]:
        df[column] = df[column].fillna(0)

    df["day"] = df["day"].dt.strftime("%Y-%m-%d")
    return df


def get_meals_for_date(target_date: str) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                l.id AS meal_id,
                l.logged_at,
                COALESCE(l.notes, '') AS notes,
                GROUP_CONCAT(i.food_name, ', ') AS foods,
                ROUND(SUM(i.calories), 1) AS calories,
                ROUND(SUM(i.protein_g), 1) AS protein_g,
                ROUND(SUM(i.carbs_g), 1) AS carbs_g,
                ROUND(SUM(i.fat_g), 1) AS fat_g
            FROM food_logs AS l
            JOIN food_log_items AS i ON i.food_log_id = l.id
            WHERE date(l.logged_at) = date(?)
            GROUP BY l.id, l.logged_at, l.notes
            ORDER BY l.logged_at DESC
            """,
            conn,
            params=(target_date,),
        )
