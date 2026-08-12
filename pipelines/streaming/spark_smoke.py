"""Local Spark smoke test for GridPulse Intelligence."""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main() -> None:
    """Create a small DataFrame and verify local Spark execution."""

    spark = (
        SparkSession.builder.appName("gridpulse-spark-smoke")
        .master("local[2]")
        .config(
            "spark.sql.shuffle.partitions",
            "2",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    data = [
        ("eia", 5),
        ("nws", 5),
        ("afdc", 5),
    ]

    dataframe = spark.createDataFrame(
        data,
        schema=[
            "source",
            "event_count",
        ],
    )

    result = dataframe.agg(F.sum("event_count").alias("total_events")).collect()[0]["total_events"]

    print()
    print("GridPulse Spark smoke test completed")
    print(f"Spark version: {spark.version}")
    print(f"Total events: {result}")

    spark.stop()


if __name__ == "__main__":
    main()
