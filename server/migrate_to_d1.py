"""
One-off migration: copy rows from your local Postgres 'issues' table
into Cloudflare D1.

Run this AFTER creating the D1 database and applying schema.sql, and
BEFORE switching the app over to d1_client. Needs both:
  - DATABASE_URL pointing at your local Postgres (the one pgAdmin uses)
  - CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_D1_DATABASE_ID / CLOUDFLARE_API_TOKEN
    in your .env (same ones the app will use)

Usage:
    python migrate_to_d1.py
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Reuse the same D1 client the app uses, so behavior matches exactly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
from app.d1_client import execute as d1_execute  # noqa: E402


COLUMNS = [
    "id", "line_user_id", "reporter_name", "category", "description",
    "image_url", "latitude", "longitude", "status", "created_at",
    "student_year", "student_class", "student_number", "issue_type",
    "fix_image_url", "resolved_at",
]


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set — point it at your local Postgres first.")
        return

    print("🔄 Connecting to local Postgres...")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    cursor.execute(f"SELECT {', '.join(COLUMNS)} FROM issues ORDER BY id ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    print(f"📦 Found {len(rows)} rows to migrate.")

    if not rows:
        print("Nothing to migrate — done.")
        return

    placeholders = ", ".join(["?"] * len(COLUMNS))
    insert_sql = f"""
        INSERT INTO issues ({', '.join(COLUMNS)})
        VALUES ({placeholders})
    """

    migrated = 0
    for row in rows:
        # Postgres gives back datetime objects for timestamp columns;
        # D1/SQLite wants text, so stringify anything that isn't
        # already a plain value.
        values = [str(v) if v is not None and not isinstance(v, (int, float, str)) else v for v in row]
        try:
            d1_execute(insert_sql, values)
            migrated += 1
        except Exception as e:
            print(f"⚠️ Failed to migrate row id={row[0]}: {e}")

    print(f"✅ Migrated {migrated}/{len(rows)} rows to D1.")


if __name__ == "__main__":
    main()
