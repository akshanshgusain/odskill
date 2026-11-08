# 'examine the statue with the lamp' loaded look_at_obj_in_light, but truth was pick_and_place
The look_at description lists this exact task as its example, so the selector loaded it. The label here was pick_and_place, so the example conflicts with the ground truth. Treat lamp-task labels as noisy and do not trust the example wording. Related: selection-lamp-examine-task-labeled-pick-and-place.
