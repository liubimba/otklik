#!/bin/bash

DB_FILE=$HOME/.otklik/db.sqlite

sqlite3 "$DB_FILE" <<EOF
PRAGMA foreign_keys = OFF;

$(sqlite3 "$DB_FILE" "
SELECT 'DELETE FROM \"' || name || '\";'
FROM sqlite_master
WHERE type = 'table'
  AND name NOT LIKE 'sqlite_%';
")

PRAGMA foreign_keys = ON;
VACUUM;
EOF
Н
