from mentor_worker_benchmark.runner import _extract_diff, _sanitize_mentor_guidance, _validate_patch_format
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
    assert len(selection.tasks) == 6
    assert all(task.category.startswith("mini_repo_") is False for task in selection.tasks)
    assert all(task.difficulty in {"easy", "medium"} for task in selection.tasks)
    assert any(task.task_id == "v1_ds_algo_003" for task in selection.tasks)


def test_task_selection_default_eval_split_v2() -> None:
    selection = resolve_tasks(task_pack="task_pack_v2", suite=None, legacy_selector=None, seed=1337)
    assert len(selection.tasks) == 160
    splits = {task.split for task in selection.tasks}
    assert splits == {"dev", "test"}
