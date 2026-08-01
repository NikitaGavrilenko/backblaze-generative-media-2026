"""Small JSON repository used by the single-process MVP."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import GenerationRun


class RunRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.runs_dir = self.data_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def save(self, run: GenerationRun) -> None:
        run_dir = self.runs_dir / run.id
        run_dir.mkdir(parents=True, exist_ok=True)
        target = run_dir / "run.json"
        temporary = run_dir / "run.json.tmp"
        temporary.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(target)

    def get(self, run_id: str) -> GenerationRun | None:
        target = self.runs_dir / run_id / "run.json"
        if not target.is_file():
            return None
        return GenerationRun.model_validate_json(target.read_text(encoding="utf-8"))

    def list(self) -> list[GenerationRun]:
        runs: list[GenerationRun] = []
        for target in self.runs_dir.glob("*/run.json"):
            try:
                runs.append(
                    GenerationRun.model_validate_json(target.read_text(encoding="utf-8"))
                )
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return sorted(runs, key=lambda item: item.created_at, reverse=True)

    def find_by_idempotency_key(self, key: str) -> GenerationRun | None:
        return next((run for run in self.list() if run.idempotency_key == key), None)

