# Candidate descriptions

## iteration 0 baseline
- look_at_obj_in_light: Procedure for examining an object under a light.
- pick_and_place: Procedure for picking up one object and putting it somewhere.
- pick_clean_then_place: Procedure for cleaning an object and then putting it somewhere.
- pick_cool_then_place: Procedure for cooling an object and then putting it somewhere.
- pick_heat_then_place: Procedure for heating an object and then putting it somewhere.
- pick_two_obj_and_place: Procedure for picking up two objects and putting them somewhere.
val_f1 0.000
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.000 precision 0.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 1 reject
- look_at_obj_in_light: Use when the task says to look at, examine, or inspect an object under a desklamp or floorlamp (e.g. "look at the alarmclock under the desklamp"). Take the object, then turn on the lamp.
- pick_and_place: Use for a plain single-object move: "put a mug on the desk", "put some soap in the cabinet". Use only when the task has no heat/cool/clean step, no lamp, and no "two".
- pick_clean_then_place: Use when the task says to put a CLEAN object somewhere (e.g. "put a clean plate in the cabinet"). Wash it at the sinkbasin, then place it.
- pick_cool_then_place: Use when the task says to put a COLD, cooled, or chilled object somewhere (e.g. "put a cold apple on the table"). Cool it in the fridge, then place it.
- pick_heat_then_place: Use when the task says to put a HOT, heated, or warm object somewhere (e.g. "put a hot potato on the countertop"). Heat it in the microwave, then place it.
- pick_two_obj_and_place: Use when the task asks for TWO of an object (e.g. "put two pillows on the sofa", "find two cds and put them in the drawer"). Find and place both, one at a time.
val_f1 0.000
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.000 precision 0.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000
