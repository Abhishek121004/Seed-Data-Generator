from __future__ import annotations

import hashlib
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from seed_data_generator.generator import GenerationConfig, generate_and_write
from seed_data_generator.validator import validate_output


def _hash_dir(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(path.glob("*.json")):
        digest.update(file_path.name.encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def test_generate_and_validate(tmp_path: Path) -> None:
    config = GenerationConfig(clients=3, projects=4, tickets=8, seed=123, output_dir=tmp_path / "output")
    _, issues = generate_and_write(config)
    assert issues == []
    assert validate_output(config.output_dir) == []


def test_generation_is_deterministic(tmp_path: Path) -> None:
    out1 = tmp_path / "one"
    out2 = tmp_path / "two"
    generate_and_write(GenerationConfig(clients=3, projects=4, tickets=8, seed=123, output_dir=out1))
    generate_and_write(GenerationConfig(clients=3, projects=4, tickets=8, seed=123, output_dir=out2))
    assert _hash_dir(out1) == _hash_dir(out2)

