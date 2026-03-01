# Task Pack Curation Report

Generated: 2026-03-01T15:24:54.403570+00:00

## Summary
- Task pack: `task_pack_v1`
- Replaced tasks: **298**
- Near-duplicate clusters (before): **9**
- Near-duplicate clusters (after): **10**

## Difficulty Distribution

| Bucket | Before | After |
| --- | --- | --- |
| easy | 105 | 105 |
| medium | 135 | 135 |
| hard | 60 | 60 |

## DEV Baseline Pass Rate (1-turn worker_only)

| Model | Before | After |
| --- | --- | --- |
| phi3:mini | 0.0 | 0.0 |
| qwen2.5-coder:7b | 0.0 | 0.0 |
| average | 0.0 | 0.0 |

## Flagged Reason Counts

- `ambiguous_tests`: 100
- `calibration_bucket_adjustment`: 226
- `duplicate_near`: 224
- `trivial_short_starter`: 200

## Top Duplicate Clusters (Before)

| Cluster | Size | Keeper | Members |
| --- | --- | --- | --- |
| 1 | 50 | `v1_concurrency_basics_005` | v1_concurrency_basics_000, v1_concurrency_basics_001, v1_concurrency_basics_002, v1_concurrency_basics_003, v1_concurrency_basics_004, v1_concurrency_basics_005, ... |
| 2 | 50 | `v1_file_io_serialization_000` | v1_file_io_serialization_000, v1_file_io_serialization_001, v1_file_io_serialization_002, v1_file_io_serialization_003, v1_file_io_serialization_004, v1_file_io_serialization_005, ... |
| 3 | 50 | `v1_multi_file_mini_module_001` | v1_multi_file_mini_module_000, v1_multi_file_mini_module_001, v1_multi_file_mini_module_002, v1_multi_file_mini_module_003, v1_multi_file_mini_module_004, v1_multi_file_mini_module_005, ... |
| 4 | 50 | `v1_numerical_edge_cases_003` | v1_numerical_edge_cases_000, v1_numerical_edge_cases_001, v1_numerical_edge_cases_002, v1_numerical_edge_cases_003, v1_numerical_edge_cases_004, v1_numerical_edge_cases_005, ... |
| 5 | 9 | `v1_string_regex_parsing_004` | v1_string_regex_parsing_004, v1_string_regex_parsing_014, v1_string_regex_parsing_016, v1_string_regex_parsing_018, v1_string_regex_parsing_019, v1_string_regex_parsing_024, ... |
| 6 | 8 | `v1_string_regex_parsing_003` | v1_string_regex_parsing_003, v1_string_regex_parsing_006, v1_string_regex_parsing_010, v1_string_regex_parsing_012, v1_string_regex_parsing_015, v1_string_regex_parsing_022, ... |
| 7 | 8 | `v1_string_regex_parsing_008` | v1_string_regex_parsing_008, v1_string_regex_parsing_009, v1_string_regex_parsing_017, v1_string_regex_parsing_026, v1_string_regex_parsing_029, v1_string_regex_parsing_038, ... |
| 8 | 6 | `v1_string_regex_parsing_011` | v1_string_regex_parsing_011, v1_string_regex_parsing_021, v1_string_regex_parsing_031, v1_string_regex_parsing_032, v1_string_regex_parsing_041, v1_string_regex_parsing_042 |
| 9 | 2 | `v1_string_regex_parsing_002` | v1_string_regex_parsing_002, v1_string_regex_parsing_030 |
