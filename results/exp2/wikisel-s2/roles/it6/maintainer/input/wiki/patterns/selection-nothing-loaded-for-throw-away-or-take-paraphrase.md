# Nothing loaded when the move is phrased as throw away, take, or put in a container

These tasks were all plain single-object moves. Ground truth is pick_and_place. The agent loaded nothing.
- 'Throw away the spray bottle on the counter' (t7)
- 'Take a set of keys to the desk' (t4)
- 'Put a bottle in a waste basket' (t3)
- 'Put a phone on the black dresser' (t1)
- 'Put a cloth in the drawer' (t6)

The verb is not always 'put'. Throw away, take to and place all mean a move. 'A set of' is not a count of two. If there is no heat, cool, clean, lamp or two cue, load pick_and_place. Never load nothing.