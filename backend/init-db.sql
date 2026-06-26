ALTER USER postgres WITH PASSWORD 'postgres';
SELECT 'CREATE DATABASE masterdesk' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'masterdesk')\gexec
