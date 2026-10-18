.PHONY: help install lint format typecheck test check demo backtest backtests plot serve docker clean

PY ?= python3

help:  ## show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install:  ## editable install with dev extras + pre-commit hooks
	$(PY) -m pip install -e ".[dev]"
	pre-commit install || true

lint:  ## ruff lint + format check
	ruff check .
	ruff format --check .

format:  ## auto-format and fix
	ruff check . --fix
	ruff format .

typecheck:  ## mypy
	mypy

test:  ## unit tests with coverage gate
	pytest --cov

check: lint typecheck test  ## everything CI runs

demo:  ## score one example hour
	fuzzy-tariff demo --P 12 --A 0.30 --G 0.20

backtest:  ## baseline scenario backtest -> reports/backtest_baseline.md
	fuzzy-tariff backtest --scenario baseline --out reports/backtest_baseline.md

backtests:  ## all synthetic scenarios
	@for s in baseline winter_evening_peak solar_midday_dip flat spike; do \
	  fuzzy-tariff backtest --scenario $$s --out reports/backtest_$$s.md; done

plot:  ## membership-function figure -> reports/membership_functions.png
	fuzzy-tariff plot-mf --out reports/membership_functions.png

serve:  ## run the API with reload
	fuzzy-tariff serve --reload

docker:  ## build the container image
	docker build -t fuzzy-tariff:dev .

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist *.egg-info
