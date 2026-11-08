# Nothing loaded even with 'ALWAYS load' wording

Traces t1, t4 and t6 are plain moves ('put a phone on the black dresser', 'place a cell phone on a dresser', 'put a cloth in the drawer'). Truth: pick_and_place. Nothing was loaded, even though the description says 'ALWAYS load' and 'Don't load nothing'.

Traces t3, t5 and t8 are 'two' tasks. Truth: pick_two_obj_and_place. Nothing was loaded there either.

The imperative wording did not change behavior. Across t1 to t8, 7 of 8 loaded nothing. The failure is in the load decision, not in which skill was picked. Val recall stayed near 0 for pick_and_place.

Fix: make the agent's first step an explicit skill choice. Don't rely on emphasis in the descriptions.