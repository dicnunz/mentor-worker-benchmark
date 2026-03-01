from mentor_worker_benchmark.runner import _extract_diff, _sanitize_mentor_guidance
from mentor_worker_benchmark.tasks.task_codegen_py.task_defs import select_tasks


def test_extract_diff_from_fenced_block() -> None:
    text = """Here is the patch:\n```diff\n--- src/solution.py\n+++ src/solution.py\n@@ -1 +1 @@\n-print('a')\n+print('b')\n```"""
    diff = _extract_diff(text)
    assert diff is not None
    assert diff.startswith("--- src/solution.py")


def test_mentor_violation_is_sanitized() -> None:
    raw = "```python\ndef solve():\n    pass\n```\nTry handling edge cases first."
    sanitized, violated = _sanitize_mentor_guidance(raw)
    assert violated
    assert "edge cases" in sanitized.lower()


def test_task_selection_quick() -> None:
    quick = select_tasks("quick")
    assert len(quick) >= 3
