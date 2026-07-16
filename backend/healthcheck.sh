#!/bin/bash
# Ежедневная диагностика + автоочистка MasterDesk

BOT_TOKEN="8743483767:AAHSRQSxvqBa0BcYCdugH0DH-SAmMO3Ns-E"
ADMIN_CHAT_ID="6466766416"

# ===== АВТООЧИСТКА =====
DISK_BEFORE=$(df / | awk 'NR==2 {print $3}')

# Docker build cache старше 24ч
docker builder prune -f --filter "until=24h" > /dev/null 2>&1

# Неиспользуемые (dangling) образы
docker image prune -f > /dev/null 2>&1

# __pycache__ и .pyc в проекте
find /root/masterdesk/backend -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
find /root/masterdesk/backend -name '*.pyc' -delete 2>/dev/null

# .bak-файлы старше 3 дней
find /root/masterdesk/backend -name '*.bak*' -mtime +3 -delete 2>/dev/null

# Бэкапы БД старше 14 дней (доп. подстраховка к backup.sh, который чистит через 7)
find /root/backups -name '*.sql' -mtime +14 -delete 2>/dev/null

DISK_AFTER=$(df / | awk 'NR==2 {print $3}')
FREED_KB=$((DISK_BEFORE - DISK_AFTER))
FREED_MB=$((FREED_KB / 1024))

# ===== ДИАГНОСТИКА =====
ALL_OK=true
REPORT="Диагностика MasterDesk
$(date '+%d.%m.%Y %H:%M') UTC

Контейнеры:
"

for name in masterdesk_api masterdesk_bot masterdesk_db masterdesk_redis masterdesk_nginx; do
    STATUS=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null)
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null)
    if [ "$STATUS" == "running" ]; then
        if [ -n "$HEALTH" ] && [ "$HEALTH" != "healthy" ] && [ "$HEALTH" != "<no value>" ]; then
            REPORT="${REPORT}[!] ${name}: running, health=${HEALTH}
"
            ALL_OK=false
        else
            REPORT="${REPORT}[OK] ${name}
"
        fi
    else
        REPORT="${REPORT}[FAIL] ${name}: ${STATUS:-не найден}
"
        ALL_OK=false
    fi
done

DISK_USE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
DISK_FREE=$(df -h / | awk 'NR==2 {print $4}')
REPORT="${REPORT}
Диск: занято ${DISK_USE}%, свободно ${DISK_FREE}
"
if [ "$FREED_MB" -gt 0 ]; then
    REPORT="${REPORT}Автоочистка освободила: ${FREED_MB}MB
"
fi
if [ "$DISK_USE" -ge 85 ]; then
    REPORT="${REPORT}[!] Диск заполнен более чем на 85%!
"
    ALL_OK=false
fi

HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost/health 2>/dev/null)
if [ "$HTTP_CODE" == "200" ]; then
    REPORT="${REPORT}
[OK] Сайт отвечает (200)
"
else
    REPORT="${REPORT}
[FAIL] Сайт не отвечает (код: ${HTTP_CODE})
"
    ALL_OK=false
fi

LAST_BACKUP=$(ls -t /root/backups/*.sql 2>/dev/null | head -1)
if [ -n "$LAST_BACKUP" ]; then
    BACKUP_AGE_HOURS=$(( ( $(date +%s) - $(stat -c %Y "$LAST_BACKUP") ) / 3600 ))
    REPORT="${REPORT}
Бэкап: $(basename "$LAST_BACKUP"), ${BACKUP_AGE_HOURS}ч назад"
    if [ "$BACKUP_AGE_HOURS" -gt 30 ]; then
        REPORT="${REPORT} [!] давно не обновлялся!"
        ALL_OK=false
    fi
else
    REPORT="${REPORT}
[FAIL] Бэкапы не найдены!"
    ALL_OK=false
fi

DEMO_VIEWS=$(docker exec masterdesk_db psql -U postgres -d masterdesk -t -A -c "SELECT COUNT(*) FROM page_events WHERE event_type='demo_view' AND created_at > NOW() - INTERVAL '24 hours';" 2>/dev/null)
REGISTER_VIEWS=$(docker exec masterdesk_db psql -U postgres -d masterdesk -t -A -c "SELECT COUNT(*) FROM page_events WHERE event_type='register_view' AND created_at > NOW() - INTERVAL '24 hours';" 2>/dev/null)
REGISTRATIONS=$(docker exec masterdesk_db psql -U postgres -d masterdesk -t -A -c "SELECT COUNT(*) FROM page_events WHERE event_type='register_success' AND created_at > NOW() - INTERVAL '24 hours';" 2>/dev/null)
REPORT="${REPORT}
Маркетинг за 24ч: демо ${DEMO_VIEWS:-0}, открытий регистрации ${REGISTER_VIEWS:-0}, новых автосервисов ${REGISTRATIONS:-0}
"
if [ "$ALL_OK" == true ]; then
    REPORT="${REPORT}

Всё в порядке"
else
    REPORT="${REPORT}

Есть проблемы, требуется внимание"
fi

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d chat_id="${ADMIN_CHAT_ID}" \
    --data-urlencode "text=${REPORT}" > /dev/null
