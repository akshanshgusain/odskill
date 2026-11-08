# Nothing loaded when the task states two

Traces t3 (two smartphones), t5 (two sets of keys) and t8 (two newspapers).
Ground truth was pick_two_obj_and_place. No skill was loaded.
The count word 'two' is the trigger. It can sit mid-sentence, and the destination can be a safe, a drawer or a stand.
Fix: when the task says two, load pick_two_obj_and_place instead of pick_and_place.
