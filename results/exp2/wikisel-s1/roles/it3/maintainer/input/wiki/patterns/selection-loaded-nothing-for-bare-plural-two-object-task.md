# Loaded nothing when the task has a bare plural

Trace t7: 'Move the alarm clocks on the desk to the drawer shelf.' The ground truth was pick_two_obj_and_place. Nothing was loaded. The task has no word 'two', so the plural noun is the only cue.

Other traces with an explicit 'two' also loaded nothing: t2, t3, t5 and t8.

Rule: if the object noun is plural, or the task says two, load pick_two_obj_and_place. Do not fall back to pick_and_place.

Evidence is aggregate only: all 8 traces loaded nothing, and baseline recall was 0 for every skill.