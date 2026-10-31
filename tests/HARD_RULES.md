# Hard rules and their tests

Each hard rule in SPEC section 2 has at least one named test, wherever it lives (SPEC 13.2). `tests/invariants/test_hard_rules_map.py` checks that every rule has a row and that every test named in a `done` or `partial` row exists.

- **Tests** names test modules that exist now.
- **Planned** names the modules later milestones add, from the milestone files. The names may change when that milestone is built.
- **Status** is `done`, `partial` (some tests exist and more arrive later), or `arrives in Mxx`.

| Rule | In a few words | Tests | Planned | Status |
| --- | --- | --- | --- | --- |
| H1 | No network capability | `tests/offline/test_guard_runtime.py`, `tests/offline/test_open_file_allowance.py`, `tests/offline/test_static_scan.py`, `tests/offline/test_lockfile.py`, `tests/offline/test_import_graph.py`, `tests/offline/test_guard_matches_rules.py`, `tests/audit/test_A20_no_launchers.py`, `tests/rules/test_P_READ_10_no_urls.py` | M05 `tests/offline/test_guard_geosupport_dirs.py`; M14 `tests/offline/test_bundle.py`, `tests_windows/test_firewall_probe.py` | partial |
| H2 | No AI | `tests/offline/test_lockfile.py`, `tests/offline/test_static_scan.py`, `tests/offline/test_guard_runtime.py` | M14 `tests/offline/test_bundle.py` | partial |
| H3 | Deterministic outputs | `tests/invariants/test_read_determinism.py`, `tests/golden/test_example_data.py` | M04 `tests/invariants/test_standardize_properties.py`; M05 `tests/invariants/test_geo_properties.py`; M08 `tests/invariants/test_determinism.py` | partial |
| H4 | Every row is accounted for, in two balances: rows received = counted + not counted yet + set aside, and counted = mapped + counted but not mapped | `tests/invariants/test_row_accounting_h4.py`, `tests/rules/test_P_READ_7_accounting.py`, `tests/audit/test_A09_rows_outside_tables.py`, `tests/audit/test_C23_blank_line_and_comma_row.py` | M08 `tests/invariants/test_balance.py` (both balances on counted rows) | partial |
| H5 | Nothing is joined on a guess | | M06 `tests/invariants/test_identity_properties.py` | arrives in M06 |
| H6 | Originals are kept | | M03 tidy-up rule tests in `tests/rules/`; M04 `tests/invariants/test_standardize_properties.py` | arrives in M03 |
| H7 | No typing values in review | | M08 `tests/rules/test_reviewers.py`; M12 reviewer screen tests in `tests/ui/` | arrives in M08 |
| H8 | No client values in the audit, logs or progress messages | `tests/invariants/test_h08_progress_message.py`, `tests/unit/test_dev_counts_only.py` | M09 `tests/rules/test_audit_logs.py` | partial |
| H9 | Client values reach disk only in downloaded files | `tests/invariants/test_h09_secret_not_leaked.py`, `tests/unit/test_secret_store.py` | M09 `tests/rules/test_store.py`, `tests/rules/test_outputs.py` | partial |
| H10 | Unmapped columns never leave the tool | `tests/rules/test_P_READ_9_sensitive.py` | M09 `tests/rules/test_outputs.py` | partial |
| H11 | Every claim on screen is true and tested | `tests/copy/test_claims_have_tests.py`, `tests/copy/test_registry.py`, `tests/unit/test_brand.py` | M10 `tests/copy/test_dataline_claims.py` | done |
| H12 | Decisions are tied to records, not positions | `tests/invariants/test_key_stability.py`, `tests/unit/test_keys.py` | M08 `tests/rules/test_counts.py` | partial |
| H13 | Results never describe an older state | | M08 `tests/rules/test_counts.py` (staleness cases) | arrives in M08 |
| H14 | Every long action shows progress | | M10 progress widget tests in `tests/ui/` | arrives in M10 |
| H15 | Confidence comes from checked facts only | | M08 `tests/rules/test_counts.py` (confidence cases) | arrives in M08 |
| H16 | Wording: American spelling, thousands separators, no emoji, exclamation marks or em dashes | `tests/copy/test_lint.py`, `tests/copy/test_registry.py` | M10 and later screen copy runs through the same lint | done |
