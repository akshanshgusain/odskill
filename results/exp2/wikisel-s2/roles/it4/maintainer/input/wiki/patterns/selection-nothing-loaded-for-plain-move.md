# Nothing loaded for a plain single-object move

Traces t1 (phone to dresser), t6 (cloth in drawer) and t7 (keys from desk to safe).
Ground truth was pick_and_place. No skill was loaded in any of them.
The task has no heat, cool, clean, lamp or count word. The pick_and_place entry says to use it for exactly this case.
Fix: when no special verb or count is present, load pick_and_place. Don't load nothing.
