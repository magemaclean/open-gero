.PHONY: test api web compose

test:
	pytest

api:
	PYTHONPATH=apps/api uvicorn opengero.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

compose:
	docker compose up --build
