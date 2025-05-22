init: && activate
    python -m venv .venv
    echo "CHURCHSUITE_CLIENT_ID='pyymykxprafwllbrpsfu'\nCHURCHSUITE_CLIENT_SECRET='redacted'\n" > .env
    pip3 install poetry
    poetry install

activate:
    source .venv/bin/activate

manage *FLAGS:
    python manage.py {{FLAGS}}

dev: && activate
    python manage.py 8001
