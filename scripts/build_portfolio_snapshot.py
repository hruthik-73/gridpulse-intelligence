"""Build a read-only public analytics snapshot for GridPulse."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

DEFAULT_SOURCE = Path("data/warehouse/gridpulse.duckdb")

DEFAULT_DESTINATION = Path("src/gridpulse_intelligence/assets/gridpulse_portfolio.duckdb")


def quote_identifier(
    value: str,
) -> str:
    """Safely quote a DuckDB identifier."""

    return (
        '"'
        + value.replace(
            '"',
            '""',
        )
        + '"'
    )


def main() -> None:
    """Materialize public analytics relations into a portable DB."""

    source = Path(
        os.getenv(
            "GRIDPULSE_SOURCE_DATABASE_PATH",
            str(DEFAULT_SOURCE),
        )
    ).resolve()

    destination = Path(
        os.getenv(
            "GRIDPULSE_PORTFOLIO_DATABASE_PATH",
            str(DEFAULT_DESTINATION),
        )
    ).resolve()

    if not source.exists():
        raise SystemExit(f"Source warehouse does not exist: {source}")

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination.exists():
        destination.unlink()

    source_connection = duckdb.connect(
        str(source),
        read_only=True,
    )

    try:
        relations = [
            row[0]
            for row in source_connection.execute(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'analytics'
                order by table_name
                """
            ).fetchall()
        ]
    finally:
        source_connection.close()

    if not relations:
        raise SystemExit("No analytics relations found in source warehouse.")

    destination_connection = duckdb.connect(str(destination))

    source_sql = str(source).replace(
        "'",
        "''",
    )

    try:
        destination_connection.execute("create schema analytics")

        destination_connection.execute(f"attach '{source_sql}' as gridpulse_source (read_only)")

        for relation in relations:
            identifier = quote_identifier(relation)

            destination_connection.execute(
                f"""
                create table analytics.{identifier}
                as
                select *
                from gridpulse_source.analytics.{identifier}
                """
            )

            count = destination_connection.execute(
                f"""
                select count(*)
                from analytics.{identifier}
                """
            ).fetchone()[0]

            print(f"{relation}: {count} rows")

        destination_connection.execute("detach gridpulse_source")

        destination_connection.execute("checkpoint")

    finally:
        destination_connection.close()

    size_mb = destination.stat().st_size / 1024 / 1024

    print()
    print("Portfolio snapshot created:")
    print(destination)
    print(f"Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
