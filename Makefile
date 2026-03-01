.PHONY: setup generate-pack sanity run-quick run-dev run-test run-all leaderboard lint test

setup:
	python -m mentor_worker_benchmark setup

generate-pack:
	python -m mentor_worker_benchmark.tasks.task_pack_v1.generate_task_pack --seed 1337

sanity:
	python -m mentor_worker_benchmark sanity --task-pack task_pack_v1 --suite all --seed 1337

run-quick:
	python -m mentor_worker_benchmark run --suite quick --max-turns 2

run-dev:
	python -m mentor_worker_benchmark run --suite dev --max-turns 4

run-test:
	python -m mentor_worker_benchmark run --suite test --max-turns 4

run-all:
	python -m mentor_worker_benchmark run --suite all --max-turns 4

leaderboard:
	python -m mentor_worker_benchmark leaderboard --results results/results.json --output results/leaderboard.md

lint:
	python -m ruff check mentor_worker_benchmark

test:
	python -m pytest
