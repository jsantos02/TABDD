------------------------------------------------------------
-- TABLES
------------------------------------------------------------

CREATE TABLE users (
  user_id        VARCHAR2(36)   PRIMARY KEY,
  email          VARCHAR2(255)  CONSTRAINT uq_users_email UNIQUE NOT NULL,
  password_hash  VARCHAR2(255)  NOT NULL,
  full_name      VARCHAR2(255)  NOT NULL,
  role           VARCHAR2(20)   NOT NULL
                  CONSTRAINT chk_users_role
                  CHECK (role IN ('passenger','admin')),
  created_at     TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,
  is_active      NUMBER(1)      DEFAULT 1 NOT NULL
                  CONSTRAINT chk_users_is_active
                  CHECK (is_active IN (0,1))
);

CREATE TABLE user_sessions (
  session_id  VARCHAR2(36)  PRIMARY KEY,
  user_id     VARCHAR2(36)  NOT NULL,
  issued_at   TIMESTAMP     DEFAULT SYSTIMESTAMP NOT NULL,
  expires_at  TIMESTAMP     NOT NULL,
  user_agent  VARCHAR2(4000),
  ip          VARCHAR2(45)
);

CREATE TABLE drivers (
  driver_id   VARCHAR2(36)  PRIMARY KEY,
  license_no  VARCHAR2(50)  NOT NULL,
  hired_at    DATE          NOT NULL
);

CREATE TABLE vehicles (
  vehicle_id  VARCHAR2(36)  PRIMARY KEY,
  plate       VARCHAR2(20)  NOT NULL,
  model       VARCHAR2(100),
  capacity    NUMBER(5)     CONSTRAINT chk_vehicles_capacity
                             CHECK (capacity > 0),
  active      NUMBER(1)     DEFAULT 1 NOT NULL
                CONSTRAINT chk_vehicles_active
                CHECK (active IN (0,1)),
  CONSTRAINT uq_vehicles_plate UNIQUE (plate)
);

CREATE TABLE lines (
  line_id  VARCHAR2(36)  PRIMARY KEY,
  code     VARCHAR2(20)  NOT NULL,
  name     VARCHAR2(255) NOT NULL,
  mode     VARCHAR2(20)  NOT NULL
             CONSTRAINT chk_lines_mode
             CHECK (mode IN ('bus','tram','metro')),
  active   NUMBER(1)     DEFAULT 1 NOT NULL
             CONSTRAINT chk_lines_active
             CHECK (active IN (0,1)),
  CONSTRAINT uq_lines_code UNIQUE (code)
);

CREATE TABLE line_schedules (
  schedule_id     VARCHAR2(36)  PRIMARY KEY,
  line_id         VARCHAR2(36)  NOT NULL,
  dow             NUMBER(1)     NOT NULL
                     CONSTRAINT chk_line_schedules_dow
                     CHECK (dow BETWEEN 0 AND 6), -- day of week
  start_time      DATE          NOT NULL,
  end_time        DATE          NOT NULL,
  headway_minutes NUMBER(5)     NOT NULL
                     CONSTRAINT chk_line_schedules_headway
                     CHECK (headway_minutes > 0)
);

CREATE TABLE stops (
  stop_id  VARCHAR2(36)   PRIMARY KEY,
  code     VARCHAR2(20)   NOT NULL,
  name     VARCHAR2(255)  NOT NULL,
  lat      NUMBER(10,6),
  lon      NUMBER(10,6),
  CONSTRAINT uq_stops_code UNIQUE (code)
);

CREATE TABLE stop_times (
  stop_time_id                VARCHAR2(36)  PRIMARY KEY,
  line_id                     VARCHAR2(36)  NOT NULL,
  stop_id                     VARCHAR2(36)  NOT NULL,
  scheduled_seconds_from_start NUMBER(10)   NOT NULL
);

