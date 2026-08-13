-- =====================================================================
-- municipal_corporation.sql
-- Phase 1: Authentication module only.
-- Creates the Citizen and Admin tables and inserts sample test records.
--
-- Passwords are stored as Werkzeug scrypt hashes (matching the
-- check_password_hash() calls used in routes/auth.py), NOT plain text.
--   Citizen 1001 password: password123
--   Admin   1    password: admin123
-- =====================================================================

CREATE DATABASE IF NOT EXISTS municipal_corporation;
USE municipal_corporation;

-- ---------------------------------------------------------------------
-- Citizen table
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS Citizen;
CREATE TABLE Citizen (
    citizenId INT PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    phone     VARCHAR(15),
    email     VARCHAR(100),
    password  VARCHAR(255) NOT NULL
);

-- ---------------------------------------------------------------------
-- Admin table
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS Admin;
CREATE TABLE Admin (
    adminId  INT PRIMARY KEY,
    password VARCHAR(255) NOT NULL
);

-- ---------------------------------------------------------------------
-- Sample records
-- ---------------------------------------------------------------------
INSERT INTO Citizen (citizenId, name, phone, email, password) VALUES
(1001, 'Harshini', '9876543210', 'harshini@email.com',
 'scrypt:32768:8:1$8YWrVoz0e8pMzgs3$1e53ea2da77553be7cf48f1f2e0913ab25cc36072606317b1e4262423adc2f7311aa6e919e070e4ce8dad5c584f55c7d2c3e01a0d8f294cac3c8fa4cd6f6436e');

INSERT INTO Admin (adminId, password) VALUES
(1, 'scrypt:32768:8:1$AksRppS5dDymt5sp$033b327f6c0af5fb12713caa6f6e7e6d2c80abff1575e0a9cfc2c5a67b50b48b82044b7fc39a473d5abd0051f4e04e879ed59124aad64015a567a461d00db66c');


-- =====================================================================
-- Phase 2: Birth Registration, Death Registration, License modules.
-- Run this section against an EXISTING database to add the three new
-- tables without touching Citizen / Admin data.
-- Relationships: Citizen (1) ---- (*) Birth_Registration
--                Citizen (1) ---- (*) Death_Registration
--                Citizen (1) ---- (*) License
-- =====================================================================

-- ---------------------------------------------------------------------
-- Birth_Registration table
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

-- =====================================================================
-- Phase 3: Hospital certificate code verification (see ClassDiagram.jpg)
-- =====================================================================
CREATE TABLE IF NOT EXISTS HospitalCertificate (
    Cert_ID         INT AUTO_INCREMENT PRIMARY KEY,
    Hospital_Name   VARCHAR(150) NOT NULL,
    Med_Cert_Code   VARCHAR(50) NOT NULL UNIQUE,
    Issue_Date      DATE NOT NULL,
    Used            TINYINT(1) NOT NULL DEFAULT 0
);

INSERT INTO HospitalCertificate (Hospital_Name, Med_Cert_Code, Issue_Date, Used) VALUES
('Apollo Hospital, Chennai',       'MC-BIRTH-1001', '2026-08-01', 0),
('Apollo Hospital, Chennai',       'MC-DEATH-1001', '2026-08-01', 0),
('Government General Hospital',    'MC-BIRTH-1002', '2026-08-02', 0),
('Government General Hospital',    'MC-DEATH-1002', '2026-08-02', 0),
('Fortis Malar Hospital',          'MC-BIRTH-1003', '2026-08-03', 0);
