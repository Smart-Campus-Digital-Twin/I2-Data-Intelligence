from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg
from pyspark.sql.types import StructType, StringType, DoubleType, TimestampType

# =============================
# 1. Start Spark Session
# =============================
spark = SparkSession.builder \
    .appName("SmartCampusStreaming") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("✅ Spark Session Started")

# =============================
# 2. Read Stream from Kafka
# =============================
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "sensor-data") \
    .option("startingOffsets", "latest") \
    .load()

print("✅ Connected to Kafka (assumed)")

# =============================
# 3. Define Schema
# =============================
schema = StructType() \
    .add("device_id", StringType()) \
    .add("timestamp", TimestampType()) \
    .add("temperature", DoubleType())

# =============================
# 4. Parse JSON Data
# =============================
parsed = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

print("✅ JSON Parsing Ready")

# =============================
# 5. Aggregation (1-min avg)
# =============================
agg = parsed.groupBy(
    window(col("timestamp"), "1 minute")
).agg(avg("temperature").alias("avg_temp"))

print("✅ Aggregation Logic Ready")

# =============================
# 6. Anomaly Detection
# =============================
anomalies = parsed.filter(col("temperature") > 50)

print("✅ Anomaly Detection Ready")

# =============================
# 7. TEMP Output (Console)
# =============================
agg_query = agg.writeStream \
    .outputMode("update") \
    .format("console") \
    .option("truncate", False) \
    .start()

anomaly_query = anomalies.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()

print("🚀 Streaming Started...")

# =============================
# 8. Keep Running
# =============================
spark.streams.awaitAnyTermination()