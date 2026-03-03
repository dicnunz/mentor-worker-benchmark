FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.lock /app/requirements.lock
RUN python -m pip install --upgrade pip \
    && pip install --require-hashes -r /app/requirements.lock

COPY pyproject.toml README.md /app/
COPY mentor_worker_benchmark /app/mentor_worker_benchmark
RUN pip install .

CMD ["python", "-m", "mentor_worker_benchmark", "sanity", "--task-pack", "task_pack_v2", "--suite", "quick", "--seed", "1337"]
