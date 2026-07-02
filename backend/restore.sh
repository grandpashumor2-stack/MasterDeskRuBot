#!/bin/bash
set -e
echo "=== Восстановление БД ==="
docker exec masterdesk_db psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';" 2>/dev/null && echo "Пароль OK" || echo "Пароль уже есть или ошибка - продолжаем"
docker exec masterdesk_db psql -U postgres -c "CREATE DATABASE masterdesk;" 2>/dev/null && echo "БД создана" || echo "БД уже существует"
docker exec masterdesk_api alembic upgrade head
docker exec masterdesk_api python scripts/init_db.py
echo "=== Готово ==="
