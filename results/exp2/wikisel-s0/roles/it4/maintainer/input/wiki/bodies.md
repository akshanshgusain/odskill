# look_at_obj_in_light
## When to Apply
- The task says to look at, examine, or inspect an object under a lamp (desklamp or floorlamp).
- Example: "look at the alarmclock under the desklamp".

## When NOT to Apply
- The task asks you to move an object to a destination.
- The task asks you to heat, cool, or clean something.
- The task asks for two objects.

## Instructions
1. Read the task and note the object and the lamp type.
2. Search likely places one at a time: desks, shelves, sidetables, dressers, drawers, cabinets. Open closed receptacles to check inside them.
3. Copy admissible actions exactly as listed, including the object and receptacle numbers.
4. When you see the object, take it: `take X from Y`.
5. Find the lamp. Go to it with `go to desklamp 1` or the matching name.
6. Use `use desklamp 1` to turn it on. Use the lamp named in the task.
7. Once the lamp is on and you are holding the object, use `look at` only if it is admissible, or `examine` as listed.
8. Do not repeat an action that just failed or returned "Nothing happens". Pick a different admissible action or a different location.
9. Keep track of the places you have already searched so you do not revisit them.
10. If the lamp is in another room or location, go there while still holding the object.

# pick_and_place
## When to Apply
- The task says to put an object in or on a destination, such as "put a mug on the desk" or "put some soap in the cabinet".
- No heating, cooling, or cleaning is mentioned.

## When NOT to Apply
- The task says to heat, cool, or clean the object first.
- The task needs two objects.
- The task is to look at an object under a lamp.

## Instructions
1. Identify the object and the destination from the task.
2. Search likely receptacles one at a time. Go to each one and, if it is closed, use `open` on it to see inside.
3. Copy admissible actions exactly as listed, including the numbers.
4. When you see the object, use `take X from Y`.
5. Go to the destination. Open it if it is closed.
6. Use `put X in/on Y`, using the exact wording from the admissible actions.
7. Do not repeat an action that just failed or returned "Nothing happens". Try a different action or a different place.
8. Keep a list of the places you have checked so you do not revisit them.
9. Hold only one object at a time. Put it down at the destination before you take anything else.

# pick_clean_then_place
## When to Apply
- The task says to clean an object and then put it somewhere, such as "put a clean plate in the cabinet".

## When NOT to Apply
- No cleaning is needed.
- The task asks for heating or cooling.
- The task needs two objects, or to look at an object in light.

## Instructions
1. Identify the object and the destination.
2. Find the object. Search likely places and open closed receptacles.
3. Copy admissible actions exactly as listed, including the numbers.
4. Take it with `take X from Y`.
5. Go to a sinkbasin with `go to sinkbasin 1`.
6. Use `clean X with sinkbasin 1`, with the exact wording from the admissible list. Do not use the faucet unless it is the only option.
7. Go to the destination and open it if it is closed.
8. Use `put X in/on Y`.
9. Do not repeat an action that just failed or returned "Nothing happens". Check the admissible actions and try a different one.
10. You must be holding the object while cleaning it. Do not put it down early.

# pick_cool_then_place
## When to Apply
- The task says to cool, chill, or refrigerate an object and then place it, such as "put a cold apple on the table".

## When NOT to Apply
- No cooling is needed.
- The task asks for heating or cleaning.
- The task needs two objects, or to look at an object in light.

## Instructions
1. Identify the object and the destination.
2. Find the object. Search likely places and open closed receptacles.
3. Copy admissible actions exactly as listed, including the numbers.
4. Take it with `take X from Y`.
5. Go to the fridge with `go to fridge 1`.
6. Open the fridge if it is closed. Use `cool X with fridge 1` as listed in the admissible actions. Do not just put the object inside unless that is the only option.
7. Take the object again if it is no longer in your hand.
8. Go to the destination and open it if it is closed.
9. Use `put X in/on Y`.
10. Do not repeat an action that just failed or returned "Nothing happens". Try a different admissible action.

# pick_heat_then_place
## When to Apply
- The task says to heat, warm, or cook an object and then place it, such as "put a hot potato on the countertop".

## When NOT to Apply
- No heating is needed.
- The task asks for cooling or cleaning.
- The task needs two objects, or to look at an object in light.

## Instructions
1. Identify the object and the destination.
2. Find the object. Search likely places and open closed receptacles.
3. Copy admissible actions exactly as listed, including the numbers.
4. Take it with `take X from Y`.
5. Go to the microwave with `go to microwave 1`.
6. Open the microwave if it is closed. Use `heat X with microwave 1` as listed in the admissible actions. If the microwave must be empty, check that first.
7. Take the object again if it is no longer in your hand.
8. Go to the destination and open it if it is closed.
9. Use `put X in/on Y`.
10. Do not repeat an action that just failed or returned "Nothing happens". Try a different admissible action.

# pick_two_obj_and_place
## When to Apply
- The task asks you to put two of an object kind in or on a destination, such as "put two pillows on the sofa".

## When NOT to Apply
- The task needs only one object.
- The task needs heating, cooling, or cleaning.
- The task is to look at an object in light.

## Instructions
1. Identify the object kind, the count of two, and the destination.
2. Search likely places one at a time. Open closed receptacles to see inside.
3. Copy admissible actions exactly as listed, including the numbers.
4. When you find the first object, take it with `take X from Y`. You can carry only one object at a time.
5. Go to the destination, open it if it is closed, and use `put X in/on Y`.
6. Go back to searching. Look at the places you have not checked yet, and also at the places near the first object.
7. Take the second object. It must be a different object of the same kind, not the one you already placed.
8. Go to the destination and put it there.
9. Do not repeat an action that just failed or returned "Nothing happens". Try a different admissible action or place.
10. Keep a list of the places you have checked and of the objects you have placed.
