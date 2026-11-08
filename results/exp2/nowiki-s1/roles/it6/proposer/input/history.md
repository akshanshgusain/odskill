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

## iteration 2 reject
- look_at_obj_in_light: Load for tasks to look at, examine, or inspect an object under a desklamp or floorlamp (e.g. "look at the alarmclock under the desklamp"). Take the object, then turn on the lamp.
- pick_and_place: Load for a plain single-object move task: "put a mug on the desk", "put some soap in the cabinet". Use only when there is no heat, cool, clean, lamp, or "two" in the task.
- pick_clean_then_place: Load when the task says to clean or wash an object, then place it (e.g. "put a clean plate in the cabinet"). Cleans at the sinkbasin before placing.
- pick_cool_then_place: Load when the task says to cool, chill, or make an object cold, then place it (e.g. "put a cold apple on the table"). Cools in the fridge.
- pick_heat_then_place: Load when the task says to heat, warm, or cook an object so it is hot, then place it (e.g. "put a hot potato on the countertop"). Heats in the microwave.
- pick_two_obj_and_place: Load when the task asks to put TWO of an object kind in or on a destination (e.g. "put two pillows on the sofa"). Find and place both, one at a time.
val_f1 0.000
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.000 precision 0.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 3 accept
- look_at_obj_in_light: ALWAYS load first for tasks phrased "look at / examine X under/with the desklamp or floorlamp". Steps: find X, take it, go to lamp, use lamp.
- pick_and_place: ALWAYS load first for tasks phrased "put a/some X in/on Y" (single object, plain move). Not for hot/cold/clean, not "two", not lamp tasks.
- pick_clean_then_place: ALWAYS load first for tasks phrased "put a clean X in/on Y" or clean/wash X then place it. Take X, clean at sinkbasin, then put.
- pick_cool_then_place: ALWAYS load first for tasks phrased "put a cool/cold/chilled X in/on Y". Take X, cool it with the fridge, then put.
- pick_heat_then_place: ALWAYS load first for tasks phrased "put a hot/heated/warm X in/on Y". Take X, heat it with the microwave, then put.
- pick_two_obj_and_place: ALWAYS load first for tasks phrased "put two X in/on Y" (two objects of the same kind). Find and place each one in turn.
val_f1 0.095
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.100 precision 1.000
- pick_cool_then_place — recall 0.100 precision 1.000
- pick_heat_then_place — recall 0.100 precision 1.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 4 accept
- look_at_obj_in_light: ALWAYS load first, before any action, for any task containing "look at", "examine", "inspect" or "see" an object "under"/"with"/"in the light of" a desklamp or floorlamp. Steps: find X, take it, go to lamp, use lamp.
- pick_and_place: ALWAYS load first, before any action, for tasks phrased "put a/some X in/on/into Y" or "move X to Y" (one object, plain move, no heating/cooling/cleaning words). Not for "hot/cold/clean", not "two", not lamp tasks. Search, take X, go to Y, put.
- pick_clean_then_place: ALWAYS load first, before any action, for tasks containing "clean", "washed" or "wash", e.g. "put a clean X in/on Y" or "clean some X and put it in Y". Take X, clean at sinkbasin, then put.
- pick_cool_then_place: ALWAYS load first, before any action, for tasks containing "cool", "cold", "chilled" or "refrigerated", e.g. "put a cool X in/on Y" or "cool some X and put it in Y". Take X, cool it with the fridge, then put.
- pick_heat_then_place: ALWAYS load first, before any action, for tasks containing "hot", "heated", "warm" or "cooked", e.g. "put a hot X in/on Y" or "heat some X and put it in Y". Take X, heat it with the microwave, then put.
- pick_two_obj_and_place: ALWAYS load first, before any action, for tasks containing "two" or a count of 2, e.g. "put two X in/on Y" (two objects of the same kind, like two pillows or two cups). Find and place each one in turn.
val_f1 0.768
- look_at_obj_in_light — recall 0.300 precision 1.000
- pick_and_place — recall 0.400 precision 1.000
- pick_clean_then_place — recall 0.700 precision 1.000
- pick_cool_then_place — recall 0.800 precision 1.000
- pick_heat_then_place — recall 0.800 precision 1.000
- pick_two_obj_and_place — recall 0.800 precision 0.889

## iteration 5 reject
- look_at_obj_in_light: ALWAYS load first, before any action, for any task with "look at", "examine", "inspect" or "see" an object "under"/"with"/"in the light of" a desklamp or floorlamp (e.g. "look at the alarmclock under the desklamp"). Any task mentioning a desklamp or floorlamp belongs here. Steps: find X, take it, go to lamp, use lamp.
- pick_and_place: ALWAYS load first, before any action, for ANY plain move task: "put a/some X in/on/into Y", "place X on Y", "move X to Y", "put a mug on the desk", "put some soap in the cabinet". One object, no hot/cold/clean/wash/cool/heat words, no "two", no lamp. Default skill for simple put tasks. Search, take X, go to Y, put.
- pick_clean_then_place: ALWAYS load first, before any action, for tasks containing "clean", "washed" or "wash", e.g. "put a clean X in/on Y" or "clean some X and put it in Y". Even if the task also says put/place, load this one. Take X, clean at sinkbasin, then put.
- pick_cool_then_place: ALWAYS load first, before any action, for tasks containing "cool", "cold", "chilled" or "refrigerated", e.g. "put a cool X in/on Y", "put a cold X in Y" or "cool some X and put it in Y". Even if the task also says put/place, load this one. Take X, cool it with the fridge, then put.
- pick_heat_then_place: ALWAYS load first, before any action, for tasks containing "hot", "heated", "heat", "warm" or "cooked", e.g. "put a hot X in/on Y" or "heat some X and put it in Y". Even if the task also says put/place, load this one. Take X, heat it with the microwave, then put.
- pick_two_obj_and_place: ALWAYS load first, before any action, for tasks containing "two", "2" or "both", e.g. "put two X in/on Y" (two objects of the same kind, like two pillows, two cups, two soapbars). Takes priority over plain put tasks. Find and place each one in turn.
val_f1 0.347
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.200 precision 1.000
- pick_cool_then_place — recall 0.600 precision 1.000
- pick_heat_then_place — recall 0.300 precision 1.000
- pick_two_obj_and_place — recall 0.200 precision 0.667
