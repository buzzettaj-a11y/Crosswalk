# Audit findings index

Every finding in `docs/audit/` (SPEC 13.3), with the milestone that closes it (from `docs/milestones/README.md`) and its regression test.
A finding listed under more than one milestone names every test that closes it. `tests/audit/test_index_complete.py` keeps this table in step with the audit files.

| ID | Severity | Milestone | Test | Status |
| --- | --- | --- | --- | --- |
| A-01 | High | M09 | arrives in M09 | pending |
| A-02 | High | M09 | arrives in M09 | pending |
| A-03 | High | M09 | arrives in M09 | pending |
| A-04 | High | M09 | arrives in M09 | pending |
| A-05 | High | M06 | `tests/audit/test_A05_same_id_merge.py` | done |
| A-06 | High | M08 | arrives in M08 | pending |
| A-07 | High | M08 | arrives in M08 | pending |
| A-08 | High | M09 | arrives in M09 | pending |
| A-09 | High | M01 | `tests/audit/test_A09_rows_outside_tables.py` | done |
| A-10 | High | M09 | arrives in M09 | pending |
| A-11 | Medium | M04 | `tests/audit/test_A11_original_kept.py` | done |
| A-12 | Medium | M08 | arrives in M08 | pending |
| A-13 | Medium | M01 | `tests/audit/test_A13_bad_file_does_not_block.py` | done |
| A-14 | Medium | M05 | `tests/audit/test_A14_seed_printed.py` | done |
| A-15 | Medium | M09 | arrives in M09 | pending |
| A-16 | Medium | M10 | arrives in M10 | pending |
| A-17 | Medium | M14 | arrives in M14 | pending |
| A-18 | Medium | M11 | arrives in M11 | pending |
| A-19 | Medium | M10 | arrives in M10 | pending |
| A-20 | Medium | M00, M14 | `tests/audit/test_A20_no_launchers.py` | done |
| A-21 | Low | M10 | arrives in M10 | pending |
| A-22 | Low | M08 | arrives in M08 | pending |
| A-23 | Low | M10 | arrives in M10 | pending |
| A-24 | Low | M09 | arrives in M09 | pending |
| A-25 | Low | M00, M15 | arrives in M15 | pending |
| B-01 | High | M04 | `tests/audit/test_B01_placeholders.py` | done |
| B-02 | High | M01 | `tests/audit/test_B02_cp1252_names.py` | done |
| B-03 | High | M04 | `tests/audit/test_B03_nassau_zips.py` | done |
| B-04 | High | M04 | `tests/audit/test_B04_non_nyc_zip.py` | done |
| B-05 | High | M04 | `tests/audit/test_B05_non_nyc_place_names.py` | done |
| B-06 | High | M03 | `tests/audit/test_B06_calculated_zip.py` | done |
| B-07 | High | M03 | `tests/audit/test_B07_nine_digit_zip.py` | done |
| B-08 | High | M03 | `tests/audit/test_B08_street_keeps_concourse.py` | done |
| B-09 | High | M03 | `tests/audit/test_B09_spaced_hyphen_house_number.py` | done |
| B-10 | High | M03 | `tests/audit/test_B10_trailing_segment_kept.py` | done |
| B-11 | High | M03 | `tests/audit/test_B11_particles_and_double_surnames.py` | done |
| B-12 | High | M03 | `tests/audit/test_B12_titles_and_suffixes.py` | done |
| B-13 | High | M04 | `tests/audit/test_B13_day_month_order.py` | done |
| B-14 | High | M04 | `tests/audit/test_B14_two_digit_year.py` | done |
| B-15 | High | M04 | `tests/audit/test_B15_future_dob.py` | done |
| B-16 | High | M04 | `tests/audit/test_B16_five_digits_not_a_date.py` | done |
| B-17 | High | M05 | `tests/audit/test_B17_fuzzy_geocode.py` | done |
| B-18 | High | M05 | `tests/audit/test_B18_privacy_offset.py` | done |
| B-19 | High | M05 | `tests/audit/test_B19_district_holes.py` | done |
| B-20 | High | M07 | `tests/audit/test_B20_unconfirmed_proposals.py` | done |
| B-21 | High | M02 | `tests/audit/test_B21_first_match_by_position.py` | done |
| B-22 | High | M02 | `tests/audit/test_B22_program_date_and_id.py` | done |
| B-23 | High | M02 | `tests/audit/test_B23_split_does_not_hijack.py`, `tests/audit/test_B23_end_to_end.py` | done |
| B-24 | Medium | M01 | `tests/audit/test_B24_invisible_characters.py`, `tests/rules/test_P_READ_3_unreadable_character.py` | done |
| B-25 | Medium | M04 | `tests/audit/test_B25_name_placeholders.py` | done |
| B-26 | Medium | M04 | `tests/audit/test_B26_unicode_zip.py` | done |
| B-27 | Medium | M04 | `tests/audit/test_B27_address_text_disagrees.py` | done |
| B-28 | Medium | M04 | `tests/audit/test_B28_place_stays_out_of_street.py` | done |
| B-29 | Medium | M03 | `tests/audit/test_B29_unit_then_city.py` | done |
| B-30 | Medium | M03 | `tests/audit/test_B30_lone_letter_units.py` | done |
| B-31 | Medium | M04 | `tests/audit/test_B31_unrecognized_city_kept.py` | done |
| B-32 | Medium | M03 | `tests/audit/test_B32_extra_name_tokens.py` | done |
| B-33 | Medium | M03 | `tests/audit/test_B33_middle_initial_placeholders.py` | done |
| B-34 | Medium | M05 | `tests/audit/test_B34_fill_proposals.py` | done |
| B-35 | Medium | M05 | `tests/audit/test_B35_verified_label.py` | done |
| B-36 | Medium | M06 | `tests/audit/test_B36_same_id_across_files.py` | done |
| B-37 | Medium | M06 | `tests/audit/test_B37_identical_record.py` | done |
| B-38 | Medium | M06 | `tests/audit/test_B38_saved_copy_decision.py` | done |
| B-39 | Medium | M06 | `tests/audit/test_B39_accent_folding.py` | done |
| B-40 | Medium | M07 | `tests/audit/test_B40_program_proposals.py` | done |
| B-41 | Low | M04 | `tests/audit/test_B41_marble_hill.py` | done |
| B-42 | Low | M03 | `tests/audit/test_B42_rear_and_front.py` | done |
| B-43 | Low | M04 | `tests/audit/test_B43_name_case.py` | done |
| B-44 | Low | M04 | `tests/audit/test_B44_summary_surnames.py` | done |
| B-45 | Low | M05 | `tests/audit/test_B45_early_failure_offset.py` | done |
| B-46 | Low | M05 | `tests/audit/test_B46_district_note.py` | done |
| B-47 | Low | M06 | `tests/audit/test_B47_default_copy_rule.py` | done |
| B-48 | Low | M02 | `tests/audit/test_B48_last_visit.py` | done |
| B-49 | Low | M02 | `tests/audit/test_B49_address_line_2.py` | done |
| C-01 | High | M06 | `tests/audit/test_C01_auto_join_score.py` | done |
| C-02 | High | M06 | `tests/audit/test_C02_same_system_id.py` | done |
| C-03 | High | M08 | arrives in M08 | pending |
| C-04 | High | M08 | arrives in M08 | pending |
| C-05 | High | M07 | `tests/audit/test_C05_fast_vs_staged.py` | done |
| C-06 | High | M08 | arrives in M08 | pending |
| C-07 | High | M08 | arrives in M08 | pending |
| C-08 | High | M08 | arrives in M08 | pending |
| C-09 | High | M08 | arrives in M08 | pending |
| C-10 | High | M05 | `tests/audit/test_C10_gazetteer_crash.py` | done |
| C-11 | High | M09 | arrives in M09 | pending |
| C-12 | Medium | M08 | arrives in M08 | pending |
| C-13 | Medium | M07 | `tests/audit/test_C13_ungroup_own_name.py` | done |
| C-14 | Medium | M08 | arrives in M08 | pending |
| C-15 | Medium | M08 | arrives in M08 | pending |
| C-16 | Medium | M08 | arrives in M08 | pending |
| C-17 | Medium | M06 | `tests/audit/test_C17_client_id_scope.py` | done |
| C-18 | Medium | M08 | arrives in M08 | pending |
| C-19 | Medium | M07 | `tests/audit/test_C19_without_program.py` | done |
| C-20 | Medium | M06 | `tests/audit/test_C20_master_id_stability.py` | done |
| C-21 | Medium | M06 | `tests/audit/test_C21_identity_verdict_audit.py` | done |
| C-22 | Medium | M09 | arrives in M09 | pending |
| C-23 | Medium | M01 | `tests/audit/test_C23_blank_line_and_comma_row.py` | done |
| C-24 | Medium | M06 | `tests/audit/test_C24_address_key.py` | done |
| C-25 | Low | M05 | `tests/audit/test_C25_shared_stream.py` | done |
| C-26 | Low | M09 | arrives in M09 | pending |
| C-27 | Low | M09 | arrives in M09 | pending |
