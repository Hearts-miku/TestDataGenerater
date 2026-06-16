.PHONY: install dev build test clean

install:
	cd backend && uv sync
	cd frontend && pnpm install

dev:
	@echo "Starting backend on :8000 and frontend on :5173"
	cd backend && PYTHONPATH=. uv run uvicorn main:app --port 8000 --reload &
	cd frontend && pnpm dev

build:
	cd frontend && pnpm build

test:
	cd backend && PYTHONPATH=. uv run pytest ../tests/phase1/ -v

clean:
	rm -rf frontend/dist backend/data/dataforge.duckdb
