"""Build analytics-ready GridPulse Gold marts."""

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

from gridpulse_intelligence.spark_gold import (
    build_afdc_city_mart,
    build_eia_hourly_mart,
    build_nws_hourly_mart,
)

SILVER_ROOT = Path("data/processed/silver")

GOLD_ROOT = Path("data/processed/gold")

EIA_SILVER_PATH = SILVER_ROOT / "eia_region_data"

NWS_SILVER_PATH = SILVER_ROOT / "nws_hourly_forecast"

AFDC_SILVER_PATH = SILVER_ROOT / "afdc_ev_stations"


def write_gold(
    dataframe: DataFrame,
    path: Path,
    partition_columns: tuple[str, ...] = (),
) -> None:
    """Write one Gold mart idempotently."""

    writer = dataframe.write.mode("overwrite").format("parquet")

    if partition_columns:
        writer = writer.partitionBy(*partition_columns)

    writer.save(str(path))


def main() -> None:
    """Build all GridPulse Gold marts."""

    spark = (
        SparkSession.builder.master("local[2]")
        .appName("gridpulse-build-gold")
        .config(
            "spark.sql.shuffle.partitions",
            "3",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    eia_silver = spark.read.parquet(str(EIA_SILVER_PATH))

    nws_silver = spark.read.parquet(str(NWS_SILVER_PATH))

    afdc_silver = spark.read.parquet(str(AFDC_SILVER_PATH))

    eia_gold = build_eia_hourly_mart(eia_silver)

    nws_gold = build_nws_hourly_mart(nws_silver)

    afdc_gold = build_afdc_city_mart(afdc_silver)

    write_gold(
        eia_gold,
        GOLD_ROOT / "eia_balancing_authority_hourly",
        ("period_date",),
    )

    write_gold(
        nws_gold,
        GOLD_ROOT / "nws_hourly_weather",
        ("forecast_date",),
    )

    write_gold(
        afdc_gold,
        GOLD_ROOT / "afdc_city_infrastructure",
        ("state",),
    )

    print()
    print("=" * 68)
    print("GRIDPULSE GOLD BUILD")
    print("=" * 68)

    print(
        "EIA Silver rows:",
        eia_silver.count(),
    )

    print(
        "EIA Gold hourly rows:",
        eia_gold.count(),
    )

    print(
        "NWS Silver rows:",
        nws_silver.count(),
    )

    print(
        "NWS Gold hourly rows:",
        nws_gold.count(),
    )

    print(
        "AFDC Silver stations:",
        afdc_silver.count(),
    )

    print(
        "AFDC Gold cities:",
        afdc_gold.count(),
    )

    print("=" * 68)
    print("Gold build completed.")
    print()

    spark.stop()


if __name__ == "__main__":
    main()
