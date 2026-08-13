-- =====================================================================
-- add_registration_tables.sql
-- Phase 2: adds Birth_Registration, Death_Registration, and License
-- tables to an ALREADY EXISTING municipal_corporation database.
--
-- Safe to run on your current database: it does NOT drop or modify the
-- Citizen or Admin tables, so existing accounts are untouched.
--
-- Usage:
--   mysql -u root -p municipal_corporation < add_registration_tables.sql
-- =====================================================================

USE municipal_corporation;

-- ---------------------------------------------------------------------
-- Birth_Registration table
-- Citizen (1) ---- (*) Birth_Registration
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Birth_Registration (
    Birth_Reg_ID       INT AUTO_INCREMENT PRIMARY KEY,
    Child_Name         VARCHAR(100) NOT NULL,
    Parent_Name        VARCHAR(100) NOT NULL,
    Parent_Citizen_ID  INT NOT NULL,
    Place_of_Birth     VARCHAR(150) NOT NULL,
    Birth_Date         DATE NOT NULL,
    Birth_Time         TIME NOT NULL,
    Med_Cert_Code      VARCHAR(50) NOT NULL UNIQUE,
    Status              ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
    CONSTRAINT fk_birth_parent_citizen
        FOREIGN KEY (Parent_Citizen_ID) REFERENCES Citizen(citizenId)
        ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- Death_Registration table
-- Citizen (1) ---- (*) Death_Registration
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Death_Registration (
    Death_Reg_ID    INT AUTO_INCREMENT PRIMARY KEY,
    Name            VARCHAR(100) NOT NULL,
    Citizen_ID      INT NOT NULL,
    Place_of_Death  VARCHAR(150) NOT NULL,
    Death_Date      DATE NOT NULL,
    Death_Time      TIME NOT NULL,
    Med_Cert_Code   VARCHAR(50) NOT NULL UNIQUE,
    Status          ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
    CONSTRAINT fk_death_citizen
        FOREIGN KEY (Citizen_ID) REFERENCES Citizen(citizenId)
        ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- License table
-- Citizen (1) ---- (*) License
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS License (
    License_ID    INT AUTO_INCREMENT PRIMARY KEY,
    Vehicle_ID    VARCHAR(50) NOT NULL,
    Citizen_ID    INT NOT NULL,
    Test_ID       VARCHAR(50) NOT NULL,
    Renewal_Date  DATE NOT NULL,
    Status        ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
    CONSTRAINT fk_license_citizen
        FOREIGN KEY (Citizen_ID) REFERENCES Citizen(citizenId)
        ON DELETE CASCADE
);
