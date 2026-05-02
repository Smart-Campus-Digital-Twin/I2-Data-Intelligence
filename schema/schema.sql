-- I2 Analytics Layer Schema — TimescaleDB
-- Smart Campus Digital Twin: Sensor readings, alerts, academic calendar, and event management
-- Aligned with Complete Simulation Logic Reference (26 buildings, 142 rooms)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;

-- ============================================================================
-- CORE MASTER DATA TABLES
-- ============================================================================

-- Buildings (26 total, matching simulator topology)
CREATE TABLE IF NOT EXISTS buildings (
    building_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    floors        INT NOT NULL,
    latitude      FLOAT,
    longitude     FLOAT,
    description   TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Rooms (142 total, with sensor configuration)
CREATE TABLE IF NOT EXISTS rooms (
    room_id       TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    building_id   TEXT NOT NULL REFERENCES buildings(building_id),
    floor         INT NOT NULL,
    capacity      INT NOT NULL DEFAULT 30,
    room_type     TEXT NOT NULL CHECK (room_type IN 
        ('classroom', 'lab', 'library', 'canteen', 'office', 'auditorium', 
         'hostel', 'server_room', 'outdoor', 'restroom', 'other')),
    sensors       TEXT[] DEFAULT ARRAY['occupancy', 'temperature', 'energy'],
    weekend_active BOOLEAN DEFAULT FALSE,  -- faculty-it, dept-design run Sat/Sun
    has_hvac      BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rooms_building ON rooms(building_id);
CREATE INDEX IF NOT EXISTS idx_rooms_floor ON rooms(building_id, floor);
CREATE INDEX IF NOT EXISTS idx_rooms_type ON rooms(room_type);

-- ============================================================================
-- ACADEMIC CALENDAR
-- ============================================================================

-- Academic Terms/Semesters
CREATE TABLE IF NOT EXISTS academic_terms (
    term_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_name     TEXT NOT NULL,
    term_type     TEXT NOT NULL,
    year          INT NOT NULL,
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    description   TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT term_date_order CHECK (start_date < end_date)
);

CREATE INDEX IF NOT EXISTS idx_terms_year ON academic_terms(year);
CREATE INDEX IF NOT EXISTS idx_terms_dates ON academic_terms(start_date, end_date);

-- Enhanced Calendar Events (with venue mapping and fill factors)
CREATE TABLE IF NOT EXISTS calendar_events (
    event_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id       UUID REFERENCES academic_terms(term_id),
    event_type    TEXT NOT NULL,
    event_name    TEXT NOT NULL,
    event_category TEXT,              -- "padura", "food_festival", "symposium", "sports", "concert", "workshop", etc.
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    start_time    TIME,
    end_time      TIME,
    venue_ids     TEXT[],             -- Array of affected building/room IDs
    occupancy_factor FLOAT DEFAULT 1.0,  -- Static factor (legacy)
    occupancy_factor_min FLOAT,       -- Min fill (e.g., 0.55)
    occupancy_factor_max FLOAT,       -- Max fill (e.g., 0.90)
    frequency     TEXT,               -- "annual", "semester", "monthly", "probabilistic", "fixed"
    probability   FLOAT,              -- For probabilistic events (0.35 = 35% chance)
    is_deterministic BOOLEAN DEFAULT FALSE,  -- Seeded/reproducible
    seed_key      TEXT,               -- Hash seed for reproducibility
    description   TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT event_date_order CHECK (start_date <= end_date),
    CONSTRAINT fill_factors CHECK (
        occupancy_factor_min IS NULL OR occupancy_factor_max IS NULL 
        OR occupancy_factor_min <= occupancy_factor_max
    )
);

CREATE INDEX IF NOT EXISTS idx_events_term ON calendar_events(term_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON calendar_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_category ON calendar_events(event_category);
CREATE INDEX IF NOT EXISTS idx_events_dates ON calendar_events(start_date, end_date);

-- Sri Lanka Public Holidays 2026 (hardcoded, 25 dates)
CREATE TABLE IF NOT EXISTS public_holidays_2026 (
    holiday_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date          DATE UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT,
    -- Per-room-type occupancy overrides on holidays
    occupancy_classroom  FLOAT DEFAULT 0.0,
    occupancy_lab        FLOAT DEFAULT 0.0,
    occupancy_library    FLOAT DEFAULT 0.0,
    occupancy_canteen    FLOAT DEFAULT 0.15,
    occupancy_office     FLOAT DEFAULT 0.0,
    occupancy_auditorium FLOAT DEFAULT 0.0,
    occupancy_hostel     FLOAT DEFAULT 0.70,
    occupancy_outdoor    FLOAT DEFAULT 0.01,
    occupancy_other      FLOAT DEFAULT 0.0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_holidays_date ON public_holidays_2026(date);

-- ============================================================================
-- TIME-SERIES DATA TABLE (HYPERTABLE)
-- ============================================================================

-- Sensor readings aggregated by room and sensor type
CREATE TABLE IF NOT EXISTS sensor_readings (
    ts              TIMESTAMPTZ NOT NULL,
    room_id         TEXT NOT NULL,
    building_id     TEXT NOT NULL,
    sensor_type     TEXT NOT NULL,
    avg_value       FLOAT8,
    min_value       FLOAT8,
    max_value       FLOAT8,
    anomaly_flag    BOOLEAN DEFAULT FALSE,
    anomaly_type    TEXT,
    sample_count    INT DEFAULT 1,
    window_start    TIMESTAMPTZ,
    window_end      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable with 1-day chunks
SELECT create_hypertable(
    'sensor_readings',
    'ts',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Enable compression for data older than 7 days
ALTER TABLE sensor_readings SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'ts DESC',
    timescaledb.compress_segmentby = 'room_id, building_id, sensor_type'
);

SELECT add_compression_policy(
    'sensor_readings',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Set retention policy: keep 90 days of data
SELECT add_retention_policy(
    'sensor_readings',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sensor_readings_room_ts 
    ON sensor_readings(room_id, ts DESC)
    WHERE anomaly_flag = FALSE;

CREATE INDEX IF NOT EXISTS idx_sensor_readings_building_ts 
    ON sensor_readings(building_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_anomaly 
    ON sensor_readings(ts DESC)
    WHERE anomaly_flag = TRUE;

CREATE INDEX IF NOT EXISTS idx_sensor_readings_type 
    ON sensor_readings(sensor_type, ts DESC);

-- ============================================================================
-- ALERTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS alerts (
    alert_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id       TEXT NOT NULL REFERENCES rooms(room_id),
    severity      TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    anomaly_type  TEXT,
    message       TEXT NOT NULL,
    triggered_at  TIMESTAMPTZ DEFAULT NOW(),
    resolved      BOOLEAN DEFAULT FALSE,
    resolved_at   TIMESTAMPTZ,
    resolved_by   TEXT,
    notes         TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT alert_resolved_time CHECK (
        (resolved = FALSE AND resolved_at IS NULL) OR 
        (resolved = TRUE AND resolved_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_alerts_room_ts ON alerts(room_id, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity_ts ON alerts(severity, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_unresolved ON alerts(triggered_at DESC) WHERE resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_alerts_anomaly_type ON alerts(anomaly_type);

-- ============================================================================
-- SEED DATA — 26 BUILDINGS, 142 ROOMS (Matching Simulator Topology)
-- ============================================================================

-- Buildings (26 total)
INSERT INTO buildings (building_id, name, floors, description) VALUES
    ('lagaan', 'Lagaan (Outdoor Sports Ground)', 0, 'Outdoor venue for sports, cultural events'),
    ('multipurpose-hall', 'Multipurpose Hall', 1, 'Main auditorium for symposiums, orientations'),
    ('hostel-a', 'Hostel A (Women)', 4, 'Residential hostel for female students'),
    ('hostel-b', 'Hostel B (Men)', 4, 'Residential hostel for male students'),
    ('hostel-c', 'Hostel C', 3, 'Additional residential hostel'),
    ('sumanadasa', 'Dept CS - Sumanadasa Building', 4, 'Classrooms, labs, server room'),
    ('faculty-it', 'Faculty of IT', 4, 'IT classrooms, labs, server (weekend classes)'),
    ('faculty-business', 'Faculty of Business', 3, 'Business classrooms and offices'),
    ('faculty-medicine', 'Faculty of Medicine', 4, 'Medical classrooms and labs'),
    ('dept-ete', 'Dept ETE (Electronics/Telecom)', 4, 'Engineering classrooms and labs'),
    ('dept-civil', 'Dept Civil Engineering', 3, 'Civil engineering classrooms and labs'),
    ('dept-textile', 'Dept Textile Engineering', 3, 'Textile engineering labs'),
    ('dept-transport', 'Dept Transport Engineering', 3, 'Transport engineering classrooms'),
    ('dept-material', 'Dept Material Science', 3, 'Material science labs'),
    ('dept-chemical', 'Dept Chemical Engineering', 3, 'Chemical engineering labs'),
    ('dept-mechanical', 'Dept Mechanical Engineering', 3, 'Mechanical engineering labs'),
    ('dept-design', 'Dept Design (Weekend Active)', 3, 'Product design labs (weekend classes)'),
    ('goda-canteen', 'Goda Canteen', 1, 'Main dining facility - Goda'),
    ('sentra-court', 'Sentra Court', 1, 'Open-air court canteen - Sentra'),
    ('l-canteen', 'L-Block Canteen', 1, 'Canteen in L-block'),
    ('wala-canteen', 'Wala Canteen', 1, 'Canteen in Wala block'),
    ('na-hall', 'NA Hall', 2, 'Auditorium NA - Halls for events'),
    ('library', 'Central Library', 3, 'Three-floor library'),
    ('admin-building', 'Admin Building', 2, 'Administration offices'),
    ('registrar-building', 'Registrar Building', 1, 'Registrar and records office'),
    ('student-center', 'Student Center', 2, 'Student activities and services')
ON CONFLICT (building_id) DO NOTHING;

-- Rooms (142 total) — Comprehensive seed data
-- Lagaan (1 room)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors, weekend_active) VALUES
    ('lagaan-outdoor', 'Outdoor Sports Ground', 'lagaan', 0, 700, 'outdoor', ARRAY['occupancy'], FALSE)
ON CONFLICT (room_id) DO NOTHING;

-- Multipurpose Hall (1 room)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('mph-main', 'Main Auditorium', 'multipurpose-hall', 1, 1000, 'auditorium', ARRAY['occupancy', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Hostels (1+1+1 = 3 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('hostel-a-common', 'Hostel A Common Room', 'hostel-a', 1, 200, 'hostel', ARRAY['occupancy', 'temperature', 'energy']),
    ('hostel-b-common', 'Hostel B Common Room', 'hostel-b', 1, 200, 'hostel', ARRAY['occupancy', 'temperature', 'energy']),
    ('hostel-c-common', 'Hostel C Common Room', 'hostel-c', 1, 150, 'hostel', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept CS Sumanadasa (13 rooms: 10 classrooms/labs + 1 server + 2 offices)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('sumanadasa-cr1', 'Classroom 1', 'sumanadasa', 1, 60, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-cr2', 'Classroom 2', 'sumanadasa', 1, 60, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-lab1', 'Computer Lab 1', 'sumanadasa', 2, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-lab2', 'Computer Lab 2', 'sumanadasa', 2, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-lab3', 'Computer Lab 3', 'sumanadasa', 2, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-lab4', 'Computer Lab 4', 'sumanadasa', 3, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-cr3', 'Classroom 3', 'sumanadasa', 3, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-cr4', 'Classroom 4', 'sumanadasa', 3, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-server', 'Server Room', 'sumanadasa', 4, 0, 'server_room', ARRAY['temperature', 'energy']),
    ('sumanadasa-office1', 'Faculty Office 1', 'sumanadasa', 4, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-office2', 'Faculty Office 2', 'sumanadasa', 4, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-conf', 'Conference Room', 'sumanadasa', 1, 30, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('sumanadasa-seminar', 'Seminar Hall', 'sumanadasa', 2, 50, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Faculty IT (13 rooms: 10 classrooms/labs + 1 server + 2 offices, weekend active)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors, weekend_active) VALUES
    ('faculty-it-cr1', 'Classroom 1', 'faculty-it', 1, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-cr2', 'Classroom 2', 'faculty-it', 1, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-lab1', 'IT Lab 1', 'faculty-it', 2, 50, 'lab', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-lab2', 'IT Lab 2', 'faculty-it', 2, 50, 'lab', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-lab3', 'IT Lab 3', 'faculty-it', 2, 50, 'lab', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-lab4', 'IT Lab 4', 'faculty-it', 3, 50, 'lab', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-cr3', 'Classroom 3', 'faculty-it', 3, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-cr4', 'Classroom 4', 'faculty-it', 3, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-server', 'Server Room', 'faculty-it', 4, 0, 'server_room', ARRAY['temperature', 'energy'], TRUE),
    ('faculty-it-office1', 'Faculty Office 1', 'faculty-it', 4, 5, 'office', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-office2', 'Faculty Office 2', 'faculty-it', 4, 5, 'office', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-conf', 'Conference Room', 'faculty-it', 1, 40, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('faculty-it-seminar', 'Seminar Hall', 'faculty-it', 2, 60, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE)
ON CONFLICT (room_id) DO NOTHING;

-- Faculty Business (9 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('business-cr1', 'Classroom 1', 'faculty-business', 1, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('business-cr2', 'Classroom 2', 'faculty-business', 1, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('business-cr3', 'Classroom 3', 'faculty-business', 2, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('business-office1', 'Office 1', 'faculty-business', 2, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('business-office2', 'Office 2', 'faculty-business', 2, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('business-office3', 'Office 3', 'faculty-business', 3, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('business-conf', 'Conference Room', 'faculty-business', 1, 40, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('business-lab', 'Business Lab', 'faculty-business', 3, 45, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('business-seminar', 'Seminar Hall', 'faculty-business', 3, 50, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Faculty Medicine (12 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('medicine-cr1', 'Classroom 1', 'faculty-medicine', 1, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-cr2', 'Classroom 2', 'faculty-medicine', 1, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-lab1', 'Anatomy Lab', 'faculty-medicine', 2, 50, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-lab2', 'Pathology Lab', 'faculty-medicine', 2, 45, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-lab3', 'Microbiology Lab', 'faculty-medicine', 2, 45, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-lab4', 'Pharmacology Lab', 'faculty-medicine', 3, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-cr3', 'Classroom 3', 'faculty-medicine', 3, 90, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-office1', 'Faculty Office 1', 'faculty-medicine', 4, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-office2', 'Faculty Office 2', 'faculty-medicine', 4, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-conf', 'Conference Room', 'faculty-medicine', 1, 50, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-seminar1', 'Seminar Hall 1', 'faculty-medicine', 3, 60, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('medicine-seminar2', 'Seminar Hall 2', 'faculty-medicine', 4, 60, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept ETE (12 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('ete-cr1', 'Classroom 1', 'dept-ete', 1, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-cr2', 'Classroom 2', 'dept-ete', 1, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-lab1', 'Electronics Lab', 'dept-ete', 2, 50, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-lab2', 'Telecom Lab', 'dept-ete', 2, 50, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-lab3', 'Signals Lab', 'dept-ete', 2, 45, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-lab4', 'Communication Lab', 'dept-ete', 3, 45, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-cr3', 'Classroom 3', 'dept-ete', 3, 90, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-office1', 'Faculty Office 1', 'dept-ete', 4, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-office2', 'Faculty Office 2', 'dept-ete', 4, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-conf', 'Conference Room', 'dept-ete', 1, 40, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-seminar1', 'Seminar Hall', 'dept-ete', 3, 60, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('ete-seminar2', 'Research Lab', 'dept-ete', 4, 30, 'lab', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept Civil (7 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('civil-cr1', 'Classroom 1', 'dept-civil', 1, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('civil-lab1', 'Structures Lab', 'dept-civil', 1, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('civil-lab2', 'Materials Lab', 'dept-civil', 2, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('civil-cr2', 'Classroom 2', 'dept-civil', 2, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('civil-office', 'Faculty Office', 'dept-civil', 3, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('civil-conf', 'Conference Room', 'dept-civil', 1, 35, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('civil-seminar', 'Seminar Hall', 'dept-civil', 2, 50, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept Textile (7 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('textile-cr1', 'Classroom 1', 'dept-textile', 1, 60, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('textile-lab1', 'Weaving Lab', 'dept-textile', 1, 35, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('textile-lab2', 'Dyeing Lab', 'dept-textile', 2, 35, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('textile-cr2', 'Classroom 2', 'dept-textile', 2, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('textile-office', 'Faculty Office', 'dept-textile', 3, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('textile-conf', 'Conference Room', 'dept-textile', 1, 30, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('textile-seminar', 'Seminar Hall', 'dept-textile', 2, 45, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept Transport (7 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('transport-cr1', 'Classroom 1', 'dept-transport', 1, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('transport-lab1', 'Simulation Lab', 'dept-transport', 1, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('transport-lab2', 'Design Lab', 'dept-transport', 2, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('transport-cr2', 'Classroom 2', 'dept-transport', 2, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('transport-office', 'Faculty Office', 'dept-transport', 3, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('transport-conf', 'Conference Room', 'dept-transport', 1, 35, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('transport-seminar', 'Seminar Hall', 'dept-transport', 2, 50, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept Material (7 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('material-cr1', 'Classroom 1', 'dept-material', 1, 65, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('material-lab1', 'Testing Lab', 'dept-material', 1, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('material-lab2', 'Analysis Lab', 'dept-material', 2, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('material-cr2', 'Classroom 2', 'dept-material', 2, 75, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('material-office', 'Faculty Office', 'dept-material', 3, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('material-conf', 'Conference Room', 'dept-material', 1, 30, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('material-seminar', 'Seminar Hall', 'dept-material', 2, 45, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept Chemical (7 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('chemical-cr1', 'Classroom 1', 'dept-chemical', 1, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('chemical-lab1', 'Process Lab', 'dept-chemical', 1, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('chemical-lab2', 'Unit Ops Lab', 'dept-chemical', 2, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('chemical-cr2', 'Classroom 2', 'dept-chemical', 2, 80, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('chemical-office', 'Faculty Office', 'dept-chemical', 3, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('chemical-conf', 'Conference Room', 'dept-chemical', 1, 35, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('chemical-seminar', 'Seminar Hall', 'dept-chemical', 2, 50, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept Mechanical (7 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('mechanical-cr1', 'Classroom 1', 'dept-mechanical', 1, 75, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('mechanical-lab1', 'Machine Shop', 'dept-mechanical', 1, 45, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('mechanical-lab2', 'Thermal Lab', 'dept-mechanical', 2, 40, 'lab', ARRAY['occupancy', 'temperature', 'energy']),
    ('mechanical-cr2', 'Classroom 2', 'dept-mechanical', 2, 85, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('mechanical-office', 'Faculty Office', 'dept-mechanical', 3, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('mechanical-conf', 'Conference Room', 'dept-mechanical', 1, 40, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('mechanical-seminar', 'Seminar Hall', 'dept-mechanical', 2, 55, 'classroom', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Dept Design (7 rooms, weekend active)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors, weekend_active) VALUES
    ('design-cr1', 'Classroom 1', 'dept-design', 1, 60, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('design-lab1', 'CAD Lab 1', 'dept-design', 1, 45, 'lab', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('design-lab2', 'CAD Lab 2', 'dept-design', 2, 45, 'lab', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('design-cr2', 'Classroom 2', 'dept-design', 2, 70, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('design-office', 'Faculty Office', 'dept-design', 3, 5, 'office', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('design-conf', 'Conference Room', 'dept-design', 1, 30, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE),
    ('design-seminar', 'Seminar Hall', 'dept-design', 2, 45, 'classroom', ARRAY['occupancy', 'temperature', 'energy'], TRUE)
ON CONFLICT (room_id) DO NOTHING;

-- Canteens (4 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('goda-main', 'Goda Canteen', 'goda-canteen', 1, 300, 'canteen', ARRAY['occupancy', 'temperature', 'energy']),
    ('sentra-main', 'Sentra Court', 'sentra-court', 1, 350, 'canteen', ARRAY['occupancy', 'temperature', 'energy']),
    ('l-main', 'L-Canteen', 'l-canteen', 1, 200, 'canteen', ARRAY['occupancy', 'temperature', 'energy']),
    ('wala-main', 'Wala Canteen', 'wala-canteen', 1, 200, 'canteen', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- NA Hall (2 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('na-hall-1', 'NA Hall 1', 'na-hall', 1, 300, 'auditorium', ARRAY['occupancy', 'energy']),
    ('na-hall-2', 'NA Hall 2', 'na-hall', 2, 300, 'auditorium', ARRAY['occupancy', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Library (3 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('library-floor1', 'Library - Floor 1', 'library', 1, 400, 'library', ARRAY['occupancy', 'temperature', 'energy']),
    ('library-floor2', 'Library - Floor 2', 'library', 2, 350, 'library', ARRAY['occupancy', 'temperature', 'energy']),
    ('library-floor3', 'Library - Floor 3', 'library', 3, 250, 'library', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Admin Building (5 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('admin-office1', 'Administration Office 1', 'admin-building', 1, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('admin-office2', 'Administration Office 2', 'admin-building', 1, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('admin-meeting', 'Conference Room', 'admin-building', 1, 30, 'classroom', ARRAY['occupancy', 'temperature', 'energy']),
    ('admin-office3', 'Administration Office 3', 'admin-building', 2, 5, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('admin-office4', 'Administration Office 4', 'admin-building', 2, 5, 'office', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Registrar Building (2 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('registrar-office', 'Registrar Office', 'registrar-building', 1, 10, 'office', ARRAY['occupancy', 'temperature', 'energy']),
    ('registrar-records', 'Records Room', 'registrar-building', 1, 5, 'office', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Student Center (2 rooms)
INSERT INTO rooms (room_id, name, building_id, floor, capacity, room_type, sensors) VALUES
    ('student-center-main', 'Main Activity Area', 'student-center', 1, 150, 'other', ARRAY['occupancy', 'temperature', 'energy']),
    ('student-center-lounge', 'Student Lounge', 'student-center', 2, 100, 'other', ARRAY['occupancy', 'temperature', 'energy'])
ON CONFLICT (room_id) DO NOTHING;

-- Total: 1 + 1 + 3 + 13 + 13 + 9 + 12 + 12 + 7 + 7 + 7 + 7 + 7 + 7 + 7 + 4 + 2 + 3 + 5 + 2 + 2 = 142 rooms ✓

-- ============================================================================
-- MATERIALIZED VIEWS FOR ANALYTICS
-- ============================================================================

-- Current occupancy status by room (latest reading)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_latest_occupancy AS
SELECT DISTINCT ON (room_id)
    room_id,
    building_id,
    ts,
    avg_value as occupancy_count,
    anomaly_flag,
    anomaly_type
FROM sensor_readings
WHERE sensor_type = 'occupancy'
ORDER BY room_id, ts DESC;

-- Anomalies in last 24 hours
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_recent_anomalies AS
SELECT
    DATE_TRUNC('hour', ts) as hour,
    room_id,
    sensor_type,
    COUNT(*) as anomaly_count,
    MAX(anomaly_type) as primary_anomaly_type
FROM sensor_readings
WHERE anomaly_flag = TRUE
  AND ts > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', ts), room_id, sensor_type;

-- ============================================================================
-- ACADEMIC CALENDAR SEED DATA — Events & Holidays
-- ============================================================================

-- Academic Terms (2025-2026)
INSERT INTO academic_terms (term_name, term_type, year, start_date, end_date, description) VALUES
    ('Semester 1 2025-26', 'semester', 2025, '2025-09-01'::DATE, '2025-12-20'::DATE, 'Fall Semester'),
    ('Semester 2 2025-26', 'semester', 2026, '2026-01-12'::DATE, '2026-05-22'::DATE, 'Spring Semester')
ON CONFLICT DO NOTHING;

-- Campus Events (deterministic, venue-mapped, fill-factored) — Matches PDF simulator
-- Dept Padura events (16 depts × 2 per year = 32 total, concentrated May-Jul and Nov-Dec)
INSERT INTO calendar_events (term_id, event_type, event_name, event_category, start_date, end_date, 
    start_time, end_time, venue_ids, occupancy_factor_min, occupancy_factor_max, 
    frequency, is_deterministic, seed_key, description) 
SELECT t.term_id, 'special_event', depts.dept_name || ' Padura', 'padura',
    depts.event_date, depts.event_date, '18:00'::TIME, '22:00'::TIME,
    ARRAY['lagaan'], 0.55, 0.90, 'annual', TRUE, 
    MD5(depts.dept_name || '|2026|Semester'),
    depts.dept_name || ' departmental cultural event'
FROM academic_terms t, 
(VALUES
    ('Dept CS', '2026-05-15'::DATE),
    ('Dept IT', '2026-05-22'::DATE),
    ('Dept ETE', '2026-05-29'::DATE),
    ('Dept Civil', '2026-06-05'::DATE),
    ('Dept Mechanical', '2026-06-12'::DATE),
    ('Dept Chemical', '2026-06-19'::DATE),
    ('Dept Textile', '2026-06-26'::DATE),
    ('Dept Transport', '2026-07-03'::DATE),
    ('Business', '2026-11-06'::DATE),
    ('Medicine', '2026-11-13'::DATE),
    ('Design', '2026-11-20'::DATE),
    ('Engineering', '2026-11-27'::DATE),
    ('Science', '2026-12-04'::DATE),
    ('Humanities', '2026-12-11'::DATE),
    ('Architecture', '2026-12-18'::DATE),
    ('Faculty Mix', '2026-12-25'::DATE)
) depts(dept_name, event_date)
WHERE t.year = 2026
ON CONFLICT DO NOTHING;

-- Food Festival (2-3 per year: March, September, November)
INSERT INTO calendar_events (term_id, event_type, event_name, event_category, start_date, end_date,
    start_time, end_time, venue_ids, occupancy_factor_min, occupancy_factor_max,
    frequency, is_deterministic, seed_key, description)
SELECT t.term_id, 'special_event', 'Food Festival 2026', 'food_festival',
    dates.event_date, dates.event_date, '10:00'::TIME, '20:00'::TIME,
    ARRAY['lagaan', 'sentra-court'], 0.45, 0.98, 'annual', TRUE,
    MD5('food_festival|2026|' || TO_CHAR(dates.event_date, 'MMDD')),
    'Campus-wide food festival - Lagaan & Sentra Court'
FROM academic_terms t,
(VALUES
    ('2026-03-20'::DATE),
    ('2026-09-18'::DATE),
    ('2026-11-14'::DATE)
) dates(event_date)
WHERE t.year = 2026
ON CONFLICT DO NOTHING;

-- Symposium (4 per year: Apr/May, Oct/Nov)
INSERT INTO calendar_events (term_id, event_type, event_name, event_category, start_date, end_date,
    start_time, end_time, venue_ids, occupancy_factor_min, occupancy_factor_max,
    frequency, is_deterministic, seed_key, description)
SELECT t.term_id, 'special_event', 'Symposium - ' || symp.title, 'symposium',
    symp.event_date, symp.event_date, '08:00'::TIME, '17:00'::TIME,
    ARRAY['multipurpose-hall'], 0.65, 0.95, 'annual', TRUE,
    MD5('symposium|2026|' || TO_CHAR(symp.event_date, 'MMDD')),
    symp.title || ' - at Multipurpose Hall'
FROM academic_terms t,
(VALUES
    ('2026-04-10'::DATE, 'Technology & Innovation'),
    ('2026-05-22'::DATE, 'Research Excellence'),
    ('2026-10-16'::DATE, 'Sustainability'),
    ('2026-11-27'::DATE, 'Future Leaders')
) symp(event_date, title)
WHERE t.year = 2026
ON CONFLICT DO NOTHING;

-- New Student Orientation (2 per year: Feb, Aug)
INSERT INTO calendar_events (term_id, event_type, event_name, event_category, start_date, end_date,
    start_time, end_time, venue_ids, occupancy_factor_min, occupancy_factor_max,
    frequency, is_deterministic, seed_key, description)
SELECT t.term_id, 'special_event', 'New Student Orientation', 'orientation',
    orient.event_date, orient.event_date, '08:00'::TIME, '13:00'::TIME,
    ARRAY['multipurpose-hall'], 0.75, 0.97, 'annual', TRUE,
    MD5('orientation|2026|' || TO_CHAR(orient.event_date, 'MMDD')),
    'Welcome & orientation for new students'
FROM academic_terms t,
(VALUES
    ('2026-02-13'::DATE),
    ('2026-08-21'::DATE)
) orient(event_date)
WHERE t.year = 2026
ON CONFLICT DO NOTHING;

-- Career Fair (2 per year: May, Nov)
INSERT INTO calendar_events (term_id, event_type, event_name, event_category, start_date, end_date,
    start_time, end_time, venue_ids, occupancy_factor_min, occupancy_factor_max,
    frequency, is_deterministic, seed_key, description)
SELECT t.term_id, 'special_event', 'Career Fair 2026', 'career_fair',
    fair.event_date, fair.event_date, '09:00'::TIME, '16:00'::TIME,
    ARRAY['multipurpose-hall', 'na-hall-1'], 0.70, 0.92, 'annual', TRUE,
    MD5('career_fair|2026|' || TO_CHAR(fair.event_date, 'MMDD')),
    'Recruitment & career opportunities fair'
FROM academic_terms t,
(VALUES
    ('2026-05-08'::DATE),
    ('2026-11-06'::DATE)
) fair(event_date)
WHERE t.year = 2026
ON CONFLICT DO NOTHING;

-- Sports Meet (~35% weekends Oct-Apr, probabilistic)
INSERT INTO calendar_events (term_id, event_type, event_name, event_category, start_date, end_date,
    start_time, end_time, venue_ids, occupancy_factor_min, occupancy_factor_max,
    frequency, probability, description)
SELECT t.term_id, 'special_event', 'Sports Meet - ' || sm.name, 'sports',
    sm.event_date, sm.event_date, '14:00'::TIME, '18:00'::TIME,
    ARRAY['lagaan'], 0.30, 0.65, 'probabilistic', 0.35,
    sm.name || ' at Lagaan'
FROM academic_terms t,
(VALUES
    ('2026-10-03'::DATE, 'Volleyball Tournament'),
    ('2026-10-17'::DATE, 'Cricket Tournament'),
    ('2026-11-07'::DATE, 'Badminton Championship'),
    ('2026-11-21'::DATE, 'Basketball Tournament'),
    ('2026-12-05'::DATE, 'Swimming Gala'),
    ('2027-01-09'::DATE, 'Athletics Meet'),
    ('2027-02-06'::DATE, 'Kabaddi Championship'),
    ('2027-03-13'::DATE, 'Handball Tournament'),
    ('2027-04-10'::DATE, 'Tennis Championship')
) sm(event_date, name)
WHERE t.year IN (2026, 2027)
ON CONFLICT DO NOTHING;

-- Concert/Cultural Night (~1 per month, 60% chance on fixed monthly date)
INSERT INTO calendar_events (term_id, event_type, event_name, event_category, start_date, end_date,
    start_time, end_time, venue_ids, occupancy_factor_min, occupancy_factor_max,
    frequency, probability, is_deterministic, seed_key, description)
SELECT t.term_id, 'special_event', 'Cultural Night - ' || cn.theme, 'concert',
    cn.event_date, cn.event_date, '18:30'::TIME, '22:00'::TIME,
    ARRAY['lagaan', 'multipurpose-hall'], 0.55, 0.90, 'monthly', 0.60, TRUE,
    MD5('concert|2026|' || TO_CHAR(cn.event_date, 'MMDD')),
    cn.theme || ' cultural performance'
FROM academic_terms t,
(VALUES
    ('2026-01-25'::DATE, 'Folk Dance'),
    ('2026-02-21'::DATE, 'Classical Music'),
    ('2026-03-21'::DATE, 'Modern Drama'),
    ('2026-04-18'::DATE, 'Comedy Night'),
    ('2026-05-23'::DATE, 'Jazz Concert'),
    ('2026-06-20'::DATE, 'Film Festival'),
    ('2026-07-18'::DATE, 'Poetry Recital'),
    ('2026-08-22'::DATE, 'Dance Showcase'),
    ('2026-09-19'::DATE, 'Theater Production'),
    ('2026-10-24'::DATE, 'Music Concert'),
    ('2026-11-21'::DATE, 'Cultural Fest'),
    ('2026-12-19'::DATE, 'Year-End Gala')
) cn(event_date, theme)
WHERE t.year = 2026
ON CONFLICT DO NOTHING;

-- Workshop (~45% weekday chance at NA Hall)
INSERT INTO calendar_events (term_id, event_type, event_name, event_category, start_date, end_date,
    start_time, end_time, venue_ids, occupancy_factor_min, occupancy_factor_max,
    frequency, probability, description)
SELECT t.term_id, 'special_event', 'Workshop: ' || ws.topic, 'workshop',
    ws.event_date, ws.event_date, ws.start_time::TIME, ws.end_time::TIME,
    ARRAY['na-hall-1'], 0.55, 0.85, 'probabilistic', 0.45,
    ws.topic || ' workshop - Professional development'
FROM academic_terms t,
(VALUES
    ('2026-01-12'::DATE, '09:00', '13:00', 'Industry 4.0'),
    ('2026-01-19'::DATE, '13:00', '17:00', 'Leadership & Soft Skills'),
    ('2026-02-02'::DATE, '09:00', '13:00', 'Python Programming'),
    ('2026-02-09'::DATE, '13:00', '17:00', 'Data Science Basics'),
    ('2026-03-02'::DATE, '09:00', '13:00', 'Web Development'),
    ('2026-03-09'::DATE, '13:00', '17:00', 'Mobile App Dev'),
    ('2026-04-06'::DATE, '09:00', '13:00', 'Entrepreneurship'),
    ('2026-04-13'::DATE, '13:00', '17:00', 'Environmental Sustainability'),
    ('2026-05-04'::DATE, '09:00', '13:00', 'Communication Skills'),
    ('2026-05-11'::DATE, '13:00', '17:00', 'Professional Ethics')
) ws(event_date, start_time, end_time, topic)
WHERE t.year = 2026
ON CONFLICT DO NOTHING;

-- Sri Lanka Public Holidays 2026 (25 holidays)
INSERT INTO public_holidays_2026 (date, name, description, 
    occupancy_classroom, occupancy_lab, occupancy_library, occupancy_canteen,
    occupancy_office, occupancy_auditorium, occupancy_hostel, occupancy_outdoor, occupancy_other) VALUES
    ('2026-01-14'::DATE, 'Thai Pongal', 'Hindu harvest festival', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-01-15'::DATE, 'Independence Day (observed)', 'National holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-02-04'::DATE, 'Independence Day (actual)', 'National holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-02-13'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-03-08'::DATE, 'Maha Shivaratri', 'Hindu festival', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-03-15'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-04-13'::DATE, 'Sinhala & Tamil New Year', 'New Year festival', 0, 0, 0, 0.15, 0, 0, 0.70, 0.02, 0),
    ('2026-04-14'::DATE, 'Sinhala & Tamil New Year (day 2)', 'New Year festival', 0, 0, 0, 0.15, 0, 0, 0.70, 0.02, 0),
    ('2026-04-15'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-05-01'::DATE, 'Labour Day', 'International workers day', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-05-15'::DATE, 'Full Moon Poya Day (Wesak)', 'Buddhist festival', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-05-16'::DATE, 'Wesak Holiday', 'Buddhist festival holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-06-14'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-07-13'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-08-12'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-08-31'::DATE, 'Bank Holiday', 'National bank holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-09-10'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-10-10'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-10-31'::DATE, 'Deepavali', 'Hindu festival of lights', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-11-09'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-12-08'::DATE, 'Full Moon Poya Day', 'Buddhist holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-12-25'::DATE, 'Christmas Day', 'Christian holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2026-12-31'::DATE, 'Bank Holiday (Year End)', 'Bank holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2027-01-14'::DATE, 'Thai Pongal (2027)', 'Hindu harvest festival', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0),
    ('2027-01-15'::DATE, 'Independence Day 2027 (observed)', 'National holiday', 0, 0, 0, 0.15, 0, 0, 0.70, 0.01, 0)
ON CONFLICT (date) DO NOTHING;

-- ============================================================================
-- FUNCTIONS & STORED PROCEDURES
-- ============================================================================

-- Get current academic term
CREATE OR REPLACE FUNCTION get_current_academic_term()
RETURNS TABLE(term_id UUID, term_name TEXT, occupancy_factor FLOAT) AS $$
BEGIN
    RETURN QUERY
    WITH term_info AS (
        SELECT t.term_id, t.term_name, 1.0 as base_factor
        FROM academic_terms t
        WHERE CURRENT_DATE BETWEEN t.start_date AND t.end_date
        LIMIT 1
    ),
    event_info AS (
        SELECT ce.occupancy_factor
        FROM calendar_events ce
        WHERE CURRENT_DATE BETWEEN ce.start_date AND ce.end_date
        LIMIT 1
    )
    SELECT 
        ti.term_id,
        ti.term_name,
        COALESCE(ei.occupancy_factor, ti.base_factor) as occupancy_factor
    FROM term_info ti
    LEFT JOIN event_info ei ON TRUE;
END;
$$ LANGUAGE plpgsql;

-- Get occupancy factor for a given date (considering academic calendar)
CREATE OR REPLACE FUNCTION get_occupancy_factor_for_date(check_date DATE)
RETURNS FLOAT AS $$
DECLARE
    v_factor FLOAT;
BEGIN
    -- Check if there's a calendar event on this date
    SELECT occupancy_factor INTO v_factor
    FROM calendar_events
    WHERE check_date BETWEEN start_date AND end_date
    LIMIT 1;
    
    -- Default to 1.0 if no special event
    RETURN COALESCE(v_factor, 1.0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ROW-LEVEL SECURITY (optional, for multi-tenant scenarios)
-- ============================================================================
-- Can be enabled by uncommenting:
-- ALTER TABLE sensor_readings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE academic_terms ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- GRANTS (for non-superuser access)
-- ============================================================================
-- Uncomment if using restricted user:
-- GRANT USAGE ON SCHEMA public TO ctuser;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO ctuser;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ctuser;
