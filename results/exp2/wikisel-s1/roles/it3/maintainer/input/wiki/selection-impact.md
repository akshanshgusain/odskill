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
- look_at_obj_in_light: Use for tasks to look at, examine, or inspect an object under a desklamp or floorlamp (e.g. 'look at the alarmclock under the desklamp'). Turn on the lamp while holding the object.
- pick_and_place: Use for a single object moved/put/placed somewhere (e.g. 'put a mug on the desk', 'move the watch from drawer to table') with NO heat, cool, clean, lamp, or count of two.
- pick_clean_then_place: Use when the object must be cleaned, washed, or rinsed (e.g. 'put a clean plate in the cabinet', 'place a rinsed knife on the counter') before placing it. Cleans at the sinkbasin.
- pick_cool_then_place: Use when the object must be cooled, chilled, cold, or refrigerated (e.g. 'put a cold apple on the table') before placing it. Cools using the fridge.
- pick_heat_then_place: Use when the object must be heated, warmed, hot, or cooked (e.g. 'put a hot potato on the countertop', 'heat a tomato and place it') before placing it. Heats with the microwave.
- pick_two_obj_and_place: Use when the task involves two objects of one kind or a plural noun (e.g. 'put two pillows on the sofa', 'alarm clocks on a shelf'), placed at one destination. Prefer over pick_and_place when plural or 'two'.
val_f1 0.000
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.000 precision 0.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000
