import os
import sys
import time
import json
import pandas as pd
from kafka import KafkaProducer

class CustomJSONEncoder(json.JSONEncoder):
    """Handles serialization of pandas Timestamps and missing values."""
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if pd.isna(obj):
            return None
        return super().default(obj)

def create_kafka_producer(brokers=['localhost:9092']):
    """Initialize Kafka Producer with JSON serialization."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=brokers,
            value_serializer=lambda v: json.dumps(v, cls=CustomJSONEncoder).encode('utf-8'),
            key_serializer=lambda v: str(v).encode('utf-8')
        )
        print(f"[OK] Successfully connected to Kafka brokers: {brokers}")
        return producer
    except Exception as e:
        print(f"[ERROR] Failed to connect to Kafka: {e}")
        return None

def stream_synthetic_data(producer, file_path, topic, speed_multiplier=10.0):
    """
    Reads synthetic CSV and pushes rows to Kafka to simulate a live data feed.
    `speed_multiplier` controls how fast records are published.
    """
    if not os.path.exists(file_path):
        print(f"Error: Could not find '{file_path}'. Run synthetic_generator.py first.")
        return

    print(f"Starting to stream data from {os.path.basename(file_path)} to topic '{topic}'...")
    df = pd.read_csv(file_path)
    
    records_sent = 0
    try:
        for index, row in df.iterrows():
            payload = row.to_dict()
            key = payload.get('timestamp', f'msg_{index}')
            
            # Publish event asynchronously
            producer.send(topic, key=key, value=payload)
            records_sent += 1
            
            if records_sent % 50 == 0:
                print(f" > Published {records_sent} events to {topic}...")
                
            # Delay to simulate continuous stream instead of immediate batch upload
            time.sleep(1.0 / speed_multiplier)
            
    except KeyboardInterrupt:
        print("\n[STOP] Data stream manually interrupted by operator.")
    finally:
        # Ensure all queued messages are sent before terminating
        producer.flush()
        print(f"Stream complete or interrupted. Total '{topic}' records pushed: {records_sent}")

if __name__ == "__main__":
    if not os.path.exists('data/synthetic'):
        print("Error: Please run this script from the root of I2-Data-Intelligence/")
        sys.exit(1)
        
    kafka_broker = os.getenv('KAFKA_BROKER', 'localhost:9092')
    producer = create_kafka_producer([kafka_broker])
    
    if producer:
        # Stream both datasets concurrently into different topics for modularity
        # Using speed_multiplier=20 to push the whole dataset in ~30 seconds for the demo
        stream_synthetic_data(
            producer, 
            file_path='data/synthetic/occupancy_energy.csv', 
            topic='sensor.campus.energy', 
            speed_multiplier=50.0
        )
        stream_synthetic_data(
            producer,
            file_path='data/synthetic/equipment_telemetry.csv',
            topic='sensor.campus.telemetry',
            speed_multiplier=50.0
        )
    else:
        print("\nHint: Is Docker running? Start the infrastructure using: docker-compose up -d")
