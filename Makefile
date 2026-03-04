.PHONY: install lint test test-fast run compose-up compose-down eval

install:
	pip install -r requirements.txt pytest ruff black

lint:
	ruff check app tests eval

format:
	black app tests eval

test:
	pytest

test-fast:
	pytest tests/test_acl_rules.py tests/test_guardrails.py tests/test_chunking.py

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8080

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v

eval:
	python eval/run_eval.py
