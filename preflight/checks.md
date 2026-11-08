# Offline checks

Projected API cost: $0. Actual API cost: $0.

- pass: forced prompt is byte-identical to the old static text (`test_forced_prompt_is_the_old_static_text`)
- pass: neutral first-turn prompt has no load or skill outside the tool (`test_neutral_first_turn_has_no_load_or_skill_outside_the_tool`)
- pass: opaque load_skill returns the body, hides canonical names, and scores the same (`test_opaque_load_hides_canonical_names_and_scores_the_same`)
- pass: wikisel proposer files minus nowiki are index, log, and patterns only (`test_wikisel_proposer_adds_only_maintainer_pages`)
- pass: history.md has baseline per-skill metrics and says not evaluated (`test_history_has_baseline_metrics_and_marks_skipped_iterations`)
- pass: final_f1 is the best accepted val F1 when the history ends in a reject (`test_history_has_baseline_metrics_and_marks_skipped_iterations`)
- pass: an opaque trace shows both names and skips unloaded distractors (`test_opaque_trace_names_the_six_skills_and_skips_unloaded_distractors`)
- pass: proposer and maintainer usage is written to disk (`test_role_usage_is_written`)
- pass: bodies never change (`test_descriptions_can_change_and_bodies_cannot`)
