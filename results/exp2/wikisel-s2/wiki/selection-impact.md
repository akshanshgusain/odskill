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
- look_at_obj_in_light: Use when the task is to look at, examine, or inspect an object under a desklamp or floorlamp (e.g. 'look at the alarmclock under the desklamp', 'hold a pencil and turn on the lamp'). Involves turning on the lamp while holding the object.
- pick_and_place: Use for a plain single-object move: take one object and put/move it in or on a destination (e.g. 'put the blue vase in the safe', 'move keys from shelf to desktop'). No heating, cooling, cleaning, lamp, or count of two.
- pick_clean_then_place: Use when the task says to clean/wash an object (e.g. 'put a clean plate in the cabinet'): take it, clean at the sinkbasin, then place it at the destination.
- pick_cool_then_place: Use when the task says to cool, chill, or make an object cold (e.g. 'put a cold apple on the table'): take it, cool in the fridge, then place it.
- pick_heat_then_place: Use when the task says to heat, warm, or cook an object (e.g. 'put a hot potato on the countertop', 'cook a plate of food then put it in the fridge'): heat in the microwave, then place it.
- pick_two_obj_and_place: Use when the task states a count of two objects (e.g. 'put two spray bottles in the bin', 'two spatulas in the drawer'): find and place both, one at a time, at the destination.
val_f1 0.121
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.400 precision 1.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 2 accept
- look_at_obj_in_light: Use when the task is to look at, examine, or inspect an object with/under a desklamp or floorlamp (e.g. 'look at the alarmclock under the desklamp', 'examine the statue with the lamp'). Involves turning on the lamp while holding the object.
- pick_and_place: ALWAYS load for a plain single-object move: take one object and put/move it in or on a destination (e.g. 'put the phone on the dresser', 'put a cloth in the drawer', 'move keys from desk to safe'). Use when there is no heat/cool/clean word, no lamp, and no count of two. Don't load nothing.
- pick_clean_then_place: Use when the task says clean/wash an object (e.g. 'put a clean plate in the cabinet', 'put a clean pan in the microwave'): take it, clean at the sinkbasin, then place it. Trigger is the word 'clean', even if the destination is a microwave or fridge.
- pick_cool_then_place: Use when the task says to cool, chill, or make an object cold (e.g. 'put a cold apple on the table'): take it, cool in the fridge, then place it.
- pick_heat_then_place: Use when the task says heat, warm, hot, or cook an object (e.g. 'put a hot potato on the countertop', 'cook a plate of food then put it in the fridge'): heat in the microwave, then place it. Not for 'clean X in the microwave'.
- pick_two_obj_and_place: Use whenever the task states a count of two (e.g. 'put two smartphones on the sofa', 'two sets of keys in the safe', 'two newspapers on the stand'). The word 'two' can be mid-sentence and any destination; find and place both, one at a time.
val_f1 0.229
- look_at_obj_in_light — recall 0.100 precision 1.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.500 precision 1.000
- pick_heat_then_place — recall 0.100 precision 1.000
- pick_two_obj_and_place — recall 0.100 precision 1.000

