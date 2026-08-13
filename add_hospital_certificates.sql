-- =====================================================================
-- add_hospital_certificates.sql
-- Phase 3: adds the HospitalCertificate table (see ClassDiagram.jpg) to
-- an ALREADY EXISTING municipal_corporation database, and seeds it with
-- a few sample codes for testing Birth/Death Registration.
--
-- Safe to run on your current database: it does NOT touch Citizen,
-- Admin, Birth_Registration, Death_Registration, or License.
--
-- Usage:
--   mysql -u root -p municipal_corporation < add_hospital_certificates.sql
-- =====================================================================

USE municipal_corporation;

CREATE TABLE IF NOT EXISTS HospitalCertificate (
    Cert_ID         INT AUTO_INCREMENT PRIMARY KEY,
    Hospital_Name   VARCHAR(150) NOT NULL,
    Med_Cert_Code   VARCHAR(50) NOT NULL UNIQUE,
    Issue_Date      DATE NOT NULL,
    Used            TINYINT(1) NOT NULL DEFAULT 0
);

-- Sample codes a hospital would have issued -- use these to test the
-- Birth/Death Registration forms.
INSERT INTO HospitalCertificate (Hospital_Name, Med_Cert_Code, Issue_Date, Used) VALUES
('Apollo Hospital, Chennai',       'MC-BIRTH-1001', '2026-08-01', 0),
('Apollo Hospital, Chennai',       'MC-DEATH-1001', '2026-08-01', 0),
('Government General Hospital',    'MC-BIRTH-1002', '2026-08-02', 0),
('Government General Hospital',    'MC-DEATH-1002', '2026-08-02', 0),
('Fortis Malar Hospital',          'MC-BIRTH-1003', '2026-08-03', 0);
