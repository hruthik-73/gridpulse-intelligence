"""Analytics-ready Gold transformations for GridPulse."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def build_eia_hourly_mart(
    eia_silver: DataFrame,
) -> DataFrame:
    """Build balancing-authority hourly electricity analytics."""

    valid = eia_silver.filter(F.col("quality_status") == "PASS")

    hourly = (
        valid.groupBy(
            "period",
            "period_date",
            "respondent",
            "respondent_name",
        )
        .agg(
            F.max(
                F.when(
                    F.col("record_type") == "D",
                    F.col("value"),
                )
            ).alias("demand_mwh"),
            F.max(
                F.when(
                    F.col("record_type") == "DF",
                    F.col("value"),
                )
            ).alias("demand_forecast_mwh"),
            F.max(
                F.when(
                    F.col("record_type") == "NG",
                    F.col("value"),
                )
            ).alias("net_generation_mwh"),
            F.max(
                F.when(
                    F.col("record_type") == "TI",
                    F.col("value"),
                )
            ).alias("total_interchange_mwh"),
            F.countDistinct("record_type").alias("metric_count"),
            F.max("kafka_timestamp").alias("latest_kafka_timestamp"),
            F.max(
                F.when(
                    F.col("replay"),
                    F.lit(1),
                ).otherwise(F.lit(0))
            ).alias("_contains_replay"),
        )
        .withColumn(
            "contains_replay",
            F.col("_contains_replay").cast("boolean"),
        )
        .drop("_contains_replay")
        .withColumn(
            "hour_of_day",
            F.hour(F.col("period")),
        )
    )

    return (
        hourly.withColumn(
            "demand_forecast_error_mwh",
            F.when(
                F.col("demand_mwh").isNotNull() & F.col("demand_forecast_mwh").isNotNull(),
                F.col("demand_mwh") - F.col("demand_forecast_mwh"),
            ),
        )
        .withColumn(
            "demand_forecast_abs_error_mwh",
            F.abs(F.col("demand_forecast_error_mwh")),
        )
        .withColumn(
            "demand_forecast_error_pct",
            F.when(
                F.col("demand_forecast_mwh").isNotNull() & (F.col("demand_forecast_mwh") != 0),
                (F.col("demand_forecast_error_mwh") / F.col("demand_forecast_mwh")) * 100,
            ),
        )
        .withColumn(
            "generation_demand_gap_mwh",
            F.when(
                F.col("net_generation_mwh").isNotNull() & F.col("demand_mwh").isNotNull(),
                F.col("net_generation_mwh") - F.col("demand_mwh"),
            ),
        )
        .withColumn(
            "has_demand",
            F.col("demand_mwh").isNotNull(),
        )
        .withColumn(
            "has_demand_forecast",
            F.col("demand_forecast_mwh").isNotNull(),
        )
        .withColumn(
            "has_generation",
            F.col("net_generation_mwh").isNotNull(),
        )
        .withColumn(
            "has_interchange",
            F.col("total_interchange_mwh").isNotNull(),
        )
    )


def build_nws_hourly_mart(
    nws_silver: DataFrame,
) -> DataFrame:
    """Build analytics-ready hourly weather forecasts."""

    valid = nws_silver.filter(F.col("quality_status") == "PASS")

    return (
        valid.withColumn(
            "location_key",
            F.concat(
                F.format_number(
                    F.col("latitude"),
                    4,
                ),
                F.lit(","),
                F.format_number(
                    F.col("longitude"),
                    4,
                ),
            ),
        )
        .withColumn(
            "temperature_f",
            F.when(
                F.col("temperature_unit") == "F",
                F.col("temperature"),
            ).when(
                F.col("temperature_unit") == "C",
                (F.col("temperature") * 9 / 5) + 32,
            ),
        )
        .withColumn(
            "temperature_c",
            F.when(
                F.col("temperature_unit") == "C",
                F.col("temperature"),
            ).when(
                F.col("temperature_unit") == "F",
                (F.col("temperature") - 32) * 5 / 9,
            ),
        )
        .withColumn(
            "precipitation_risk",
            F.when(
                F.col("precipitation_probability").isNull(),
                F.lit("unknown"),
            )
            .when(
                F.col("precipitation_probability") < 20,
                F.lit("low"),
            )
            .when(
                F.col("precipitation_probability") < 50,
                F.lit("moderate"),
            )
            .otherwise(F.lit("high")),
        )
        .withColumn(
            "forecast_hour",
            F.hour(F.col("period_start")),
        )
        .select(
            "location_key",
            "latitude",
            "longitude",
            "period_start",
            "period_end",
            "forecast_date",
            "forecast_hour",
            "temperature",
            "temperature_unit",
            "temperature_f",
            "temperature_c",
            "precipitation_probability",
            "precipitation_risk",
            "relative_humidity",
            "wind_speed",
            "wind_direction",
            "short_forecast",
            "event_id",
            "replay",
            "topic",
            "partition",
            "offset",
            "kafka_timestamp",
        )
    )


def build_afdc_city_mart(
    afdc_silver: DataFrame,
) -> DataFrame:
    """Aggregate EV charging infrastructure by city."""

    valid = afdc_silver.filter(F.col("quality_status") == "PASS")

    city = (
        valid.groupBy(
            "city",
            "state",
            "country",
        )
        .agg(
            F.countDistinct("station_id").alias("station_count"),
            F.sum(
                F.coalesce(
                    F.col("ev_level1_evse_num"),
                    F.lit(0),
                )
            ).alias("level1_ports"),
            F.sum(
                F.coalesce(
                    F.col("ev_level2_evse_num"),
                    F.lit(0),
                )
            ).alias("level2_ports"),
            F.sum(
                F.coalesce(
                    F.col("ev_dc_fast_num"),
                    F.lit(0),
                )
            ).alias("dc_fast_ports"),
            F.sum(
                F.when(
                    F.coalesce(
                        F.col("ev_dc_fast_num"),
                        F.lit(0),
                    )
                    > 0,
                    F.lit(1),
                ).otherwise(F.lit(0))
            ).alias("dc_fast_station_count"),
            F.countDistinct("ev_network").alias("network_count"),
            F.max("updated_at").alias("latest_station_update"),
        )
        .withColumn(
            "total_known_ports",
            F.col("level1_ports") + F.col("level2_ports") + F.col("dc_fast_ports"),
        )
    )

    return city.withColumn(
        "ports_per_station",
        F.when(
            F.col("station_count") > 0,
            F.col("total_known_ports") / F.col("station_count"),
        ),
    ).withColumn(
        "dc_fast_station_share_pct",
        F.when(
            F.col("station_count") > 0,
            (F.col("dc_fast_station_count") / F.col("station_count")) * 100,
        ),
    )
