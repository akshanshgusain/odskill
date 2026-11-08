# Lamp mentioned: look_at_obj_in_light vs pick_and_place

Traces t4 and t5, nothing loaded. t4 'examine the statue with the lamp' had ground truth pick_and_place, although the wording suggests look_at_obj_in_light. t5 'Hold a pencil and turn on the lamp' had ground truth look_at_obj_in_light. The lamp keyword alone does not decide the skill. Check whether the task is about examining an object under the light, and don't rely on the word 'examine'. Labels here look counterintuitive, so treat them with caution.