## iteration 3 reject
- look_at_obj_in_light: Use when the task is to look at, examine, or inspect an object with/under a desklamp or floorlamp (e.g. 'look at the alarmclock under the desklamp', 'examine the statue with the lamp'). The lamp is only a tool to turn on while holding the object; this is not pick_and_place.
- pick_and_place: ALWAYS load for a plain single-object move: take one object and put/move/take/throw it into a destination (e.g. 'put the phone on the dresser', 'move keys from desk to safe', 'throw away / take the X to the bin'). Use when there is no heat/cool/clean word (hot, cold, clean, cleaned, cook), no lamp, and no count of two. Don't load nothing.
- pick_clean_then_place: Use when the task says clean, cleaned, or wash an object (e.g. 'put a clean plate in the cabinet', 'put a cleaned pan in the microwave'): take it, clean at the sinkbasin, then place it. Trigger is the word 'clean'/'cleaned', even if the destination is a microwave or fridge.
- pick_cool_then_place: Use when the task says to cool, chill, or make an object cold (e.g. 'put a cold apple on the table'): take it, cool in the fridge, then place it.
- pick_heat_then_place: Use when the task says heat, warm, hot, or cook an object (e.g. 'put a hot potato on the countertop', 'cook a plate of food then put it in the fridge'): heat in the microwave, then place it. Not for 'clean X' with a microwave destination.
- pick_two_obj_and_place: Use whenever the task states a count of two (e.g. 'put two smartphones on the sofa', 'two sets of keys in the safe', 'find two newspapers and put them on the stand'). The word 'two' can be mid-sentence and any destination; find and place both, one at a time.
val_f1 0.176
- look_at_obj_in_light — recall 0.000 precision 0.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.600 precision 1.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 4 reject
- look_at_obj_in_light: Use when the task is to look at, examine, or inspect an object with/under a desklamp or floorlamp (e.g. 'look at the alarmclock under the desklamp', 'examine the statue with the lamp'). Involves turning on the lamp while holding the object.
- pick_and_place: Use for a plain single-object move with no heat/cool/clean word, no lamp, no count of two: take one object and put/move/place/throw/take it to a destination (e.g. 'put the phone on the dresser', 'move keys from desk to safe'). Load this rather than nothing.
- pick_clean_then_place: Use when the task says clean, cleaned, wash, or washed an object (e.g. 'put a clean plate in the cabinet', 'wash the mug and put it on the shelf'): take it, clean at the sinkbasin, then place it. Trigger is the clean/wash word, even if the destination is a microwave or fridge.
- pick_cool_then_place: Use when the task says to cool, chill, or make an object cold (e.g. 'put a cold apple on the table'): take it, cool in the fridge, then place it.
- pick_heat_then_place: Use when the task says heat, warm, hot, or cook an object (e.g. 'put a hot potato on the countertop', 'cook an egg then put it in the fridge'): heat in the microwave, then place it. Not for 'clean X in the microwave'.
- pick_two_obj_and_place: Use whenever the task states a count of two or 'two X' anywhere in the sentence (e.g. 'put two smartphones on the sofa', 'two sets of keys in the safe'). Any destination; find and place both, one at a time.
val_f1 0.094
- look_at_obj_in_light — recall 0.100 precision 1.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.100 precision 1.000
- pick_heat_then_place — recall 0.100 precision 1.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 5 reject
- look_at_obj_in_light: Use when the task is to look at, examine, or inspect an object with/under a desklamp or floorlamp (e.g. 'look at the alarmclock under the desklamp', 'examine the statue with the lamp'). Involves turning on the lamp while holding the object.
- pick_and_place: ALWAYS load for a plain single-object move: take one object and put/move it in or on a destination (e.g. 'put the phone on the dresser', 'put a cloth in the drawer', 'move keys from desk to safe'). Use when there is no heat/cool/clean word, no lamp, and no count of two. Don't load nothing.
- pick_clean_then_place: Use when the task says clean/wash/rinse/scrub an object, or implies cleaning by putting it in the sink with water (e.g. 'put a clean plate in the cabinet', 'put soap in the sink with water to be placed on the toilet lid'): take it, clean at the sinkbasin, then place it. Applies even if the destination is a microwave or fridge.
- pick_cool_then_place: Use when the task says to cool, chill, or make an object cold (e.g. 'put a cold apple on the table'): take it, cool in the fridge, then place it.
- pick_heat_then_place: Use when the task says heat, warm, hot, or cook an object (e.g. 'put a hot potato on the countertop', 'cook a plate of food then put it in the fridge'): heat in the microwave, then place it. Not for 'clean X in the microwave'.
- pick_two_obj_and_place: Use when the task states a count of two OR uses a plural object noun with no number (e.g. 'put two smartphones on the sofa', 'move the alarm clocks on the desk to the drawer shelf'). The word 'two' can be mid-sentence and any destination; find and place both, one at a time.
val_f1 0.119
- look_at_obj_in_light — recall 0.100 precision 1.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.300 precision 1.000
- pick_heat_then_place — recall 0.000 precision 0.000
- pick_two_obj_and_place — recall 0.000 precision 0.000

## iteration 6 reject
- look_at_obj_in_light: Use only when the goal is to look at, examine, or inspect an object under a desklamp or floorlamp (e.g. 'look at the alarmclock under the desklamp', 'examine the statue with the lamp'). Involves turning on the lamp while holding the object. Not for ordinary placing tasks that merely mention a lamp.
- pick_and_place: ALWAYS load for a plain single-object move with no heat/cool/clean word, no two-count, and no lamp-examine goal: take one object and put/move/take/throw it to a destination (e.g. 'put the phone on the dresser', 'move keys from desk to safe'). Also use when a lamp is only incidental and the goal is just placing. Don't load nothing.
- pick_clean_then_place: Use when the task says clean, cleaned, wash, washed, or rinse an object (e.g. 'put a clean plate in the cabinet', 'rinse the mug and put it away'): take it, clean at the sinkbasin, then place it. Applies even if the destination is a microwave or fridge.
- pick_cool_then_place: Use when the task says to cool, chill, or make an object cold (e.g. 'put a cold apple on the table'): take it, cool in the fridge, then place it.
- pick_heat_then_place: Use when the task says heat, warm, hot, or cook an object (e.g. 'put a hot potato on the countertop', 'cook a plate of food then put it in the fridge'): heat in the microwave, then place it. Not for 'clean X in the microwave'. A microwave named only as the source is not a heat task.
- pick_two_obj_and_place: Use whenever the task has a count of two or a plural pair (e.g. 'put two smartphones on the sofa', 'two sets of keys in the safe', 'both newspapers on the stand'). 'Two' can be mid-sentence and any destination; find and place both, one at a time.
val_f1 0.182
- look_at_obj_in_light — recall 0.100 precision 1.000
- pick_and_place — recall 0.000 precision 0.000
- pick_clean_then_place — recall 0.000 precision 0.000
- pick_cool_then_place — recall 0.400 precision 1.000
- pick_heat_then_place — recall 0.100 precision 1.000
- pick_two_obj_and_place — recall 0.000 precision 0.000
