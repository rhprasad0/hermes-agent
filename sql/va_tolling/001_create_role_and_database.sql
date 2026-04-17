\set ON_ERROR_STOP on
\getenv va_tolling_password VA_TOLLING_DB_PASSWORD

\if :{?va_tolling_password}
\else
\echo 'set VA_TOLLING_DB_PASSWORD in the environment before running this script'
\quit 1
\endif

SELECT format('CREATE ROLE va_tolling_app LOGIN PASSWORD %L', :'va_tolling_password')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_roles WHERE rolname = 'va_tolling_app'
)\gexec

SELECT format('ALTER ROLE va_tolling_app WITH LOGIN PASSWORD %L', :'va_tolling_password')\gexec

SELECT 'CREATE DATABASE va_tolling OWNER va_tolling_app'
WHERE NOT EXISTS (
  SELECT 1 FROM pg_database WHERE datname = 'va_tolling'
)\gexec

ALTER DATABASE va_tolling OWNER TO va_tolling_app;
