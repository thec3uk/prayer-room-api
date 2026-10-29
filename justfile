init:
    python -m venv .venv
    echo "CHURCHSUITE_CLIENT_ID='pyymykxprafwllbrpsfu'\nCHURCHSUITE_CLIENT_SECRET='redacted'\n" > .env
    pip3 install poetry
    poetry install

manage *FLAGS:
    python manage.py {{FLAGS}}

worker:
    celery -A prayer_room_api worker --loglevel=info

# Start the dev server in the background; `just logs` follows it, `just stop` ends it.
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -f .dev.pid ] && kill -0 "$(cat .dev.pid)" 2>/dev/null; then
        echo "already running (pid $(cat .dev.pid))"; exit 0
    fi
    set -m  # own process group, so stop also ends the server's children
    nohup .venv/bin/python manage.py runserver 8001 > .dev.log 2>&1 &
    echo $! > .dev.pid
    sleep 2
    kill -0 "$(cat .dev.pid)" 2>/dev/null || { cat .dev.log; rm -f .dev.pid; exit 1; }
    echo "prayer-room-api on http://localhost:8001 (pid $(cat .dev.pid)); just logs to follow"

stop:
    #!/usr/bin/env bash
    [ -f .dev.pid ] || { echo "not running"; exit 0; }
    kill -- -"$(cat .dev.pid)" 2>/dev/null || true
    rm -f .dev.pid

logs:
    tail -f .dev.log

# Bring the sqlite dev database up to date.
seed:
    .venv/bin/python manage.py migrate
