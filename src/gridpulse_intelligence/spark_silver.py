"""Typed Silver transformations for GridPulse Bronze events."""

from typing import Final

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

EIA_PAYLOAD_SCHEMA: Final[StructType] = StructType(
    [
        StructField(
            "period",
            StringType(),
            True,
        ),
        StructField(
            "record_type",
            StringType(),
            True,
        ),
        StructField(
            "respondent",
            StringType(),
            True,
        ),
        StructField(
            "respondent_name",
            StringType(),
            True,
        ),
        StructField(
            "type_name",
            StringType(),
            True,
        ),
        StructField(
            "value",
            DoubleType(),
            True,
        ),
        StructField(
            "value_units",
            StringType(),
            True,
        ),
    ]
)

NWS_PAYLOAD_SCHEMA: Final[StructType] = StructType(
    [
        StructField(
            "latitude",
            DoubleType(),
            True,
        ),
        StructField(
            "longitude",
            DoubleType(),
            True,
        ),
        StructField(
            "period_end",
            StringType(),
            True,
        ),
        StructField(
            "period_start",
            StringType(),
            True,
        ),
        StructField(
            "precipitation_probability",
            DoubleType(),
            True,
        ),
        StructField(
            "relative_humidity",
            DoubleType(),
            True,
        ),
        StructField(
            "short_forecast",
            StringType(),
            True,
        ),
        StructField(
            "temperature",
            DoubleType(),
            True,
        ),
        StructField(
            "temperature_unit",
            StringType(),
            True,
        ),
        StructField(
            "wind_direction",
            StringType(),
            True,
        ),
        StructField(
            "wind_speed",
            StringType(),
            True,
        ),
    ]
)

AFDC_PAYLOAD_SCHEMA: Final[StructType] = StructType(
    [
        StructField(
            "access_code",
            StringType(),
            True,
        ),
        StructField(
            "city",
            StringType(),
            True,
        ),
        StructField(
            "country",
            StringType(),
            True,
        ),
        StructField(
            "date_last_confirmed",
            StringType(),
            True,
        ),
        StructField(
            "ev_connector_types",
            ArrayType(
                StringType(),
                containsNull=False,
            ),
            True,
        ),
        StructField(
            "ev_dc_fast_num",
            IntegerType(),
            True,
        ),
        StructField(
            "ev_level1_evse_num",
            IntegerType(),
            True,
        ),
        StructField(
            "ev_level2_evse_num",
            IntegerType(),
            True,
        ),
        StructField(
            "ev_network",
            StringType(),
            True,
        ),
        StructField(
            "facility_type",
            StringType(),
            True,
        ),
        StructField(
            "fuel_type_code",
            StringType(),
            True,
        ),
        StructField(
            "latitude",
            DoubleType(),
            True,
        ),
        StructField(
            "longitude",
            DoubleType(),
            True,
        ),
        StructField(
            "state",
            StringType(),
            True,
        ),
        StructField(
            "station_id",
            LongType(),
            True,
        ),
        StructField(
            "station_name",
            StringType(),
            True,
        ),
        StructField(
            "status_code",
            StringType(),
            True,
        ),
        StructField(
            "street_address",
            StringType(),
            True,
        ),
        StructField(
            "updated_at",
            StringType(),
            True,
        ),
        StructField(
            "zip_code",
            StringType(),
            True,
        ),
    ]
)

LINEAGE_COLUMNS: Final[tuple[str, ...]] = (
    "event_id",
    "event_version",
    "event_type",
    "partition_key",
    "emitted_at",
    "replay",
    "source_timestamp",
    "topic",
    "partition",
    "offset",
    "kafka_timestamp",
    "kafka_key",
)


def _source_payload(
    bronze: DataFrame,
    source: str,
    schema: StructType,
) -> DataFrame:
    """Filter one source and parse its payload."""

    return (
        bronze.filter(F.col("source") == source)
        .withColumn(
            "payload",
            F.from_json(
                F.col("payload_json"),
                schema,
            ),
        )
        .withColumn(
            "event_emitted_at",
            F.to_timestamp(F.col("emitted_at")),
        )
    )


def _with_quality_columns(
    dataframe: DataFrame,
    quality_error: Column,
) -> DataFrame:
    """Attach common Silver quality metadata."""

    return (
        dataframe.withColumn(
            "quality_error",
            quality_error,
        )
        .withColumn(
            "is_valid",
            F.col("quality_error").isNull(),
        )
        .withColumn(
            "quality_status",
            F.when(
                F.col("is_valid"),
                F.lit("PASS"),
            ).otherwise(
                F.lit("FAIL"),
            ),
        )
    )


