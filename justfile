init:
    python -m venv .venv
    echo "CHURCHSUITE_CLIENT_ID='pyymykxprafwllbrpsfu'\nCHURCHSUITE_CLIENT_SECRET='redacted'\n" > .env
    pip3 install poetry
    poetry install

manage *FLAGS:
    python manage.py {{FLAGS}}

dev:
    python manage.py runserver 8001
