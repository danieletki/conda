-- Script di inizializzazione PostgreSQL per MercatoPro
-- Questo script viene eseguito automaticamente alla prima creazione del container

-- Crea utente aggiuntivo se necessario
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mercato_user') THEN
        CREATE USER mercato_user WITH PASSWORD 'mercato_password';
    END IF;
END $$;

-- Concedi privilegi all'utente
GRANT ALL PRIVILEGES ON DATABASE mercato_db TO mercato_user;

-- Connessione al database per configurazioni aggiuntive
\c mercato_db;

-- Crea estensioni utili
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Concedi privilegi sulle tabelle (verranno create dalle migrazioni Django)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mercato_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mercato_user;

-- Imposta timezone di default
ALTER DATABASE mercato_db SET timezone TO 'UTC';

-- Log di conferma
DO $$
BEGIN
    RAISE NOTICE 'Database mercato_db configurato con successo per MercatoPro!';
END $$;