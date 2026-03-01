.PHONY: setup quick lock generate-pack sanity run-quick run-dev run-test run-all leaderboard compare lint test

setup:
	python -m mentor_worker_benchmark setup

quick:
	python -m mentor_worker_benchmark run --suite quick --repro

lock:
	. .venv/bin/activate && pip-compile --generate-hashes --output-file requirements.lock requirements.in

generate-pack:
	python -m mentor_worker_benchmark.tasks.task_pack_v1.generate_task_pack --seed 1337

sanity:
	python -m mentor_worker_benchmark sanity --task-pack task_pack_v1 --suite all --seed 1337

run-quick:
	python -m mentor_worker_benchmark run --suite quick --max-turns 2 --repro

run-dev:
	python -m mentor_worker_benchmark run --suite dev --max-turns 4 --repro

run-test:
	python -m mentor_worker_benchmark run --suite test --max-turns 4 --repro

run-all:
	python -m mentor_worker_benchmark run --suite all --max-turns 4 --repro

leaderboard:
	python -m mentor_worker_benchmark leaderboard --results results/results.json --output results/leaderboard.md

compare:
	python -m mentor_worker_benchmark compare --before results/before.json --after results/results.json

lint:
	python -m ruff check mentor_worker_benchmark

test:
	python -m pytest
