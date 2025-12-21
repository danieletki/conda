# MercatoPro Makefile per Docker

# Variabili di configurazione
PROJECT_NAME = mercatopro
COMPOSE_FILE = docker-compose.yml
DOCKER_COMPOSE = docker-compose -f $(COMPOSE_FILE)
PYTHON_CONTAINER = $(PROJECT_NAME)_web_1

# Colori per output
YELLOW = \033[1;33m
GREEN = \033[1;32m
RED = \033[1;31m
NC = \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

.PHONY: help
help: ## Mostra questo help
    @echo "$(GREEN)MercatoPro Docker Management$(NC)"
    @echo "$(YELLOW)Usage: make [target]$(NC)"
    @echo ""
    @echo "$(YELLOW)Targets:$(NC)"
    @awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: setup
setup: ## Setup iniziale del progetto
    @echo "$(YELLOW)🔧 Setup iniziale MercatoPro...$(NC)"
    cp .env.example .env
    @echo "$(GREEN)✅ File .env creato da .env.example$(NC)"
    @echo "$(GREEN)✅ Modifica .env se necessario, poi esegui: make up$(NC)"

.PHONY: build
build: ## Costruisce le immagini
    @echo "$(YELLOW)🔨 Build delle immagini...$(NC)"
    $(DOCKER_COMPOSE) build
    @echo "$(GREEN)✅ Build completata$(NC)"

.PHONY: up
up: ## Avvia tutti i servizi Docker
    @echo "$(YELLOW)🚀 Avvio servizi MercatoPro...$(NC)"
    $(DOCKER_COMPOSE) up -d
    @echo "$(GREEN)✅ Servizi avviati!$(NC)"
    @echo "$(YELLOW)Attendere che i servizi siano pronti...$(NC)"
    sleep 10
    @echo "$(GREEN)✅ Applicazione disponibile su: http://localhost$(NC)"

.PHONY: down
down: ## Ferma tutti i servizi
    @echo "$(YELLOW)🛑 Arresto servizi...$(NC)"
    $(DOCKER_COMPOSE) down
    @echo "$(GREEN)✅ Servizi fermati$(NC)"

.PHONY: restart
restart: down up ## Riavvia tutti i servizi

.PHONY: rebuild
rebuild: ## Ricostruisce le immagini e riavvia
    @echo "$(YELLOW)🔨 Rebuild delle immagini...$(NC)"
    $(DOCKER_COMPOSE) build --no-cache
    @echo "$(GREEN)✅ Immagini ricostruite$(NC)"

.PHONY: logs
logs: ## Mostra i log di tutti i servizi
    $(DOCKER_COMPOSE) logs -f

.PHONY: logs-web
logs-web: ## Mostra i log del web server
    $(DOCKER_COMPOSE) logs -f web

.PHONY: logs-db
logs-db: ## Mostra i log del database
    $(DOCKER_COMPOSE) logs -f db

.PHONY: status
status: ## Mostra lo stato dei servizi
    @echo "$(YELLOW)📊 Stato servizi:$(NC)"
    $(DOCKER_COMPOSE) ps

.PHONY: ps
ps: status ## Alias per status

.PHONY: shell
shell: ## Apre una shell nel container web
    @echo "$(YELLOW)🐚 Apertura shell nel container web...$(NC)"
    $(DOCKER_COMPOSE) exec web /bin/bash

.PHONY: dj-shell
dj-shell: ## Apre Django shell
    @echo "$(YELLOW)🐍 Apertura Django shell...$(NC)"
    $(DOCKER_COMPOSE) exec web python manage.py shell

.PHONY: migrate
migrate: ## Esegue le migrazioni Django
    @echo "$(YELLOW)📦 Esecuzione migrazioni...$(NC)"
    $(DOCKER_COMPOSE) exec web python manage.py migrate
    @echo "$(GREEN)✅ Migrazioni completate$(NC)"

.PHONY: seed
seed: ## Popola il database con dati di test
    @echo "$(YELLOW)🌱 Popolamento dati di test...$(NC)"
    $(DOCKER_COMPOSE) exec web python manage.py seed_data
    @echo "$(GREEN)✅ Dati di test creati$(NC)"

.PHONY: createsuperuser
createsuperuser: ## Crea superuser Django
    @echo "$(YELLOW)👤 Creazione superuser...$(NC)"
    $(DOCKER_COMPOSE) exec web python manage.py createsuperuser

.PHONY: collectstatic
collectstatic: ## Raccoglie i file statici
    @echo "$(YELLOW)📁 Raccogliendo file statici...$(NC)"
    $(DOCKER_COMPOSE) exec web python manage.py collectstatic --noinput
    @echo "$(GREEN)✅ File statici raccolti$(NC)"

.PHONY: test
test: ## Esegue i test Django
    @echo "$(YELLOW)🧪 Esecuzione test...$(NC)"
    $(DOCKER_COMPOSE) exec web python manage.py test

.PHONY: test-docker
test-docker: ## Esegue test completi del deployment Docker
    @echo "$(YELLOW)🧪 Esecuzione test Docker deployment...$(NC)"
    ./test_docker.sh

.PHONY: clean
clean: ## Rimuove container e volumi (CANCELLA TUTTI I DATI)
    @echo "$(RED)⚠️  ATTENZIONE: Rimozione completa di tutti i dati!$(NC)"
    @echo "$(RED)Questo comando rimuoverà:$(NC)"
    @echo "$(RED)  - Tutti i container$(NC)"
    @echo "$(RED)  - Tutti i volumi$(NC)"
    @echo "$(RED)  - Database PostgreSQL$(NC)"
    @echo "$(RED)  - File media$(NC)"
    @read -p "$(YELLOW)Sei sicuro? (y/N): $(NC)" confirm && [ "$$confirm" = "y" ]
    $(DOCKER_COMPOSE) down -v
    $(DOCKER_COMPOSE) rm -f
    @echo "$(GREEN)✅ Pulizia completata$(NC)"

.PHONY: reset
reset: down clean up ## Reset completo del progetto
    @echo "$(GREEN)🔄 Reset completo completato$(NC)"

.PHONY: backup-db
backup-db: ## Backup del database
    @echo "$(YELLOW)💾 Backup database...$(NC)"
    $(DOCKER_COMPOSE) exec db pg_dump -U mercato_user mercato_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
    @echo "$(GREEN)✅ Backup salvato$(NC)"

.PHONY: restore-db
restore-db: ## Restore del database (richiede file .sql)
    @if [ -z "$(FILE)" ]; then \
        echo "$(RED)❌ Specifica il file di backup: make restore-db FILE=backup.sql$(NC)"; \
        exit 1; \
    fi
    @echo "$(YELLOW)🔄 Restore database da $(FILE)...$(NC)"
    $(DOCKER_COMPOSE) exec -T db psql -U mercato_user mercato_db < $(FILE)
    @echo "$(GREEN)✅ Database ripristinato$(NC)"

.PHONY: inspect
inspect: ## Ispeziona il container web
    @echo "$(YELLOW)🔍 Ispezione container web...$(NC)"
    docker inspect $(PYTHON_CONTAINER)

.PHONY: stats
stats: ## Mostra statistiche di utilizzo risorse
    @echo "$(YELLOW)📈 Statistiche risorse Docker...$(NC)"
    docker stats

.PHONY: health
health: ## Controlla la salute dei servizi
    @echo "$(YELLOW)🏥 Controllo salute servizi...$(NC)"
    @echo "$(YELLOW)Database:$(NC)"
    $(DOCKER_COMPOSE) exec db pg_isready -U mercato_user || echo "$(RED)❌ Database non pronto$(NC)"
    @echo "$(YELLOW)Redis:$(NC)"
    $(DOCKER_COMPOSE) exec redis redis-cli ping || echo "$(RED)❌ Redis non pronto$(NC)"
    @echo "$(YELLOW)Web:$(NC)"
    @curl -f http://localhost/admin/ > /dev/null 2>&1 && echo "$(GREEN)✅ Web accessibile$(NC)" || echo "$(RED)❌ Web non accessibile$(NC)"

.PHONY: nginx-logs
nginx-logs: ## Mostra i log di Nginx
    $(DOCKER_COMPOSE) logs -f nginx

.PHONY: celery-logs
celery-logs: ## Mostra i log di Celery
    $(DOCKER_COMPOSE) logs -f celery-worker celery-beat

.PHONY: update
update: ## Aggiorna il progetto (pull + rebuild + up)
    @echo "$(YELLOW)🔄 Aggiornamento progetto...$(NC)"
    git pull
    $(DOCKER_COMPOSE) pull
    $(DOCKER_COMPOSE) build
    $(DOCKER_COMPOSE) up -d
    @echo "$(GREEN)✅ Progetto aggiornato$(NC)"

.PHONY: dev-setup
dev-setup: setup up migrate collectstatic ## Setup completo per sviluppo
    @echo "$(GREEN)🎉 Setup sviluppo completato!$(NC)"
    @echo "$(YELLOW)Accesso admin: http://localhost/admin$(NC)"
    @echo "$(YELLOW)Username: admin, Password: admin123$(NC)"

.PHONY: production-check
production-check: ## Controlla configurazione produzione
    @echo "$(YELLOW)🔒 Controllo configurazione produzione...$(NC)"
    @echo "Debug mode:"
    @$(DOCKER_COMPOSE) exec web python -c "from django.conf import settings; print('DEBUG:', settings.DEBUG)"
    @echo "Secret Key (primi 20 caratteri):"
    @$(DOCKER_COMPOSE) exec web python -c "from django.conf import settings; print(settings.SECRET_KEY[:20] + '...')"
    @echo "Allowed Hosts:"
    @$(DOCKER_COMPOSE) exec web python -c "from django.conf import settings; print(settings.ALLOWED_HOSTS)"

# Target speciali che non corrispondono a file
.PHONY: .PHONY