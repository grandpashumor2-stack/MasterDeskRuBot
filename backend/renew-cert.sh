#!/bin/bash
set -euo pipefail
cd /root/masterdesk/backend
docker run --rm \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  certbot/certbot renew --webroot -w /var/www/certbot --quiet
docker compose exec nginx nginx -s reload
