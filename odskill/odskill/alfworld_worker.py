"""One persistent ALFWorld game. Run with ALFWORLD_PYTHON, not the paper venv.

stdin: one JSON object per line, {"op": "reset", "game": "..."} or {"op": "step", "action": "..."}.
stdout: one JSON object per line. Library noise stays on stderr.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_stdout = sys.stdout
sys.stdout = sys.stderr  # library prints must not break the JSON line protocol
# This file lives next to odskill/alfworld.py. Drop that directory so
# `import alfworld` resolves to the simulator, not our agent module.
_here = str(Path(__file__).resolve().parent)
sys.path[:] = [entry for entry in sys.path if str(Path(entry).resolve()) != _here]
from wikiskill.alfworld.step import _load_env, _payload  # noqa: E402


def _text(value) -> str:
    if isinstance(value, (list, tuple)):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def _emit(payload: dict) -> None:
    _stdout.write(json.dumps(payload) + "\n")
    _stdout.flush()


def main() -> None:
    env = None
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        op = req.get("op")
        if op == "close":
            break
        if op == "reset":
            if env is not None:
                env.close()
            env = _load_env(Path(req["game"]), max_steps=int(req.get("max_steps", 50)))
            obs, info = env.reset()
            _emit(_payload(_text(obs), info, step=0))
            continue
        if op == "step":
            if env is None:
                _emit({"error": "reset first"})
                continue
            obs, reward, done, info = env.step(req["action"])
            _emit(_payload(_text(obs), info, reward=int(reward), done=done,
                           step=int(req.get("step", 0))))
            continue
        _emit({"error": "unknown op"})
    if env is not None:
        env.close()


if __name__ == "__main__":
    main()