CREATE TABLE driver_assignments (
  assignment_id  VARCHAR2(36)  PRIMARY KEY,
  driver_id      VARCHAR2(36)  NOT NULL,
  vehicle_id     VARCHAR2(36)  NOT NULL,
  line_id        VARCHAR2(36)  NOT NULL,
  start_ts       TIMESTAMP     NOT NULL,
  end_ts         TIMESTAMP,
  CONSTRAINT chk_driver_assignments_time
    CHECK (end_ts IS NULL OR end_ts > start_ts)
);

CREATE TABLE trips (
  trip_id         VARCHAR2(36)  PRIMARY KEY,
  user_id         VARCHAR2(36),
  line_id         VARCHAR2(36),
  origin_stop_id  VARCHAR2(36),
  dest_stop_id    VARCHAR2(36),
  planned_start   TIMESTAMP     NOT NULL,
  planned_end     TIMESTAMP,
  created_at      TIMESTAMP     DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE TABLE trip_stops (
  trip_id  VARCHAR2(36),
  stop_id  VARCHAR2(36)  NOT NULL,
  eta      TIMESTAMP,
  ata      TIMESTAMP,
  CONSTRAINT pk_trip_stops PRIMARY KEY (trip_id)
);

------------------------------------------------------------
-- INDEXES
------------------------------------------------------------

-- Non-unique index on users.email (unique constraint already defined)
CREATE INDEX idx_users_email ON users (email);

-- Unique index on line_id, stop_id
CREATE UNIQUE INDEX idx_stop_times_line_stop
  ON stop_times (line_id, stop_id);

CREATE INDEX idx_driver_assignments_active
  ON driver_assignments (line_id, start_ts);

------------------------------------------------------------
-- FOREIGN KEYS
------------------------------------------------------------

ALTER TABLE user_sessions
  ADD CONSTRAINT fk_user_sessions_user
  FOREIGN KEY (user_id)
  REFERENCES users (user_id)
  ON DELETE CASCADE;

ALTER TABLE line_schedules
  ADD CONSTRAINT fk_line_schedules_line
  FOREIGN KEY (line_id)
  REFERENCES lines (line_id)
  ON DELETE CASCADE;

ALTER TABLE stop_times
  ADD CONSTRAINT fk_stop_times_line
  FOREIGN KEY (line_id)
  REFERENCES lines (line_id)
  ON DELETE CASCADE;

ALTER TABLE stop_times
  ADD CONSTRAINT fk_stop_times_stop
  FOREIGN KEY (stop_id)
  REFERENCES stops (stop_id);

ALTER TABLE driver_assignments
  ADD CONSTRAINT fk_driver_assignments_driver
  FOREIGN KEY (driver_id)
  REFERENCES drivers (driver_id)
  ON DELETE CASCADE;

ALTER TABLE driver_assignments
  ADD CONSTRAINT fk_driver_assignments_vehicle
  FOREIGN KEY (vehicle_id)
  REFERENCES vehicles (vehicle_id);

ALTER TABLE driver_assignments
  ADD CONSTRAINT fk_driver_assignments_line
  FOREIGN KEY (line_id)
  REFERENCES lines (line_id);

ALTER TABLE trips
  ADD CONSTRAINT fk_trips_user
  FOREIGN KEY (user_id)
  REFERENCES users (user_id)
  ON DELETE SET NULL;

ALTER TABLE trips
  ADD CONSTRAINT fk_trips_line
  FOREIGN KEY (line_id)
  REFERENCES lines (line_id);

ALTER TABLE trips
  ADD CONSTRAINT fk_trips_origin_stop
  FOREIGN KEY (origin_stop_id)
  REFERENCES stops (stop_id);

ALTER TABLE trips
  ADD CONSTRAINT fk_trips_dest_stop
  FOREIGN KEY (dest_stop_id)
  REFERENCES stops (stop_id);

ALTER TABLE trip_stops
  ADD CONSTRAINT fk_trip_stops_trip
  FOREIGN KEY (trip_id)
  REFERENCES trips (trip_id)
  ON DELETE CASCADE;

ALTER TABLE trip_stops
  ADD CONSTRAINT fk_trip_stops_stop
  FOREIGN KEY (stop_id)
  REFERENCES stops (stop_id);
