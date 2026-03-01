.PHONY: setup run-quick run-full leaderboard lint test

setup:
	python -m mentor_worker_benchmark setup

run-quick:
	python -m mentor_worker_benchmark run --tasks quick --max-turns 2

run-full:
	python -m mentor_worker_benchmark run --tasks all --max-turns 4

leaderboard:
	python -m mentor_worker_benchmark leaderboard --results results/results.json --output results/leaderboard.md

lint:
	python -m ruff check mentor_worker_benchmark

test:
	python -m pytest
