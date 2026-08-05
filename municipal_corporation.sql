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
