FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyspark==3.5.0 redis psycopg2-binary

WORKDIR /app
COPY spark_stream_job.py /app/

ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

ENTRYPOINT ["spark-submit", "--packages", "org.postgresql:postgresql:42.6.0", "spark_stream_job.py"]
