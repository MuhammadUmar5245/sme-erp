# SME-ERP commands (all run through Docker Compose). Windows without make: use .\make.ps1 <target>.
COMPOSE = docker compose
RUN = $(COMPOSE) run --rm web

.PHONY: help env up down build logs migrate makemigrations seed test shell createsuperuser backup restore cert

help:
	@echo "make up | down | migrate | seed | test | backup | restore | logs | shell | cert"

env:
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example - edit the secrets.")

up: env
	$(COMPOSE) up -d --build
	@echo "SME-ERP is starting at https://localhost"

down:
	$(COMPOSE) down

build: env
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=100

migrate: env
	$(RUN) python manage.py migrate

makemigrations: env
	$(RUN) python manage.py makemigrations

seed: env
	$(RUN) python manage.py seed_demo --reset

test: env
	$(RUN) pytest

shell: env
	$(RUN) python manage.py shell

createsuperuser: env
	$(RUN) python manage.py createsuperuser

cert:
	$(COMPOSE) run --rm -e FORCE=1 certs

backup:
	$(COMPOSE) exec cron /scripts/backup.sh

restore:
	$(COMPOSE) exec cron /scripts/restore.sh $(FILE)
