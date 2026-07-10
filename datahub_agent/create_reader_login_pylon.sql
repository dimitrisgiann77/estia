-- Data Hub Agent — read-only login για το PYLON (τρέξε το ΜΙΑ φορά στο SSMS ως admin,
-- στον server του Pylon). Δινει ΜΟΝΟ αναγνωση (db_datareader). ΚΑΜΙΑ εγγραφη/DDL.
-- ΑΛΛΑΞΕ: <PYLON_DB> = το ονομα της βασης Pylon (δες Q2/pylon_tables_map)· και τον κωδικο.
-- Αν το Pylon εχει ΠΟΛΛΕΣ βασεις (π.χ. μια ανα εταιρεια), επαναλαβε τα βηματα 2-3 ανα βαση.

-- 1) Login στο server επιπεδο
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'estia_reader')
    CREATE LOGIN estia_reader WITH PASSWORD = 'ΒΑΛΕ_ΔΥΝΑΤΟ_ΚΩΔΙΚΟ_ΕΔΩ', CHECK_POLICY = ON;
GO

-- 2) User μεσα στη βαση Pylon + ρολος db_datareader (μονο αναγνωση)
USE [<PYLON_DB>];
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'estia_reader')
    CREATE USER estia_reader FOR LOGIN estia_reader;
GO
ALTER ROLE db_datareader ADD MEMBER estia_reader;
GO

-- 3) Ελεγχος: πρεπει να επιστρεψει 'db_datareader'
SELECT r.name AS role_name
FROM sys.database_role_members m
JOIN sys.database_principals r ON r.principal_id = m.role_principal_id
JOIN sys.database_principals u ON u.principal_id = m.member_principal_id
WHERE u.name = 'estia_reader';
GO
