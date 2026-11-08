# Nothing loaded when clean is implied but the word is missing

Trace t2: 'Put soap in the sink with water to be placed on the toilet lid.' The ground truth was pick_clean_then_place. Nothing was loaded.

The task never says clean or wash. It describes the cleaning act: an object goes in the sink with water. The clean description keys on the word 'clean', so the match failed.

Fix: the description should list implied cleaning cues, such as sink, water, rinse and scrub, alongside clean/wash. The agent should load a skill even when no trigger word matches. Offered descriptions are unchanged in this evidence.
