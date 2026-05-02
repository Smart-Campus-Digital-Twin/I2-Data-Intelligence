-- ============================================================================
-- Smart Campus Digital Twin — TimescaleDB Schema Initialization
-- Database: campustwin
-- Created by: I2-T1 — Docker Compose Full Local Dev Stack
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" CASCADE;

-- ============================================================================
-- 1. BUILDINGS TABLE (dimension)
-- ============================================================================
CREATE TABLE IF NOT EXISTS buildings (
  building_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  floors INT NOT NULL DEFAULT 1,
  address TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sample buildings
INSERT INTO buildings (building_id, name, floors, address) VALUES
  ('eng-block-a', 'Engineering Block A', 4, '123 Campus St'),
  ('eng-block-b', 'Engineering Block B', 3, '124 Campus St'),
  ('library', 'Central Library', 5, '125 Campus St')
ON CONFLICT (building_id) DO NOTHING;

-- ============================================================================
-- 2. ROOMS TABLE (dimension)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rooms (
  room_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  building_id TEXT NOT NULL,
  floor INT NOT NULL,
  capacity INT NOT NULL DEFAULT 30,
  room_type TEXT DEFAULT 'classroom', -- classroom|lab|office|hallway|other
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT fk_building FOREIGN KEY (building_id) REFERENCES buildings(building_id) ON DELETE CASCADE
);

-- Create index on building_id for faster queries
CREATE INDEX IF NOT EXISTS idx_rooms_building_id ON rooms(building_id);

-- Sample rooms
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type) VALUES
  ('room-101', 'Lecture Hall 101', 'eng-block-a', 1, 60, 'classroom'),
  ('room-102', 'Lab 102', 'eng-block-a', 1, 30, 'lab'),
  ('room-201', 'Classroom 201', 'eng-block-b', 2, 45, 'classroom'),
  ('room-202', 'Office 202', 'eng-block-b', 2, 20, 'office'),
  ('reading-hall', 'Main Reading Hall', 'library', 1, 120, 'hallway')
ON CONFLICT (room_id) DO NOTHING;

