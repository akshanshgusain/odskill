# Nothing loaded when the count of two is implied by a plural

Trace t4: 'Move the alarm clocks on the desk to the drawer shelf.' The ground truth was pick_two_obj_and_place. Nothing was loaded.

The task has no literal 'two'. The plural noun implies two objects. The two-object description triggers on the stated count, so it was not matched.

Fix: say that a plural object noun with no number also suggests pick_two_obj_and_place. Say that a skill must be loaded when the plain pick_and_place wording does not fit a plural task.
