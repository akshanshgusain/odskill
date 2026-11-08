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

## iteration 1 accept
- look_at_obj_in_light: Use when the task says look at / examine / inspect an object under a desklamp or floorlamp (e.g. "look at the alarmclock under the desklamp"). Take the object, turn on the lamp.
- pick_and_place: Use when the task is simply to put one object in/on a destination (e.g. "put a mug on the desk") with NO heating, cooling, cleaning, lamp, or second object.
- pick_clean_then_place: Use when the task says to clean/wash an object and then put it somewhere (e.g. "put a clean plate in the cabinet"). Cleans at a sinkbasin.
- pick_cool_then_place: Use when the task says to cool/chill/cold an object and then put it somewhere (e.g. "put a cool apple on the table"). Cools in the fridge.
- pick_heat_then_place: Use when the task says to heat/warm/hot an object and then put it somewhere (e.g. "put a hot potato on the countertop"). Heats in the microwave.
- pick_two_obj_and_place: Use when the task asks to put TWO of an object kind in/on a destination (e.g. "put two pillows on the sofa"). Find and place both, one at a time.
val_f1 0.065
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.100 precision 1.000
- pick_heat_then_place — recall 0.100 precision 1.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 2 accept
- look_at_obj_in_light: ALWAYS load for tasks like "look at X under the desklamp", "examine X with the floorlamp", or "inspect X in light". Take the object, go to the lamp, use it to turn it on. Any task mentioning a lamp.
- pick_and_place: Load for tasks "put a/some X in/on Y" or "move X to Y" with a single object and no heated/cooled/cleaned/hot/cold/clean/lamp/two/"two" words. Plain find, take, put.
- pick_clean_then_place: Load for tasks with "clean", "wash", or "rinse" an object then put it somewhere (e.g. "put a clean plate in the cabinet", "clean some mug and put it on the desk"). Uses sinkbasin.
- pick_cool_then_place: Load for tasks with "cool", "cold", "chill", or "refrigerate" an object then put it somewhere (e.g. "put a cool apple on the table", "cool some mug and put it in the cabinet"). Uses fridge.
- pick_heat_then_place: Load for tasks with "hot", "heat", "warm", or "cook" an object then put it somewhere (e.g. "put a hot potato on the countertop", "heat some egg and put it on the table"). Uses microwave.
- pick_two_obj_and_place: Load for tasks with "two" or a count of 2 objects, e.g. "put two pillows on the sofa", "find two soapbars and put them in the cabinet". Find and place both, one at a time.
val_f1 0.179
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.400 precision 1.000
- pick_heat_then_place — recall 0.200 precision 1.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 3 accept
- look_at_obj_in_light: ALWAYS load this skill when the task mentions look at, examine, or inspect an object under/with/in a desklamp or floorlamp (e.g. "look at the alarmclock under the desklamp"). Take the object, go to the lamp, and turn it on with `use`. Any task with a lamp.
- pick_and_place: Load for any simple "put a/some X in/on Y" or "move X to Y" task with one object (e.g. "put a mug on the desk", "put some soap in the cabinet"). Use it when the task has no hot/heat/cool/cold/clean words, no lamp, and no "two". Find, take, put.
- pick_clean_then_place: Load when the task says "clean", "wash", or "rinse" an object and then put it somewhere (e.g. "put a clean plate in the cabinet", "clean some mug and put it on the desk"). Take the object to the sinkbasin, clean it, then place it.
- pick_cool_then_place: Load when the task says "cool", "cold", "chill", or "refrigerate" an object and then put it somewhere (e.g. "put a cool apple on the table", "cool some mug and put it in the cabinet"). Take the object to the fridge, cool it, then place it.
- pick_heat_then_place: Load when the task says "hot", "heat", "warm", or "cook" an object and then put it somewhere (e.g. "put a hot potato on the countertop", "heat some egg and put it on the table"). Take the object to the microwave, heat it, then place it.
- pick_two_obj_and_place: ALWAYS load when the task says "two" or asks for 2 of an object (e.g. "put two pillows on the sofa", "find two soapbars and put them in the cabinet"). Find and place the first object, then find and place a second one, carrying one at a time.
val_f1 0.286
- look_at_obj_in_light — recall 0.600 precision 1.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.400 precision 1.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000
