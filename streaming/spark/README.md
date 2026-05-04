# T3 - Spark Streaming Job

## Responsibilities

- Consume sensor events from Kafka topics `sensor.raw` and `sensor.processed`
- Parse JSON payloads using the shared sensor schema
- Perform 5-second tumbling window aggregations
- Detect anomalies for temperature, humidity, pressure, vibration, and occupancy
- Persist aggregated analytics to TimescaleDB `sensor_readings`
- Update Redis room state and publish `room-updates` / `alert-events`

## Running the Job

1. Copy the environment template into the I2 root folder:

```bash
cp ../.env.example .env
```

2. Install the Python dependencies:

```bash
cd I2-Data-Intelligence/streaming/spark
python -m pip install -r requirements.txt
```

3. Run the Spark job locally with `spark-submit`:

```bash
spark-submit --packages org.postgresql:postgresql:42.6.0 spark_stream_job.py
```

4. Or run it as a Docker service from the I2 root:

```bash
docker compose up -d spark-processor
```

## Environment variables

The script reads these values from the environment:

- `KAFKA_BROKERS` (default: `kafka:29092`)
- `KAFKA_TOPICS` (default: `sensor.raw,sensor.processed`)
- `TIMESCALE_URL` (default: `postgresql://ctuser:ctpass@timescaledb:5432/campustwin`)
- `REDIS_URL` (default: `redis://redis:6379`)
- `STREAM_WINDOW` (default: `5 seconds`)

## What changed

- Replaced console-only placeholder logic with a working PySpark job
- Added TimescaleDB JDBC writes for `sensor_readings`
- Added Redis state updates for room-level sensor state
- Added anomaly detection and Redis pub/sub alert publishing
- Added a local `requirements.txt` for Python runtime dependencies
