import json
import logging
import os
from datetime import date
from urllib.parse import urlparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    avg,
    col,
    count as spark_count,
    from_json,
    lit,
    max as spark_max,
    min as spark_min,
    to_timestamp,
    when,
    window,
)
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("I2-T3-Spark")

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:29092")
KAFKA_TOPICS = os.getenv("KAFKA_TOPICS", "sensor.raw,sensor.processed")
TIMESCALE_URL = os.getenv(
    "TIMESCALE_URL", "postgresql://ctuser:ctpass@timescaledb:5432/campustwin"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
STREAM_WINDOW = os.getenv("STREAM_WINDOW", "5 seconds")
SPARK_APP_NAME = os.getenv("SPARK_APP_NAME", "SmartCampusSparkProcessor")


def parse_postgres_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError(f"Unsupported URL scheme for TimescaleDB: {parsed.scheme}")
    jdbc_url = f"jdbc:postgresql://{parsed.hostname}:{parsed.port}{parsed.path}"
    return jdbc_url, parsed.username, parsed.password


def build_spark_session():
    builder = SparkSession.builder.appName(SPARK_APP_NAME)
    builder = builder.config(
        "spark.jars.packages", "org.postgresql:postgresql:42.6.0"
    )
    builder = builder.config("spark.sql.shuffle.partitions", "6")
    return builder.getOrCreate()


def load_reference_table(spark, jdbc_url, user, password, table_name, select_columns="*"):
    dbtable = f"(SELECT {select_columns} FROM {table_name}) AS {table_name}_ref"
    return (
        spark.read.format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", dbtable)
        .option("user", user)
        .option("password", password)
        .option("driver", "org.postgresql.Driver")
        .load()
    )


def build_input_schema():
    return StructType(
        [
            StructField("sensor_id", StringType(), nullable=False),
            StructField("building_id", StringType(), nullable=False),
            StructField("floor", IntegerType(), nullable=False),
            StructField("room_id", StringType(), nullable=False),
            StructField("sensor_type", StringType(), nullable=False),
            StructField("value", DoubleType(), nullable=False),
            StructField("unit", StringType(), nullable=False),
            StructField("timestamp_ms", LongType(), nullable=False),
            StructField("quality", DoubleType(), nullable=True),
        ]
    )


def build_anomaly_expression():
    return (
        when(
            (col("sensor_type") == "temperature") & (col("avg_value") > 30.0),
            lit("TEMP_HIGH"),
        )
        .when(
            (col("sensor_type") == "temperature") & (col("avg_value") < 16.0),
            lit("TEMP_LOW"),
        )
        .when(
            (col("sensor_type") == "humidity") & (col("avg_value") > 90.0),
            lit("HUMIDITY_HIGH"),
        )
        .when(
            (col("sensor_type") == "humidity") & (col("avg_value") < 15.0),
            lit("HUMIDITY_LOW"),
        )
        .when(
            (col("sensor_type") == "pressure") & (col("avg_value") > 1040.0),
            lit("PRESSURE_HIGH"),
        )
        .when(
            (col("sensor_type") == "pressure") & (col("avg_value") < 985.0),
            lit("PRESSURE_LOW"),
        )
        .when(
            (col("sensor_type") == "vibration") & (col("avg_value") > 15.0),
            lit("VIBRATION_SPIKE"),
        )
        .when(
            (col("sensor_type") == "occupancy") & (col("avg_value") > 120.0),
            lit("OVERCAPACITY"),
        )
        .otherwise(lit(None).cast(StringType()))
    )


def enrich_payload(parsed):
    return (
        parsed.withColumn("ts", to_timestamp((col("timestamp_ms") / 1000).cast("double")))
        .withColumnRenamed("value", "raw_value")
        .withColumn("quality", col("quality").cast(DoubleType()))
    )


def build_stream(spark, schema, room_reference):
    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKERS)
        .option("subscribe", KAFKA_TOPICS)
        .option("startingOffsets", "latest")
        .load()
    )

    payload = raw_stream.selectExpr("CAST(value AS STRING) AS payload")
    parsed = payload.select(from_json(col("payload"), schema).alias("data")).select("data.*")
    parsed = parsed.filter(
        col("room_id").isNotNull()
        & col("sensor_type").isNotNull()
        & col("value").isNotNull()
        & col("timestamp_ms").isNotNull()
    )

    enriched = (
        enrich_payload(parsed)
        .join(
            room_reference.select(
                "room_id",
                col("building_id").alias("lookup_building_id"),
                col("room_type"),
            ),
            on="room_id",
            how="left",
        )
        .withColumn(
            "building_id",
            when(col("building_id").isNull(), col("lookup_building_id")).otherwise(
                col("building_id")
            ),
        )
        .drop("lookup_building_id")
    )

    aggregation = (
        enriched.groupBy(
            window(col("ts"), STREAM_WINDOW),
            col("room_id"),
            col("building_id"),
            col("sensor_type"),
        )
        .agg(
            avg("raw_value").alias("avg_value"),
            spark_min("raw_value").alias("min_value"),
            spark_max("raw_value").alias("max_value"),
            spark_count("*").alias("sample_count"),
        )
        .withColumn("anomaly_type", build_anomaly_expression())
        .withColumn("anomaly_flag", col("anomaly_type").isNotNull())
        .withColumn("window_start", col("window.start"))
        .withColumn("window_end", col("window.end"))
        .withColumn("ts", col("window.end"))
        .drop("window")
    )

    return aggregation


