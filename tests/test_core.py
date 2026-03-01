from mentor_worker_benchmark.runner import _extract_diff, _sanitize_mentor_guidance
from mentor_worker_benchmark.tasks.task_registry import resolve_tasks


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
    selection = resolve_tasks(task_pack="task_pack_v1", suite="quick", legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 18


def test_task_selection_default_eval_split() -> None:
    selection = resolve_tasks(task_pack="task_pack_v1", suite=None, legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 100
    splits = {task.split for task in selection.tasks}
    assert splits == {"dev", "test"}