def transform_eia(
    bronze: DataFrame,
) -> DataFrame:
    """Create typed EIA Silver candidate records."""

    parsed = _source_payload(
        bronze=bronze,
        source="eia",
        schema=EIA_PAYLOAD_SCHEMA,
    )

    typed = parsed.select(
        *LINEAGE_COLUMNS,
        "event_emitted_at",
        F.col("payload.period").alias("period_raw"),
        F.to_timestamp(F.col("payload.period")).alias("period"),
        F.col("payload.record_type").alias("record_type"),
        F.col("payload.respondent").alias("respondent"),
        F.col("payload.respondent_name").alias("respondent_name"),
        F.col("payload.type_name").alias("type_name"),
        F.col("payload.value").alias("value"),
        F.col("payload.value_units").alias("value_units"),
    ).withColumn(
        "period_date",
        F.to_date(F.col("period")),
    )

    quality_error = (
        F.when(
            F.col("period").isNull(),
            F.lit("invalid_period"),
        )
        .when(
            F.col("respondent").isNull() | (F.length(F.trim(F.col("respondent"))) == 0),
            F.lit("invalid_respondent"),
        )
        .when(
            F.col("record_type").isNull() | (F.length(F.trim(F.col("record_type"))) == 0),
            F.lit("invalid_record_type"),
        )
        .when(
            F.col("value").isNull(),
            F.lit("invalid_value"),
        )
        .when(
            F.col("value_units").isNull() | (F.length(F.trim(F.col("value_units"))) == 0),
            F.lit("invalid_value_units"),
        )
    )

    return _with_quality_columns(
        typed,
        quality_error,
    )


def transform_nws(
    bronze: DataFrame,
) -> DataFrame:
    """Create typed NWS Silver candidate records."""

    parsed = _source_payload(
        bronze=bronze,
        source="nws",
        schema=NWS_PAYLOAD_SCHEMA,
    )

    typed = parsed.select(
        *LINEAGE_COLUMNS,
        "event_emitted_at",
        F.col("payload.latitude").alias("latitude"),
        F.col("payload.longitude").alias("longitude"),
        F.to_timestamp(F.col("payload.period_start")).alias("period_start"),
        F.to_timestamp(F.col("payload.period_end")).alias("period_end"),
        F.col("payload.temperature").alias("temperature"),
        F.col("payload.temperature_unit").alias("temperature_unit"),
        F.col("payload.precipitation_probability").alias("precipitation_probability"),
        F.col("payload.relative_humidity").alias("relative_humidity"),
        F.col("payload.wind_speed").alias("wind_speed"),
        F.col("payload.wind_direction").alias("wind_direction"),
        F.col("payload.short_forecast").alias("short_forecast"),
    ).withColumn(
        "forecast_date",
        F.to_date(F.col("period_start")),
    )

    quality_error = (
        F.when(
            F.col("latitude").isNull() | (F.col("latitude") < -90) | (F.col("latitude") > 90),
            F.lit("invalid_latitude"),
        )
        .when(
            F.col("longitude").isNull() | (F.col("longitude") < -180) | (F.col("longitude") > 180),
            F.lit("invalid_longitude"),
        )
        .when(
            F.col("period_start").isNull(),
            F.lit("invalid_period_start"),
        )
        .when(
            F.col("period_end").isNull(),
            F.lit("invalid_period_end"),
        )
        .when(
            F.col("period_end") <= F.col("period_start"),
            F.lit("invalid_period_range"),
        )
        .when(
            F.col("temperature").isNull(),
            F.lit("invalid_temperature"),
        )
        .when(
            F.col("temperature_unit").isNull()
            | (
                ~F.col("temperature_unit").isin(
                    "F",
                    "C",
                )
            ),
            F.lit("invalid_temperature_unit"),
        )
        .when(
            F.col("precipitation_probability").isNotNull()
            & (
                (F.col("precipitation_probability") < 0)
                | (F.col("precipitation_probability") > 100)
            ),
            F.lit("invalid_precipitation_probability"),
        )
        .when(
            F.col("relative_humidity").isNotNull()
            & ((F.col("relative_humidity") < 0) | (F.col("relative_humidity") > 100)),
            F.lit("invalid_relative_humidity"),
        )
        .when(
            F.col("short_forecast").isNull() | (F.length(F.trim(F.col("short_forecast"))) == 0),
            F.lit("invalid_short_forecast"),
        )
    )

    return _with_quality_columns(
        typed,
        quality_error,
    )


