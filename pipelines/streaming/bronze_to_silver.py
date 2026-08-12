"""Normalize GridPulse Bronze events into typed Silver datasets."""

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from gridpulse_intelligence.spark_silver import (
    deduplicate_afdc,
    deduplicate_eia,
    deduplicate_nws,
    transform_afdc,
    transform_eia,
    transform_nws,
)

BRONZE_PATH = Path("data/raw/streaming/bronze_events")

SILVER_ROOT = Path("data/processed/silver")

QUARANTINE_PATH = Path("data/quarantine/silver_events")


def write_dataset(
    dataframe: DataFrame,
    path: Path,
    partition_columns: tuple[str, ...] = (),
) -> None:
    """Write one Silver dataset idempotently."""

    writer = dataframe.write.mode("overwrite").format("parquet")

    if partition_columns:
        writer = writer.partitionBy(*partition_columns)

    writer.save(str(path))


def main() -> None:
    """Build all GridPulse Silver datasets."""

    spark = (
        SparkSession.builder.master("local[2]")
        .appName("gridpulse-bronze-to-silver")
        .config(
            "spark.sql.shuffle.partitions",
            "3",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    bronze = spark.read.parquet(str(BRONZE_PATH))

    eia_candidates = transform_eia(bronze)

    nws_candidates = transform_nws(bronze)

    afdc_candidates = transform_afdc(bronze)

    eia_silver = deduplicate_eia(eia_candidates)

    nws_silver = deduplicate_nws(nws_candidates)

    afdc_silver = deduplicate_afdc(afdc_candidates)

    invalid = (
        eia_candidates.filter(~F.col("is_valid"))
        .withColumn(
            "source",
            F.lit("eia"),
        )
        .select(
            "source",
            "event_id",
            "event_type",
            "topic",
            "partition",
            "offset",
            "kafka_timestamp",
            "quality_error",
        )
        .unionByName(
            nws_candidates.filter(~F.col("is_valid"))
            .withColumn(
                "source",
                F.lit("nws"),
            )
            .select(
                "source",
                "event_id",
                "event_type",
                "topic",
                "partition",
                "offset",
                "kafka_timestamp",
                "quality_error",
            )
        )
        .unionByName(
            afdc_candidates.filter(~F.col("is_valid"))
            .withColumn(
                "source",
                F.lit("afdc"),
            )
            .select(
                "source",
                "event_id",
                "event_type",
                "topic",
                "partition",
                "offset",
                "kafka_timestamp",
                "quality_error",
            )
        )
    )

    write_dataset(
        eia_silver,
        SILVER_ROOT / "eia_region_data",
        ("period_date",),
    )

    write_dataset(
        nws_silver,
        SILVER_ROOT / "nws_hourly_forecast",
        ("forecast_date",),
    )

    write_dataset(
        afdc_silver,
        SILVER_ROOT / "afdc_ev_stations",
        ("state",),
    )

    write_dataset(
        invalid,
        QUARANTINE_PATH,
        ("source",),
    )

    print()
    print("=" * 64)
    print("GRIDPULSE SILVER BUILD")
    print("=" * 64)
    print(
        "Bronze input:",
        bronze.count(),
    )
    print(
        "EIA Silver:",
        eia_silver.count(),
    )
    print(
        "NWS Silver:",
        nws_silver.count(),
    )
    print(
        "AFDC Silver:",
        afdc_silver.count(),
    )
    print(
        "Silver quality failures:",
        invalid.count(),
    )
    print("=" * 64)
    print("Silver build completed.")
    print()

    spark.stop()


if __name__ == "__main__":
    main()
