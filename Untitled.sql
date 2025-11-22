CREATE TABLE "users" (
  "user_id" uuid PRIMARY KEY,
  "email" text UNIQUE NOT NULL,
  "password_hash" text NOT NULL,
  "full_name" text NOT NULL,
  "role" text NOT NULL CHECK (role in ('passenger','admin')),
  "created_at" timestamp DEFAULT now() NOT NULL,
  "is_active" bool DEFAULT true NOT NULL
);

CREATE TABLE "user_sessions" (
  "session_id" uuid PRIMARY KEY,
  "user_id" uuid NOT NULL,
  "issued_at" timestamp DEFAULT now() NOT NULL,
  "expires_at" timestamp NOT NULL,
  "user_agent" text,
  "ip" inet
);

CREATE TABLE "drivers" (
  "driver_id" uuid PRIMARY KEY,
  "license_no" text NOT NULL,
  "hired_at" date NOT NULL
);

CREATE TABLE "vehicles" (
  "vehicle_id" uuid PRIMARY KEY,
  "plate" text UNIQUE NOT NULL,
  "model" text,
  "capacity" int CHECK (capacity > 0),
  "active" bool DEFAULT true NOT NULL
);

CREATE TABLE "lines" (
  "line_id" uuid PRIMARY KEY,
  "code" text UNIQUE NOT NULL,
  "name" text NOT NULL,
  "mode" text NOT NULL CHECK (mode in ('bus','tram','metro')),
  "active" bool DEFAULT true NOT NULL
);

CREATE TABLE "line_schedules" (
  "schedule_id" uuid PRIMARY KEY,
  "line_id" uuid NOT NULL,
  "dow" int NOT NULL CHECK (dow between 0 and 6), -- day of the week
  "start_time" time NOT NULL,
  "end_time" time NOT NULL,
  "headway_minutes" int NOT NULL CHECK (headway_minutes > 0)
);

CREATE TABLE "stops" (
  "stop_id" uuid PRIMARY KEY,
  "code" text UNIQUE NOT NULL,
  "name" text NOT NULL,
  "lat" double,
  "lon" double
);

CREATE TABLE "stop_times" (
  "stop_time_id" uuid PRIMARY KEY,
  "line_id" uuid NOT NULL,
  "stop_id" uuid NOT NULL,
  "scheduled_seconds_from_start" int NOT NULL
);

CREATE TABLE "driver_assignments" (
  "assignment_id" uuid PRIMARY KEY,
  "driver_id" uuid NOT NULL,
  "vehicle_id" uuid NOT NULL,
  "line_id" uuid NOT NULL,
  "start_ts" timestamp NOT NULL,
  "end_ts" timestamp,
  CHECK (end_ts is null or end_ts > start_ts)
);

CREATE TABLE "trips" (
  "trip_id" uuid PRIMARY KEY,
  "user_id" uuid,
  "line_id" uuid,
  "origin_stop_id" uuid,
  "dest_stop_id" uuid,
  "planned_start" timestamp NOT NULL,
  "planned_end" timestamp,
  "created_at" timestamp DEFAULT now() NOT NULL
);

CREATE TABLE "trip_stops" (
  "trip_id" uuid,
  "stop_id" uuid NOT NULL,
  "eta" timestamp,
  "ata" timestamp,
  PRIMARY KEY ("trip_id")
);

CREATE INDEX "idx_users_email" ON "users" ("email");

CREATE UNIQUE INDEX ON "stop_times" ("line_id", "stop_id");

CREATE INDEX "idx_driver_assignments_active" ON "driver_assignments" ("line_id", "start_ts");

ALTER TABLE "user_sessions" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("user_id") ON DELETE CASCADE;

ALTER TABLE "line_schedules" ADD FOREIGN KEY ("line_id") REFERENCES "lines" ("line_id") ON DELETE CASCADE;

ALTER TABLE "stop_times" ADD FOREIGN KEY ("line_id") REFERENCES "lines" ("line_id") ON DELETE CASCADE;

ALTER TABLE "stop_times" ADD FOREIGN KEY ("stop_id") REFERENCES "stops" ("stop_id") ON DELETE RESTRICT;

ALTER TABLE "driver_assignments" ADD FOREIGN KEY ("driver_id") REFERENCES "drivers" ("driver_id") ON DELETE CASCADE;

ALTER TABLE "driver_assignments" ADD FOREIGN KEY ("vehicle_id") REFERENCES "vehicles" ("vehicle_id") ON DELETE RESTRICT;

ALTER TABLE "driver_assignments" ADD FOREIGN KEY ("line_id") REFERENCES "lines" ("line_id") ON DELETE RESTRICT;

ALTER TABLE "trips" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("user_id") ON DELETE SET NULL;

ALTER TABLE "trips" ADD FOREIGN KEY ("line_id") REFERENCES "lines" ("line_id");

ALTER TABLE "trips" ADD FOREIGN KEY ("origin_stop_id") REFERENCES "stops" ("stop_id");

ALTER TABLE "trips" ADD FOREIGN KEY ("dest_stop_id") REFERENCES "stops" ("stop_id");

ALTER TABLE "trip_stops" ADD FOREIGN KEY ("trip_id") REFERENCES "trips" ("trip_id") ON DELETE CASCADE;

ALTER TABLE "trip_stops" ADD FOREIGN KEY ("stop_id") REFERENCES "stops" ("stop_id");
