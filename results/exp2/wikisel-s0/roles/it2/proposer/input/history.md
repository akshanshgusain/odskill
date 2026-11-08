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
- look_at_obj_in_light: Use when the task says to look at, examine, or inspect an object under a desklamp or floorlamp (e.g. "look at the alarmclock under the desklamp"). Not for moving objects.
- pick_and_place: Use for a plain move of ONE object to a destination (e.g. "put a mug on the desk", "move keys to the safe") with no clean/wet, heat/hot, cool/cold word and no count of two. Default for simple moves.
- pick_clean_then_place: Use when the task says to clean (clean, cleaned, wash, wet) an object and then put it somewhere, e.g. "put a clean plate in the cabinet". Uses a sinkbasin. One object.
- pick_cool_then_place: Use when the task says to cool, chill, cold, or refrigerate an object then place it, e.g. "put a cold apple on the table". Uses the fridge. One object.
- pick_heat_then_place: Use when the task says to heat, warm, hot, or cook an object then place it, e.g. "put a hot potato on the countertop". Uses the microwave. One object.
- pick_two_obj_and_place: Use when the task says "two" or gives a count of objects to put somewhere, e.g. "put two pillows on the sofa". Choose this over pick_and_place whenever two items are required.
val_f1 0.000
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.000 precision 0.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000
