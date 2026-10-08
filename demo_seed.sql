-- =====================================================================
-- demo_seed.sql
-- MUNCORPPY — Demo data seed for 3-admin zone demonstration.
--
-- SAFE TO RUN on an existing database that already has the schema.
-- Does NOT drop any tables. Uses INSERT IGNORE / INSERT ... ON DUPLICATE
-- KEY UPDATE so it is safe to run more than once.
--
-- What this file does:
--   1. Adds zone_min / zone_max columns to the Admin table (IF NOT EXISTS).
--   2. Inserts / updates 3 Admin accounts with zone assignments.
--   3. Inserts 9 demo Citizen accounts (3 per zone).
--   4. Adds extra HospitalCertificate codes for demo registration flows.
--
-- Passwords (stored as Werkzeug scrypt hashes, never plain text):
--   Admin 1   (adminId=1):  AdminZone1#
--   Admin 2   (adminId=2):  AdminZone2#
--   Admin 3   (adminId=3):  AdminZone3#
--   Citizen 1001 (existing): password123  (preserved)
--   Citizen 1002:  Citizen1002!
--   Citizen 1003:  Citizen1003!
--   Citizen 2001:  Citizen2001!
--   Citizen 2002:  Citizen2002!
--   Citizen 2003:  Citizen2003!
--   Citizen 3001:  Citizen3001!
--   Citizen 3002:  Citizen3002!
--   Citizen 3003:  Citizen3003!
--
-- Usage:
--   mysql -u root -p municipal_corporation < demo_seed.sql
-- =====================================================================

USE municipal_corporation;

-- ---------------------------------------------------------------------
-- Step 1: Add zone columns to Admin table (idempotent via procedure)
-- MySQL versions prior to 8.0 don't support IF NOT EXISTS on ADD COLUMN,
-- so we use a short-lived stored procedure to guard the ALTER.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS _add_zone_columns;
DELIMITER $$
CREATE PROCEDURE _add_zone_columns()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'Admin' AND column_name = 'zone_min'
    ) THEN
        ALTER TABLE Admin ADD COLUMN zone_min INT NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'Admin' AND column_name = 'zone_max'
    ) THEN
        ALTER TABLE Admin ADD COLUMN zone_max INT NULL;
    END IF;
END$$
DELIMITER ;
CALL _add_zone_columns();
DROP PROCEDURE IF EXISTS _add_zone_columns;

-- ---------------------------------------------------------------------
-- Step 2: Upsert 3 Admin accounts with zone assignments
-- Passwords are Werkzeug scrypt hashes — NEVER plain text.
-- ---------------------------------------------------------------------
INSERT INTO Admin (adminId, password, zone_min, zone_max)
VALUES
    (1,
     'scrypt:32768:8:1$2sxWJuF9U4NXlXbm$e7d8e8ae2bff9d4fb47d7a5ece0520d1c371a7722faadec3dc7cc08f79096221e923f11947e44b5502f18132e4236edbb0d38d785c7be7bb8f3663563b81a4da',
     1000, 1999),
    (2,
     'scrypt:32768:8:1$JEQrwhA7qEWhuZci$f07bb8387e71de741ef53553a712bc710733ede14376a04441e704180cdadedf38fac7871b6b9051f659ae028cfa860a118ba943c65a23b9f8abb30fd32594ef',
     2000, 2999),
    (3,
     'scrypt:32768:8:1$FkEDfwIUDNW3kOos$aa89e6267f2a87e261522b984283ea69dd009a870f7dca46ac00af378964d096e9fcc9b718e1ec7615bce8f158636c1cde257103cd6a7331fb580036ef98dbf7',
     3000, 3999)
ON DUPLICATE KEY UPDATE
    password  = VALUES(password),
    zone_min  = VALUES(zone_min),
    zone_max  = VALUES(zone_max);

-- ---------------------------------------------------------------------
-- Step 3: Demo Citizen accounts
-- Zone 1 (1000–1999) — managed by Admin 1
-- Citizen 1001 already exists (Harshini). Preserve her password hash.
-- New: 1002, 1003
-- Zone 2 (2000–2999) — managed by Admin 2: 2001, 2002, 2003
-- Zone 3 (3000–3999) — managed by Admin 3: 3001, 3002, 3003
-- ---------------------------------------------------------------------

