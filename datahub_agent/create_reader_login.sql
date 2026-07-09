-- Data Hub Agent — read-only login για τη bmisthos (τρέξε το ΜΙΑ φορά στο SSMS ως admin).
-- Δίνει ΜΟΝΟ ανάγνωση (db_datareader). ΚΑΜΙΑ εγγραφή/DDL. Αλλαξε τον κωδικο!

-- 1) Login στο server επίπεδο
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'estia_reader')
    CREATE LOGIN estia_reader WITH PASSWORD = 'ΒΑΛΕ_ΔΥΝΑΤΟ_ΚΩΔΙΚΟ_ΕΔΩ', CHECK_POLICY = ON;
GO

-- 2) User μεσα στη bmisthos + ρολος db_datareader (μονο ανάγνωση)
USE bmisthos;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'estia_reader')
    CREATE USER estia_reader FOR LOGIN estia_reader;
GO
ALTER ROLE db_datareader ADD MEMBER estia_reader;
GO

-- Έλεγχος: πρεπει να επιστρεψει 'db_datareader'
SELECT r.name AS role_name
FROM sys.database_role_members m
JOIN sys.database_principals r ON r.principal_id = m.role_principal_id
JOIN sys.database_principals u ON u.principal_id = m.member_principal_id
WHERE u.name = 'estia_reader';
GO