def transform_afdc(
    bronze: DataFrame,
) -> DataFrame:
    """Create typed AFDC Silver candidate records."""

    parsed = _source_payload(
        bronze=bronze,
        source="afdc",
        schema=AFDC_PAYLOAD_SCHEMA,
    )

    typed = parsed.select(
        *LINEAGE_COLUMNS,
        "event_emitted_at",
        F.col("payload.station_id").alias("station_id"),
        F.col("payload.station_name").alias("station_name"),
        F.col("payload.street_address").alias("street_address"),
        F.col("payload.city").alias("city"),
        F.col("payload.state").alias("state"),
        F.col("payload.zip_code").alias("zip_code"),
        F.col("payload.country").alias("country"),
        F.col("payload.latitude").alias("latitude"),
        F.col("payload.longitude").alias("longitude"),
        F.col("payload.fuel_type_code").alias("fuel_type_code"),
        F.col("payload.access_code").alias("access_code"),
        F.col("payload.status_code").alias("status_code"),
        F.col("payload.ev_network").alias("ev_network"),
        F.col("payload.ev_connector_types").alias("ev_connector_types"),
        F.col("payload.ev_level1_evse_num").alias("ev_level1_evse_num"),
        F.col("payload.ev_level2_evse_num").alias("ev_level2_evse_num"),
        F.col("payload.ev_dc_fast_num").alias("ev_dc_fast_num"),
        F.col("payload.facility_type").alias("facility_type"),
        F.to_date(F.col("payload.date_last_confirmed")).alias("date_last_confirmed"),
        F.to_timestamp(F.col("payload.updated_at")).alias("updated_at"),
    )

    quality_error = (
        F.when(
            F.col("station_id").isNull() | (F.col("station_id") <= 0),
            F.lit("invalid_station_id"),
        )
        .when(
            F.col("station_name").isNull() | (F.length(F.trim(F.col("station_name"))) == 0),
            F.lit("invalid_station_name"),
        )
        .when(
            F.col("latitude").isNull() | (F.col("latitude") < -90) | (F.col("latitude") > 90),
            F.lit("invalid_latitude"),
        )
        .when(
            F.col("longitude").isNull() | (F.col("longitude") < -180) | (F.col("longitude") > 180),
            F.lit("invalid_longitude"),
        )
        .when(
            F.col("state").isNull() | (F.length(F.trim(F.col("state"))) != 2),
            F.lit("invalid_state"),
        )
        .when(
            F.col("fuel_type_code").isNull() | (F.col("fuel_type_code") != "ELEC"),
            F.lit("invalid_fuel_type"),
        )
        .when(
            F.col("access_code").isNull() | (F.col("access_code") != "public"),
            F.lit("invalid_access_code"),
        )
        .when(
            F.col("status_code").isNull() | (F.col("status_code") != "E"),
            F.lit("invalid_status_code"),
        )
    )

    return _with_quality_columns(
        typed,
        quality_error,
    )


def _deduplicate_latest(
    dataframe: DataFrame,
    keys: tuple[str, ...],
    additional_order: tuple[Column, ...] = (),
) -> DataFrame:
    """Keep the newest valid record for each business key."""

    window = Window.partitionBy(*keys).orderBy(
        *additional_order,
        F.col("event_emitted_at").desc_nulls_last(),
        F.col("kafka_timestamp").desc_nulls_last(),
        F.col("partition").desc(),
        F.col("offset").desc(),
    )

    return (
        dataframe.filter(F.col("is_valid"))
        .withColumn(
            "_silver_row_number",
            F.row_number().over(window),
        )
        .filter(F.col("_silver_row_number") == 1)
        .drop("_silver_row_number")
    )


def deduplicate_eia(
    dataframe: DataFrame,
) -> DataFrame:
    """Deduplicate EIA using its natural business key."""

    return _deduplicate_latest(
        dataframe,
        (
            "period",
            "respondent",
            "record_type",
        ),
    )


def deduplicate_nws(
    dataframe: DataFrame,
) -> DataFrame:
    """Deduplicate forecasts by location and forecast hour."""

    return _deduplicate_latest(
        dataframe,
        (
            "latitude",
            "longitude",
            "period_start",
        ),
    )


def deduplicate_afdc(
    dataframe: DataFrame,
) -> DataFrame:
    """Keep the newest observation for each charging station."""

    return _deduplicate_latest(
        dataframe,
        ("station_id",),
        (F.col("updated_at").desc_nulls_last(),),
    )
