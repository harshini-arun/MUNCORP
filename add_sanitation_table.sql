-- =====================================================================
-- add_sanitation_table.sql
-- Adds the Sanitation Request module (see ActivityDiagram.jpg /
-- ClassDiagram.jpg). Safe to run on your existing database.
--
-- Usage:
--   mysql -u root -p municipal_corporation < add_sanitation_table.sql
-- =====================================================================

USE municipal_corporation;

CREATE TABLE IF NOT EXISTS Sanitation_Request (
    Request_ID      INT AUTO_INCREMENT PRIMARY KEY,
    Citizen_ID      INT NOT NULL,
    Area_PIN        VARCHAR(10) NOT NULL,
    Requested_Date  DATE NOT NULL,
    Schedule_Date   DATE NULL,
    Status          ENUM('Pending', 'Scheduled', 'Rejected') NOT NULL DEFAULT 'Pending',
    CONSTRAINT fk_sanitation_citizen
        FOREIGN KEY (Citizen_ID) REFERENCES Citizen(citizenId)
        ON DELETE CASCADE
);
