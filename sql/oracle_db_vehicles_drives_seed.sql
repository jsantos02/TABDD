-- ============================================================
-- Seed vehicles, drivers, driver_assignments
-- 2 vehicles + 2 drivers per line
-- Includes model + capacity based on line_mode
-- ============================================================

-- ----------------------------
-- VEHICLES
-- ----------------------------

INSERT INTO vehicles (vehicle_id, plate, model, capacity)
SELECT
    'VEH_' || l.code || '_01',
    'PT-'  || l.code || '-01',
    CASE
        WHEN l.line_mode = 'metro' THEN 'CRRC Tram'
        WHEN l.line_mode = 'bus'   THEN 'Mercedez-Benz Citaro'
        ELSE 'Generic Vehicle'
    END,
    CASE
        WHEN l.line_mode = 'metro' THEN 244
        WHEN l.line_mode = 'bus'   THEN 44
        ELSE NULL
    END
FROM lines l
WHERE NOT EXISTS (
    SELECT 1 FROM vehicles v
    WHERE v.vehicle_id = 'VEH_' || l.code || '_01'
);

INSERT INTO vehicles (vehicle_id, plate, model, capacity)
SELECT
    'VEH_' || l.code || '_02',
    'PT-'  || l.code || '-02',
    CASE
        WHEN l.line_mode = 'metro' THEN 'CRRC Tram'
        WHEN l.line_mode = 'bus'   THEN 'Mercedez-Benz Citaro'
        ELSE 'Generic Vehicle'
    END,
    CASE
        WHEN l.line_mode = 'metro' THEN 244
        WHEN l.line_mode = 'bus'   THEN 44
        ELSE NULL
    END
FROM lines l
WHERE NOT EXISTS (
    SELECT 1 FROM vehicles v
    WHERE v.vehicle_id = 'VEH_' || l.code || '_02'
);

-- ----------------------------
-- DRIVERS
-- ----------------------------

INSERT INTO drivers (driver_id, license_no, hired_at)
SELECT
    'DRV_' || l.code || '_01',
    'LIC-' || l.code || '-01',
    SYSDATE - 30
FROM lines l
WHERE NOT EXISTS (
    SELECT 1 FROM drivers d
    WHERE d.driver_id = 'DRV_' || l.code || '_01'
);

INSERT INTO drivers (driver_id, license_no, hired_at)
SELECT
    'DRV_' || l.code || '_02',
    'LIC-' || l.code || '-02',
    SYSDATE - 30
FROM lines l
WHERE NOT EXISTS (
    SELECT 1 FROM drivers d
    WHERE d.driver_id = 'DRV_' || l.code || '_02'
);

-- ----------------------------
-- DRIVER ASSIGNMENTS
-- ----------------------------

INSERT INTO driver_assignments (assignment_id, driver_id, vehicle_id, line_id, start_ts)
SELECT
    'ASG_' || l.code || '_01',
    'DRV_' || l.code || '_01',
    'VEH_' || l.code || '_01',
    l.line_id,
    SYSTIMESTAMP
FROM lines l
WHERE NOT EXISTS (
    SELECT 1 FROM driver_assignments da
    WHERE da.assignment_id = 'ASG_' || l.code || '_01'
);

INSERT INTO driver_assignments (assignment_id, driver_id, vehicle_id, line_id, start_ts)
SELECT
    'ASG_' || l.code || '_02',
    'DRV_' || l.code || '_02',
    'VEH_' || l.code || '_02',
    l.line_id,
    SYSTIMESTAMP
FROM lines l
WHERE NOT EXISTS (
    SELECT 1 FROM driver_assignments da
    WHERE da.assignment_id = 'ASG_' || l.code || '_02'
);

COMMIT;
