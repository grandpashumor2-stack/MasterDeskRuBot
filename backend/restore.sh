#!/bin/bash
echo "=== Восстановление БД ==="
docker exec masterdesk_db psql -U postgres -c "CREATE DATABASE masterdesk;" 2>/dev/null || echo "БД уже существует"
docker exec masterdesk_api alembic upgrade head
docker exec masterdesk_api python scripts/init_db.py
echo "=== Готово ==="
