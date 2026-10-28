.PHONY: up down build logs migrate revision test fe-dev be-shell db-shell fmt

# --- Stack ---
up:            ## Build & start the full stack
	docker compose up --build

down:          ## Stop stack (keep volumes)
	docker compose down

clean:         ## Stop stack and drop volumes (fresh DB)
	docker compose down -v

logs:
	docker compose logs -f backend

# --- Database / migrations ---
migrate:       ## Apply latest migrations inside the backend container
	docker compose exec backend alembic upgrade head

revision:      ## Autogenerate a migration: make revision m="add trips"
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

db-shell:
	docker compose exec db psql -U travelos -d travelos

# --- Tests ---
test:          ## Run backend tests inside the container (needs DB up)
	docker compose exec backend pytest -q

# --- Convenience ---
be-shell:
	docker compose exec backend bash

fe-dev:        ## Run the frontend locally (outside docker)
	cd frontend && npm install && npm run dev
