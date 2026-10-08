-- =====================================================================
-- add_tax_and_grievance.sql
-- Phase 5: Tax Payment + Public Grievance modules.
--
-- Also adds a Submitted_On column to Birth/Death/License. This is
-- required by the Grievance module's "Check for Approval Delay" step
-- (ActivityDiagram.jpg): to know whether a request is overdue we need
-- to know WHEN it was filed, and Birth_Date / Death_Date / Renewal_Date
-- are event dates, not submission dates. Existing rows are backfilled
-- with today's date so nothing is left NULL.
--
-- Safe to run on your existing database.
--
-- Usage:
--   mysql -u root -p municipal_corporation < add_tax_and_grievance.sql
-- =====================================================================

USE municipal_corporation;

-- ---------------------------------------------------------------------
-- Submission dates (needed for grievance delay checking)
-- ---------------------------------------------------------------------
ALTER TABLE Birth_Registration ADD COLUMN Submitted_On DATE NULL;
UPDATE Birth_Registration SET Submitted_On = CURDATE() WHERE Submitted_On IS NULL;

ALTER TABLE Death_Registration ADD COLUMN Submitted_On DATE NULL;
UPDATE Death_Registration SET Submitted_On = CURDATE() WHERE Submitted_On IS NULL;

ALTER TABLE License ADD COLUMN Submitted_On DATE NULL;
UPDATE License SET Submitted_On = CURDATE() WHERE Submitted_On IS NULL;

-- ---------------------------------------------------------------------
-- Tax_Payment  (ClassDiagram.jpg: TaxPayment)
-- A citizen may pay property tax OR business tax; the unused pair of
-- columns stays NULL, which is why Tax_Type records which kind it is.
-- Citizen (1) ---- (*) Tax_Payment
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Tax_Payment (
    Transaction_ID   INT AUTO_INCREMENT PRIMARY KEY,
    Citizen_ID       INT NOT NULL,
    Tax_Type         ENUM('Property', 'Business') NOT NULL,
    Property_ID      VARCHAR(50) NULL,
    Property_Value   DECIMAL(15, 2) NULL,
    Business_ID      VARCHAR(50) NULL,
    Business_Income  DECIMAL(15, 2) NULL,
    Tax_Amount       DECIMAL(15, 2) NOT NULL,
    Payment_Date     DATE NOT NULL,
    CONSTRAINT fk_tax_citizen
        FOREIGN KEY (Citizen_ID) REFERENCES Citizen(citizenId)
        ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- Grievance  (ClassDiagram.jpg: Grievance)
-- Reference_Type + Reference_ID together point at the request the
-- grievance is about (the class diagram's single referenceId isn't
-- enough on its own, since IDs are only unique within their own table).
-- Both stay NULL for a general grievance not tied to any request.
-- Citizen (1) ---- (*) Grievance
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Grievance (
    Grievance_ID    INT AUTO_INCREMENT PRIMARY KEY,
    Citizen_ID      INT NOT NULL,
    Category        VARCHAR(50) NOT NULL,
    Description     TEXT NOT NULL,
    Grievance_Date  DATE NOT NULL,
    Reference_Type  ENUM('Birth', 'Death', 'License', 'Sanitation') NULL,
    Reference_ID    INT NULL,
    Status          ENUM('Open', 'Resolved', 'Rejected') NOT NULL DEFAULT 'Open',
    Admin_Response  TEXT NULL,
    Responded_On    DATE NULL,
    CONSTRAINT fk_grievance_citizen
        FOREIGN KEY (Citizen_ID) REFERENCES Citizen(citizenId)
        ON DELETE CASCADE
);
