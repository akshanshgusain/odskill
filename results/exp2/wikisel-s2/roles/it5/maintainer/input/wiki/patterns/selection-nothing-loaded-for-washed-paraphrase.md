# Nothing loaded when task says 'washed'

Trace t7: 'put washed plate on shelves'. Truth: pick_clean_then_place. Nothing was loaded. The description keys on 'clean/wash', but the model skipped it because the task has no 'clean' and reads like a plain put.

Signal: washed, rinsed, or scrubbed means the clean skill, not pick_and_place.

Fix: list the inflections washed, rinsed and cleaned in the description.