-- Zone 1 — new demo citizens
INSERT INTO Citizen (citizenId, name, phone, email, password)
VALUES
    (1002, 'Arjun Ramesh',   '9876501002', 'arjun.ramesh@email.com',
     'scrypt:32768:8:1$SXcwIrPrQqTvfw9f$3accf155008cc6447eb29f1ce5990ad723c0cdd43d3467b0f150dfe77651438bc9e325872400cd33100f045e29762364d12f9db296579d168e852d440755bd5a'),
    (1003, 'Meena Suresh',   '9876501003', 'meena.suresh@email.com',
     'scrypt:32768:8:1$yvG5Kmf0Bwgcv7Sy$fc52a4ca0d77044a8df4f869a7ae415396de739285ff8ffdcc42ba69a18cd904acf4bcbcfba476024c23f37a6dcd42525e120cbc3fe1e8ddeb1427c9ddd41559')
ON DUPLICATE KEY UPDATE
    name  = VALUES(name),
    phone = VALUES(phone),
    email = VALUES(email);

-- Zone 2
INSERT INTO Citizen (citizenId, name, phone, email, password)
VALUES
    (2001, 'Priya Venkat',   '9876502001', 'priya.venkat@email.com',
     'scrypt:32768:8:1$PJtQGYAQtTNEAMCz$4e41bb541d46eb7459f09f71b283c0cad863ceaca92f7d4086db6bbf950d36009bfe974c4b4a61053de9057352e893aced79feb2fb2d6bb19cb9fcda70ee2ca9'),
    (2002, 'Ravi Kumar',     '9876502002', 'ravi.kumar@email.com',
     'scrypt:32768:8:1$cLcbRycGk4wjGHQM$c8845aec51a4e39947b4bd85d822827ec37d46668e60b1a1a3b9c09a8905e277a1eaa6d508dc453b60593c2bd3e818d16f9570d011cf4c2fccc1a0a295485caa'),
    (2003, 'Lakshmi Nair',   '9876502003', 'lakshmi.nair@email.com',
     'scrypt:32768:8:1$1xaSWpwENqtxQZuv$f758724e537ae4cd7ae2482c4988813e102618d6f685bf89a9745704b9d32ed344d097fb2104cbbe95103d1ab192b14a2cf231fb1f78bb2306949fd4d548f7af')
ON DUPLICATE KEY UPDATE
    name  = VALUES(name),
    phone = VALUES(phone),
    email = VALUES(email);

-- Zone 3
INSERT INTO Citizen (citizenId, name, phone, email, password)
VALUES
    (3001, 'Suresh Pillai',  '9876503001', 'suresh.pillai@email.com',
     'scrypt:32768:8:1$lT82s5lXHH6oynMA$0a1114473088c442466ea506bc23db6990bffc7bfc74b3fe5a3539d0f9a835ebba81af11b8a3332d2e9f1163b26b4e812e69536e69d37eb71e6ad493b681faab'),
    (3002, 'Divya Krishnan', '9876503002', 'divya.krishnan@email.com',
     'scrypt:32768:8:1$iGwKmJOFYsIETzC0$4c8e6796bdf21ebe67993ba67cd7ad5c443ed6f21add72dba9a5a4413c3de6defda475f059be69a50a8f77d79c0ab6272799d0d673bb9b4817715735e05ad44d'),
    (3003, 'Anand Gopalan',  '9876503003', 'anand.gopalan@email.com',
     'scrypt:32768:8:1$zvktOTfavQ8gJda3$26a0b0bd5def5c0bc9f229b56589744f0060915cb445e7ffa57621cc881ddd1eebc051b7f30bcf8cbc312f29bbd798b647e50228cc27901c01c6ef1e10de7126')
ON DUPLICATE KEY UPDATE
    name  = VALUES(name),
    phone = VALUES(phone),
    email = VALUES(email);

-- ---------------------------------------------------------------------
-- Step 4: Extra HospitalCertificate codes for demo use
-- (Existing codes are preserved; INSERT IGNORE skips if already present)
-- ---------------------------------------------------------------------
INSERT IGNORE INTO HospitalCertificate (Hospital_Name, Med_Cert_Code, Issue_Date, Used) VALUES
('Apollo Hospital, Chennai',    'MC-BIRTH-2001', '2026-09-01', 0),
('Apollo Hospital, Chennai',    'MC-DEATH-2001', '2026-09-01', 0),
('Government General Hospital', 'MC-BIRTH-2002', '2026-09-02', 0),
('Government General Hospital', 'MC-DEATH-2002', '2026-09-02', 0),
('Fortis Malar Hospital',       'MC-BIRTH-2003', '2026-09-03', 0),
('Fortis Malar Hospital',       'MC-DEATH-2003', '2026-09-03', 0),
('MIOT International Hospital', 'MC-BIRTH-3001', '2026-09-04', 0),
('MIOT International Hospital', 'MC-DEATH-3001', '2026-09-04', 0),
('Sri Ramachandra Hospital',    'MC-BIRTH-3002', '2026-09-05', 0),
('Sri Ramachandra Hospital',    'MC-DEATH-3002', '2026-09-05', 0);
