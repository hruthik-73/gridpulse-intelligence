"""Tests for GridPulse Gold analytics transformations."""

from datetime import date, datetime

import pytest
from pyspark.sql import DataFrame, SparkSession

from gridpulse_intelligence.spark_gold import (
    build_afdc_city_mart,
    build_eia_hourly_mart,
    build_nws_hourly_mart,
)


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    """Create one Spark session for Gold tests."""

    session = (
        SparkSession.builder.master("local[2]")
        .appName("gridpulse-gold-tests")
        .config(
            "spark.sql.shuffle.partitions",
            "2",
        )
        .getOrCreate()
    )

    session.sparkContext.setLogLevel("ERROR")

    yield session

    session.stop()


def make_eia_silver(
    spark: SparkSession,
    rows: list[tuple[object, ...]],
) -> DataFrame:
    """Create a minimal EIA Silver DataFrame."""

    return spark.createDataFrame(
        rows,
        schema=(
            "period timestamp, "
            "period_date date, "
            "respondent string, "
            "respondent_name string, "
            "record_type string, "
            "value double, "
            "kafka_timestamp timestamp, "
            "replay boolean, "
            "quality_status string"
        ),
    )


def make_nws_silver(
    spark: SparkSession,
    rows: list[tuple[object, ...]],
) -> DataFrame:
    """Create a minimal NWS Silver DataFrame."""

    return spark.createDataFrame(
        rows,
        schema=(
            "latitude double, "
            "longitude double, "
            "period_start timestamp, "
            "period_end timestamp, "
            "forecast_date date, "
            "temperature double, "
            "temperature_unit string, "
            "precipitation_probability double, "
            "relative_humidity double, "
            "wind_speed string, "
            "wind_direction string, "
            "short_forecast string, "
            "event_id string, "
            "replay boolean, "
            "topic string, "
            "partition int, "
            "offset long, "
            "kafka_timestamp timestamp, "
            "quality_status string"
        ),
    )


def make_afdc_silver(
    spark: SparkSession,
    rows: list[tuple[object, ...]],
) -> DataFrame:
    """Create a minimal AFDC Silver DataFrame."""

    return spark.createDataFrame(
        rows,
        schema=(
            "city string, "
            "state string, "
            "country string, "
            "station_id long, "
            "ev_level1_evse_num int, "
            "ev_level2_evse_num int, "
            "ev_dc_fast_num int, "
            "ev_network string, "
            "updated_at timestamp, "
            "quality_status string"
        ),
    )


def test_eia_gold_pivots_four_metrics(
    spark: SparkSession,
) -> None:
    """D, DF, NG, and TI should become one hourly Gold row."""

    period = datetime(
        2026,
        8,
        10,
        5,
    )

    kafka_time = datetime(
        2026,
        8,
        11,
        20,
    )

    rows = [
        (
            period,
            date(2026, 8, 10),
            "BANC",
            "Balancing Authority of Northern California",
            "D",
            100.0,
            kafka_time,
            False,
            "PASS",
        ),
        (
            period,
            date(2026, 8, 10),
            "BANC",
            "Balancing Authority of Northern California",
            "DF",
            80.0,
            kafka_time,
            False,
            "PASS",
        ),
        (
            period,
            date(2026, 8, 10),
            "BANC",
            "Balancing Authority of Northern California",
            "NG",
            110.0,
            kafka_time,
            False,
            "PASS",
        ),
        (
            period,
            date(2026, 8, 10),
            "BANC",
            "Balancing Authority of Northern California",
            "TI",
            -5.0,
            kafka_time,
            False,
            "PASS",
        ),
    ]

    silver = make_eia_silver(
        spark,
        rows,
    )

    result = build_eia_hourly_mart(silver).collect()

    assert len(result) == 1

    row = result[0]

    assert row["demand_mwh"] == 100.0
    assert row["demand_forecast_mwh"] == 80.0
    assert row["net_generation_mwh"] == 110.0
    assert row["total_interchange_mwh"] == -5.0

    assert row["demand_forecast_error_mwh"] == 20.0

    assert row["demand_forecast_abs_error_mwh"] == 20.0

    assert row["demand_forecast_error_pct"] == pytest.approx(25.0)

    assert row["generation_demand_gap_mwh"] == 10.0

    assert row["metric_count"] == 4
    assert row["has_demand"] is True
    assert row["has_demand_forecast"] is True
    assert row["has_generation"] is True
    assert row["has_interchange"] is True


def test_eia_zero_forecast_has_no_percentage(
    spark: SparkSession,
) -> None:
    """Forecast percentage error should avoid division by zero."""

    period = datetime(
        2026,
        8,
        10,
        6,
    )

    kafka_time = datetime(
        2026,
        8,
        11,
        20,
    )

    silver = make_eia_silver(
        spark,
        [
            (
                period,
                date(2026, 8, 10),
                "PJM",
                "PJM Interconnection",
                "D",
                10.0,
                kafka_time,
                False,
                "PASS",
            ),
            (
                period,
                date(2026, 8, 10),
                "PJM",
                "PJM Interconnection",
                "DF",
                0.0,
                kafka_time,
                False,
                "PASS",
            ),
        ],
    )

    row = build_eia_hourly_mart(silver).collect()[0]

    assert row["demand_forecast_error_mwh"] == 10.0

    assert row["demand_forecast_error_pct"] is None


