# T3 - Spark Streaming Job

## Responsibilities

- Consume sensor events from Kafka topics `sensor.raw` and `sensor.processed`
- Parse JSON sensor payloads
- Perform 5-second tumbling window aggregations
- Detect anomalies
- Persist aggregates to TimescaleDB `sensor_readings`
- Update Redis room state and publish real-time events

## Running the Job

### Local Python run

```bash
cd I2-Data-Intelligence/streaming/spark
python -m pip install -r requirements.txt
python spark_stream_job.py
```

### Docker run

```bash
cd I2-Data-Intelligence
docker compose up -d spark-processor
```

### Script alias

If you want a shorter entrypoint, `streaming/spark/spark_job.py` forwards to the main Spark job.
