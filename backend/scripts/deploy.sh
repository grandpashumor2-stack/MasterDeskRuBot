#!/bin/bash
docker compose build --no-cache
docker compose up -d db redis
sleep 10
docker compose run --rm api alembic upgrade head
docker compose run --rm api python scripts/init_db.py
docker compose run --rm api python scripts/init_demo.py
docker compose up -d
echo "Done!"
