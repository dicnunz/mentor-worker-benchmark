import re
from typing import Any

from mentor_worker_benchmark.runner import (
    _capture_runtime_context,
    _extract_diff,
    _sanitize_mentor_guidance,
    _validate_patch_format,
)
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
    assert "failing assertions" in sanitized.lower() or "focus" in sanitized.lower()
    assert "def solve" not in sanitized


def test_patch_with_path_traversal_is_rejected() -> None:
    raw = """```diff
--- ../outside.py
+++ ../outside.py
@@ -1 +1 @@
-print('a')
+print('b')
```"""
    assert _extract_diff(raw) is None


def test_extract_diff_repairs_common_malformed_hunk_header() -> None:
    raw = """```diff
--- src/solution.py
+++ src/solution.py
@@ -1,4 +++ b/src/solution.py
-def solve():
+def solve():
     pass
```"""
    diff = _extract_diff(raw)
    assert diff is not None
    assert "@@ -1,2 +1,2 @@" in diff


def test_extract_diff_repairs_hunk_counts_and_missing_context_prefixes() -> None:
    raw = """```diff
--- src/solution.py
+++ src/solution.py
@@ -1,4 +1,4 @@
def solve():
-    return 0
+    return 1
```"""
    diff = _extract_diff(raw)
    assert diff is not None
    assert "@@ -1,2 +1,2 @@" in diff
    assert "\n def solve():" in diff


def test_validate_patch_rejects_mismatched_hunk_counts() -> None:
    raw = """--- src/solution.py
+++ src/solution.py
@@ -1,6 +1,20 @@
 def solve():
-    return 0
+    return 1
"""
    valid, reason = _validate_patch_format(raw)
    assert not valid
    assert "Hunk line counts do not match header" in reason


def test_task_selection_quick() -> None:
    selection = resolve_tasks(task_pack="task_pack_v1", suite="quick", legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 18


def test_task_selection_default_eval_split() -> None:
    selection = resolve_tasks(task_pack="task_pack_v1", suite=None, legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 100
    splits = {task.split for task in selection.tasks}
    assert splits == {"dev", "test"}


def test_task_selection_quick_v2() -> None:
    selection = resolve_tasks(task_pack="task_pack_v2", suite="quick", legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 30
    assert all(task.quick for task in selection.tasks)

    selection_again = resolve_tasks(task_pack="task_pack_v2", suite="quick", legacy_selector=None, seed=1337)
    assert [task.task_id for task in selection.tasks] == [task.task_id for task in selection_again.tasks]


def test_task_selection_default_eval_split_v2() -> None:
    selection = resolve_tasks(task_pack="task_pack_v2", suite=None, legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 208
    splits = {task.split for task in selection.tasks}
    assert splits == {"dev", "test"}


def test_task_selection_dev50_v2() -> None:
    selection = resolve_tasks(task_pack="task_pack_v2", suite="dev50", legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 50
    assert {task.split for task in selection.tasks} == {"dev"}

    selection_again = resolve_tasks(task_pack="task_pack_v2", suite="dev50", legacy_selector=None, seed=1337)
    assert [task.task_id for task in selection.tasks] == [task.task_id for task in selection_again.tasks]


def test_task_selection_dev10_v2() -> None:
    selection = resolve_tasks(task_pack="task_pack_v2", suite="dev10", legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 10
    assert {task.split for task in selection.tasks} == {"dev"}

    selection_again = resolve_tasks(task_pack="task_pack_v2", suite="dev10", legacy_selector=None, seed=1337)
    assert [task.task_id for task in selection.tasks] == [task.task_id for task in selection_again.tasks]


def test_capture_runtime_context_records_pip_hash_and_task_pack(monkeypatch: Any) -> None:
    class _DummyClient:
        def runtime_metadata(self, model_names: list[str]) -> dict[str, Any]:
            return {"models": model_names}

    monkeypatch.setattr(
        "mentor_worker_benchmark.runner._capture_pip_freeze_hash",
        lambda: ("a" * 64, 12),
    )
    monkeypatch.setattr("mentor_worker_benchmark.runner._git_commit_hash", lambda: "de5a929")
    monkeypatch.setattr("mentor_worker_benchmark.runner._git_is_dirty", lambda: False)

    context = _capture_runtime_context(
        mentor_client=_DummyClient(),
        worker_client=_DummyClient(),
        mentor_models=["m1"],
        worker_models=["w1"],
        mentor_provider="ollama",
        worker_provider="ollama",
        task_pack_id="task_pack_v2",
        task_pack_version="2.0.0",
        task_pack_source="registry",
        task_pack_hash="b" * 64,
        task_pack_manifest_path="mentor_worker_benchmark/tasks/task_pack_v2/metadata.json",
    )

    assert context["python"]["pip_freeze_sha256"] == "a" * 64
    assert context["python"]["pip_freeze_line_count"] == 12
    assert re.fullmatch(r"[0-9a-f]{64}", context["python"]["pip_freeze_sha256"]) is not None
    assert context["task_pack"]["id"] == "task_pack_v2"
    assert context["task_pack"]["source"] == "registry"
    assert context["task_pack"]["hash"] == "b" * 64
