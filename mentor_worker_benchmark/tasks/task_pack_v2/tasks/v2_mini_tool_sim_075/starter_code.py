def summarize_from_report(path: str, min_severity: str = "info") -> dict[str, object]:
    """Reference entrypoint for this task.

    The benchmark harness executes tests against src/pipeline.py.
    """
    raise NotImplementedError("Implement in src/pipeline.py and related src modules.")
