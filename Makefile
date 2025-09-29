lint:
	uv run ruff format .
	uv run ruff check . --fix
	
dev:
	uv run uvicorn main:app --reload