def test_eia_gold_excludes_failed_silver_rows(
    spark: SparkSession,
) -> None:
    """Gold must only aggregate Silver PASS records."""

    period = datetime(
        2026,
        8,
        10,
        7,
    )

    kafka_time = datetime(
        2026,
        8,
        11,
        20,
    )

    silver = make_eia_silver(
        spark,
        [
            (
                period,
                date(2026, 8, 10),
                "PJM",
                "PJM Interconnection",
                "D",
                500.0,
                kafka_time,
                False,
                "PASS",
            ),
            (
                period,
                date(2026, 8, 10),
                "PJM",
                "PJM Interconnection",
                "NG",
                999999.0,
                kafka_time,
                False,
                "FAIL",
            ),
        ],
    )

    row = build_eia_hourly_mart(silver).collect()[0]

    assert row["demand_mwh"] == 500.0

    assert row["net_generation_mwh"] is None

    assert row["metric_count"] == 1


def test_nws_gold_converts_fahrenheit(
    spark: SparkSession,
) -> None:
    """Fahrenheit forecasts should also expose Celsius."""

    silver = make_nws_silver(
        spark,
        [
            (
                41.4993,
                -81.6944,
                datetime(2026, 8, 11, 21),
                datetime(2026, 8, 11, 22),
                date(2026, 8, 11),
                68.0,
                "F",
                28.0,
                87.0,
                "2 mph",
                "W",
                "Chance Showers",
                "event-1",
                False,
                "gridpulse.nws.forecast.v1",
                1,
                1,
                datetime(2026, 8, 11, 20),
                "PASS",
            )
        ],
    )

    row = build_nws_hourly_mart(silver).collect()[0]

    assert row["temperature_f"] == 68.0

    assert row["temperature_c"] == pytest.approx(20.0)

    assert row["precipitation_risk"] == "moderate"


def test_nws_gold_converts_celsius(
    spark: SparkSession,
) -> None:
    """Celsius forecasts should also expose Fahrenheit."""

    silver = make_nws_silver(
        spark,
        [
            (
                41.4993,
                -81.6944,
                datetime(2026, 8, 11, 22),
                datetime(2026, 8, 11, 23),
                date(2026, 8, 11),
                20.0,
                "C",
                70.0,
                80.0,
                "4 mph",
                "NW",
                "Thunderstorms",
                "event-2",
                False,
                "gridpulse.nws.forecast.v1",
                1,
                2,
                datetime(2026, 8, 11, 20),
                "PASS",
            )
        ],
    )

    row = build_nws_hourly_mart(silver).collect()[0]

    assert row["temperature_c"] == 20.0

    assert row["temperature_f"] == pytest.approx(68.0)

    assert row["precipitation_risk"] == "high"


def test_nws_null_precipitation_is_unknown(
    spark: SparkSession,
) -> None:
    """Missing precipitation probability should remain explicit."""

    silver = make_nws_silver(
        spark,
        [
            (
                41.4993,
                -81.6944,
                datetime(2026, 8, 11, 23),
                datetime(2026, 8, 12, 0),
                date(2026, 8, 11),
                72.0,
                "F",
                None,
                75.0,
                "3 mph",
                "W",
                "Mostly Cloudy",
                "event-3",
                False,
                "gridpulse.nws.forecast.v1",
                1,
                3,
                datetime(2026, 8, 11, 20),
                "PASS",
            )
        ],
    )

    row = build_nws_hourly_mart(silver).collect()[0]

    assert row["precipitation_risk"] == "unknown"


def test_afdc_gold_aggregates_city_infrastructure(
    spark: SparkSession,
) -> None:
    """Station observations should aggregate into city metrics."""

    silver = make_afdc_silver(
        spark,
        [
            (
                "Cleveland",
                "OH",
                "US",
                1001,
                0,
                2,
                0,
                "Network A",
                datetime(2026, 7, 1, 10),
                "PASS",
            ),
            (
                "Cleveland",
                "OH",
                "US",
                1002,
                1,
                4,
                2,
                "Network B",
                datetime(2026, 7, 10, 10),
                "PASS",
            ),
        ],
    )

    row = build_afdc_city_mart(silver).collect()[0]

    assert row["city"] == "Cleveland"
    assert row["state"] == "OH"

    assert row["station_count"] == 2
    assert row["level1_ports"] == 1
    assert row["level2_ports"] == 6
    assert row["dc_fast_ports"] == 2

    assert row["total_known_ports"] == 9

    assert row["ports_per_station"] == pytest.approx(4.5)

    assert row["dc_fast_station_count"] == 1

    assert row["dc_fast_station_share_pct"] == pytest.approx(50.0)

    assert row["network_count"] == 2

    assert row["latest_station_update"] == datetime(
        2026,
        7,
        10,
        10,
    )


def test_afdc_gold_excludes_failed_rows(
    spark: SparkSession,
) -> None:
    """Failed Silver station rows must not enter Gold."""

    silver = make_afdc_silver(
        spark,
        [
            (
                "Cleveland",
                "OH",
                "US",
                1001,
                0,
                2,
                0,
                "Network A",
                datetime(2026, 7, 1, 10),
                "PASS",
            ),
            (
                "Cleveland",
                "OH",
                "US",
                9999,
                50,
                50,
                50,
                "Bad Network",
                datetime(2026, 7, 20, 10),
                "FAIL",
            ),
        ],
    )

    row = build_afdc_city_mart(silver).collect()[0]

    assert row["station_count"] == 1
    assert row["level1_ports"] == 0
    assert row["level2_ports"] == 2
    assert row["dc_fast_ports"] == 0
    assert row["total_known_ports"] == 2
