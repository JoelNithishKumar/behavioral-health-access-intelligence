import duckdb

from config import DB_PATH, SQL_DIR, SYNTHETIC_DIR
from data_quality import run_data_quality_checks

TABLES = [
    "dim_department",
    "dim_clinic",
    "dim_zip_code",
    "dim_patient",
    "dim_provider",
    "fact_referral",
    "fact_appointment",
    "fact_screening",
    "fact_encounter",
    "fact_followup",
]


def load_csv_tables() -> None:
    conn = duckdb.connect(str(DB_PATH))
    for table in TABLES:
        csv_path = SYNTHETIC_DIR / f"{table}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing {csv_path}. Run python src/generate_synthetic_data.py first.")
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto('{csv_path.as_posix()}', HEADER=TRUE)")
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"Loaded {table}: {count:,} rows")
    conn.close()


def create_views() -> None:
    conn = duckdb.connect(str(DB_PATH))
    sql_path = SQL_DIR / "02_create_views.sql"
    conn.execute(sql_path.read_text())
    print("Created analytics SQL views.")
    conn.close()


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    load_csv_tables()
    dq_df = run_data_quality_checks(DB_PATH)
    print("Data quality checks complete:")
    print(dq_df[["rule_id", "status", "failed_row_count"]].to_string(index=False))
    create_views()
    print(f"Warehouse ready: {DB_PATH}")


if __name__ == "__main__":
    main()