def write_batch_to_timescale(batch_df, jdbc_url, jdbc_user, jdbc_password):
    (
        batch_df.write.format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", "sensor_readings")
        .option("user", jdbc_user)
        .option("password", jdbc_password)
        .option("driver", "org.postgresql.Driver")
        .mode("append")
        .save()
    )


def publish_redis_events(batch_df, redis_url):
    try:
        import redis
    except ImportError as exc:
        logger.error("Missing redis dependency: %s", exc)
        raise

    client = redis.from_url(redis_url, decode_responses=True)
    pipeline = client.pipeline(transaction=False)

    for row in batch_df.collect():
        room_key = f"room:{row.room_id}"
        mapping = {
            "last_updated": row.ts.isoformat() if row.ts is not None else "",
            f"{row.sensor_type}_avg": f"{row.avg_value:.2f}" if row.avg_value is not None else "",
            f"{row.sensor_type}_min": f"{row.min_value:.2f}" if row.min_value is not None else "",
            f"{row.sensor_type}_max": f"{row.max_value:.2f}" if row.max_value is not None else "",
            f"{row.sensor_type}_count": str(int(row.sample_count)) if row.sample_count is not None else "",
            f"{row.sensor_type}_anomaly_flag": str(bool(row.anomaly_flag)),
            f"{row.sensor_type}_anomaly_type": row.anomaly_type or "",
        }

        filtered_mapping = {k: v for k, v in mapping.items() if v != ""}
        if filtered_mapping:
            pipeline.hset(room_key, mapping=filtered_mapping)

        event = {
            "room_id": row.room_id,
            "building_id": row.building_id,
            "sensor_type": row.sensor_type,
            "avg_value": row.avg_value,
            "min_value": row.min_value,
            "max_value": row.max_value,
            "sample_count": int(row.sample_count or 0),
            "anomaly_flag": bool(row.anomaly_flag),
            "anomaly_type": row.anomaly_type,
            "window_start": row.window_start.isoformat() if row.window_start is not None else None,
            "window_end": row.window_end.isoformat() if row.window_end is not None else None,
        }

        pipeline.publish("room-updates", json.dumps(event))

        if row.anomaly_flag:
            alert_payload = {
                "room_id": row.room_id,
                "sensor_type": row.sensor_type,
                "anomaly_type": row.anomaly_type,
                "severity": "CRITICAL",
                "message": f"Anomaly detected for {row.sensor_type} in {row.room_id}",
                "timestamp": row.ts.isoformat() if row.ts is not None else None,
            }
            pipeline.publish("alert-events", json.dumps(alert_payload))

    pipeline.execute()


def ensure_term_context(spark, jdbc_url, jdbc_user, jdbc_password):
    try:
        terms_df = load_reference_table(
            spark,
            jdbc_url,
            jdbc_user,
            jdbc_password,
            "academic_terms",
            select_columns="term_id, term_name, year, start_date, end_date",
        )
    except Exception as exc:
        logger.warning("Unable to load academic terms: %s", exc)
        return

    today = date.today().isoformat()
    active_term = (
        terms_df.filter((col("start_date") <= lit(today)) & (col("end_date") >= lit(today)))
        .limit(1)
        .collect()
    )

    if active_term:
        row = active_term[0]
        logger.info(
            "Current academic term: %s (%s) %s - %s",
            row.term_name,
            row.year,
            row.start_date,
            row.end_date,
        )
    else:
        logger.info("No active academic term found for %s", today)


def main():
    jdbc_url, jdbc_user, jdbc_password = parse_postgres_url(TIMESCALE_URL)
    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    logger.info("Starting Spark Structured Streaming for I2-T3")
    logger.info("Kafka brokers: %s", KAFKA_BROKERS)
    logger.info("Kafka topics: %s", KAFKA_TOPICS)
    logger.info("TimescaleDB JDBC: %s", jdbc_url)
    logger.info("Redis URL: %s", REDIS_URL)

    room_reference = load_reference_table(
        spark,
        jdbc_url,
        jdbc_user,
        jdbc_password,
        "rooms",
        select_columns="room_id, building_id, room_type",
    )

    ensure_term_context(spark, jdbc_url, jdbc_user, jdbc_password)

    schema = build_input_schema()
    aggregation = build_stream(spark, schema, room_reference)

    def foreach_batch(batch_df, batch_id):
        if batch_df.rdd.isEmpty():
            logger.debug("Skipping empty batch %s", batch_id)
            return

        row_count = batch_df.count()
        logger.info("Writing batch %s to TimescaleDB and Redis (%s rows)", batch_id, row_count)
        write_batch_to_timescale(batch_df, jdbc_url, jdbc_user, jdbc_password)
        publish_redis_events(batch_df, REDIS_URL)

    query = (
        aggregation.writeStream.outputMode("update")
        .foreachBatch(foreach_batch)
        .option("checkpointLocation", "/tmp/spark-i2-t3-checkpoint")
        .trigger(processingTime=STREAM_WINDOW)
        .start()
    )

    logger.info("Streaming query started. Waiting for termination...")
    query.awaitTermination()


if __name__ == "__main__":
    main()
