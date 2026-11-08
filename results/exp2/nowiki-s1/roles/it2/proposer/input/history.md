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
- look_at_obj_in_light: Use when the task says look at / examine / inspect an object under or with a lamp (desklamp or floorlamp), e.g. "look at the alarmclock under the desklamp". Take the object, turn on the lamp.
- pick_and_place: Use for a plain move task: "put a mug on the desk", "put some soap in the cabinet". One object, no heating, cooling, or cleaning, no lamp, not two items.
- pick_clean_then_place: Use when the task says to clean (or "clean X" / "put a clean plate in...") an object and then place it. Washes at a sinkbasin before placing.
- pick_cool_then_place: Use when the task says cool, chill, cold, or refrigerate an object, then place it, e.g. "put a cold apple on the table". Uses the fridge to cool.
- pick_heat_then_place: Use when the task says heat, warm, hot, or cook an object, then place it, e.g. "put a hot potato on the countertop". Uses the microwave to heat.
- pick_two_obj_and_place: Use when the task asks for TWO of an object kind put in/on a destination, e.g. "put two pillows on the sofa". Find and place both, one at a time.
val_f1 0.000
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.000 precision 0.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000