-- ============================================================================
-- 3. SENSOR_READINGS TABLE (hypertable)
-- Partitioned by timestamp for efficient time-series storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS sensor_readings (
  ts TIMESTAMPTZ NOT NULL,
  room_id TEXT NOT NULL,
  building_id TEXT NOT NULL,
  sensor_type TEXT NOT NULL, -- temperature|humidity|occupancy|energy|door
  avg_value FLOAT8 NOT NULL,
  min_value FLOAT8,
  max_value FLOAT8,
  sample_count INT DEFAULT 1,
  anomaly_flag BOOLEAN DEFAULT FALSE,
  anomaly_type TEXT, -- TEMP_HIGH|OVERCAPACITY|ENERGY_SPIKE|null
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable (idempotent - safe to run multiple times)
SELECT create_hypertable('sensor_readings', 'ts', if_not_exists => TRUE, chunk_time_interval => '1 day'::interval);

-- Add compression policy (compress data older than 7 days)
SELECT add_compression_policy('sensor_readings', INTERVAL '7 days', if_not_exists => true);

-- Add data retention policy (keep data for 90 days)
SELECT add_retention_policy('sensor_readings', INTERVAL '90 days', if_not_exists => true);

-- Create composite index for fast room + timestamp queries
CREATE INDEX IF NOT EXISTS idx_sensor_readings_room_ts 
  ON sensor_readings (room_id, ts DESC) WHERE anomaly_flag = FALSE;

CREATE INDEX IF NOT EXISTS idx_sensor_readings_type_ts 
  ON sensor_readings (sensor_type, ts DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_anomaly 
  ON sensor_readings (anomaly_flag, ts DESC) WHERE anomaly_flag = TRUE;

-- ============================================================================
-- 4. ALERTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS alerts (
  alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_id TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
  anomaly_type TEXT, -- TEMP_HIGH|OVERCAPACITY|ENERGY_SPIKE|SENSOR_OFFLINE
  message TEXT,
  triggered_at TIMESTAMPTZ DEFAULT NOW(),
  resolved BOOLEAN DEFAULT FALSE,
  resolved_at TIMESTAMPTZ,
  resolution_note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT fk_room FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
);

-- Create indexes for alert queries
CREATE INDEX IF NOT EXISTS idx_alerts_room_id ON alerts(room_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered_at ON alerts(triggered_at DESC);

-- ============================================================================
-- 5. NODE_STATUS TABLE
-- Tracks ESP32 sensor node connectivity and health
-- ============================================================================
CREATE TABLE IF NOT EXISTS node_status (
  node_id TEXT PRIMARY KEY,
  room_id TEXT NOT NULL,
  last_heartbeat TIMESTAMPTZ,
  is_online BOOLEAN DEFAULT FALSE,
  firmware_version TEXT,
  signal_strength INT, -- RSSI dBm
  uptime_seconds BIGINT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT fk_room FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
);

-- Create indexes for node queries
CREATE INDEX IF NOT EXISTS idx_node_status_room_id ON node_status(room_id);
CREATE INDEX IF NOT EXISTS idx_node_status_online ON node_status(is_online);
CREATE INDEX IF NOT EXISTS idx_node_status_last_heartbeat ON node_status(last_heartbeat DESC);

-- ============================================================================
-- 6. ML_PREDICTIONS TABLE
-- Stores ML model predictions for energy and occupancy forecasting
-- ============================================================================
CREATE TABLE IF NOT EXISTS ml_predictions (
  prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts TIMESTAMPTZ NOT NULL,
  room_id TEXT NOT NULL,
  prediction_type TEXT NOT NULL, -- energy|occupancy
  predicted_value FLOAT8 NOT NULL,
  confidence FLOAT8 NOT NULL,
  model_version TEXT,
  valid_until TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT fk_room FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
);

-- Create indexes for prediction queries
CREATE INDEX IF NOT EXISTS idx_ml_predictions_room_type ON ml_predictions(room_id, prediction_type);
CREATE INDEX IF NOT EXISTS idx_ml_predictions_valid_until ON ml_predictions(valid_until DESC);
CREATE INDEX IF NOT EXISTS idx_ml_predictions_ts ON ml_predictions(ts DESC);

-- ============================================================================
-- 7. VIEWS (for easy data access)
-- ============================================================================

-- Current room status view
CREATE OR REPLACE VIEW v_current_room_status AS
SELECT 
  r.room_id,
  r.name,
  r.building_id,
  r.floor,
  r.capacity,
  b.name as building_name,
  sr.avg_value as temperature,
  sr.min_value as temperature_min,
  sr.max_value as temperature_max,
  sr.anomaly_flag,
  sr.anomaly_type,
  sr.ts as last_reading_ts,
  CASE WHEN sr.anomaly_flag THEN 'CRITICAL' ELSE 'OK' END as status
FROM rooms r
LEFT JOIN buildings b ON r.building_id = b.building_id
LEFT JOIN LATERAL (
  SELECT * FROM sensor_readings 
  WHERE sensor_readings.room_id = r.room_id 
  ORDER BY ts DESC LIMIT 1
) sr ON TRUE;

-- Active alerts view
CREATE OR REPLACE VIEW v_active_alerts AS
SELECT 
  alert_id,
  room_id,
  severity,
  anomaly_type,
  message,
  triggered_at,
  DATE_TRUNC('minute', NOW() - triggered_at) as duration
FROM alerts
WHERE resolved = FALSE
ORDER BY triggered_at DESC;

-- Hourly aggregated readings view
CREATE OR REPLACE VIEW v_hourly_readings AS
SELECT
  room_id,
  TIME_BUCKET('1 hour', ts) as hour,
  sensor_type,
  AVG(avg_value) as value_avg,
  MIN(min_value) as value_min,
  MAX(max_value) as value_max,
  COUNT(*) as sample_count,
  MAX(CASE WHEN anomaly_flag THEN 1 ELSE 0 END) as anomalies_detected
FROM sensor_readings
GROUP BY room_id, hour, sensor_type
ORDER BY hour DESC, room_id;

-- ============================================================================
-- 8. FUNCTIONS
-- ============================================================================

-- Function to get latest reading for a room
CREATE OR REPLACE FUNCTION get_latest_room_reading(p_room_id TEXT)
RETURNS TABLE (
  sensor_type TEXT,
  avg_value FLOAT8,
  min_value FLOAT8,
  max_value FLOAT8,
  ts TIMESTAMPTZ,
  anomaly_flag BOOLEAN
) AS $$
  SELECT sensor_type, avg_value, min_value, max_value, ts, anomaly_flag
  FROM sensor_readings
  WHERE room_id = p_room_id
  ORDER BY ts DESC
  LIMIT 5;
$$ LANGUAGE SQL STABLE;

-- Function to get room readings for a date range
CREATE OR REPLACE FUNCTION get_room_readings_range(
  p_room_id TEXT,
  p_start_ts TIMESTAMPTZ,
  p_end_ts TIMESTAMPTZ,
  p_sensor_type TEXT DEFAULT NULL
)
RETURNS TABLE (
  ts TIMESTAMPTZ,
  sensor_type TEXT,
  avg_value FLOAT8,
  min_value FLOAT8,
  max_value FLOAT8
) AS $$
  SELECT ts, sensor_type, avg_value, min_value, max_value
  FROM sensor_readings
  WHERE room_id = p_room_id
    AND ts BETWEEN p_start_ts AND p_end_ts
    AND (p_sensor_type IS NULL OR sensor_type = p_sensor_type)
  ORDER BY ts ASC;
$$ LANGUAGE SQL STABLE;

-- ============================================================================
-- 9. SAMPLE DATA (for development/testing)
-- ============================================================================

-- Insert sample sensor readings for the last 24 hours
INSERT INTO sensor_readings (ts, room_id, building_id, sensor_type, avg_value, min_value, max_value, sample_count)
SELECT 
  NOW() - (INTERVAL '1 hour' * (row_number() OVER ())) as ts,
  r.room_id,
  r.building_id,
  s.sensor_type,
  CASE 
    WHEN s.sensor_type = 'temperature' THEN 20 + RANDOM() * 5
    WHEN s.sensor_type = 'humidity' THEN 30 + RANDOM() * 40
    WHEN s.sensor_type = 'occupancy' THEN LEAST(r.capacity, RANDOM() * r.capacity * 1.1)::INT
    WHEN s.sensor_type = 'energy' THEN 100 + RANDOM() * 400
    ELSE 0
  END as avg_value,
  CASE 
    WHEN s.sensor_type = 'temperature' THEN 19
    WHEN s.sensor_type = 'humidity' THEN 25
    WHEN s.sensor_type = 'occupancy' THEN 0
    WHEN s.sensor_type = 'energy' THEN 50
    ELSE 0
  END as min_value,
  CASE 
    WHEN s.sensor_type = 'temperature' THEN 25
    WHEN s.sensor_type = 'humidity' THEN 70
    WHEN s.sensor_type = 'occupancy' THEN r.capacity
    WHEN s.sensor_type = 'energy' THEN 500
    ELSE 0
  END as max_value,
  10
FROM rooms r
CROSS JOIN (
  SELECT UNNEST(ARRAY['temperature', 'humidity', 'occupancy', 'energy']) as sensor_type
) s
CROSS JOIN LATERAL generate_series(0, 23) 
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 10. GRANTS (if needed for user permissions)
-- ============================================================================

-- Grant read-only access to API user (if separate user created)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO api_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO api_user;

-- Grant full access for local development
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ctuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ctuser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ctuser;

-- ============================================================================
-- END OF SCHEMA INITIALIZATION
-- ============================================================================
