#!/bin/bash
mkdir -p /root/backups
docker exec masterdesk_db pg_dump -U postgres masterdesk > /root/backups/masterdesk_$(date +%Y%m%d_%H%M%S).sql
find /root/backups -name "*.sql" -mtime +7 -delete
