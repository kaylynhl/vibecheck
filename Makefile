# vibecheck Makefile

PY := python
VENV := .venv
PIP := $(VENV)/bin/pip
PYBIN := $(VENV)/bin/python

.PHONY: help venv install setup fmt lint test serve eval-check groq-baseline clean

help:
	@echo "Targets:"
	@echo "  make setup   - create venv + install deps"
	@echo "  make fmt     - format (black + isort)"
	@echo "  make lint    - lint (ruff)"
	@echo "  make test    - run tests (pytest)"
	@echo "  make serve   - run FastAPI backend (uvicorn, :8000, autoreload)"
	@echo "  make eval-check - check labeled photo counts for CLIP-LoRA"
	@echo "  make groq-baseline - cache Groq predictions for data/eval photos"
	@echo "  make clean   - remove caches + build artifacts"

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@$(PIP) -q install --upgrade pip

install: venv
	@$(PIP) install -r requirements.txt

setup: install
	@$(PYBIN) -m ipykernel install --user --name vibecheck --display-name "vibecheck"
	@echo "Setup complete. Activate with: source .venv/bin/activate"

fmt: venv
	@$(VENV)/bin/black .
	@$(VENV)/bin/isort .

lint: venv
	@$(VENV)/bin/ruff check src tests scripts

test: venv
	@$(VENV)/bin/pytest -q

serve: venv
	@$(PYBIN) scripts/serve.py

eval-check: venv
	@$(PYBIN) scripts/check_eval_dataset.py

groq-baseline: venv
	@$(PYBIN) scripts/export_groq_baseline.py

clean:
	@rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
