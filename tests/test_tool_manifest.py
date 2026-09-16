from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def test_exported_official_manifest_is_deterministic_and_excludes_byod_tools() -> None:
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    command = [sys.executable, str(root / "scripts" / "export_tool_manifest.py")]

    first = subprocess.run(command, cwd=root, env=env, check=True, capture_output=True, text=True)
    second = subprocess.run(command, cwd=root, env=env, check=True, capture_output=True, text=True)

    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    names = [tool["name"] for tool in payload["tools"]]
    assert names == sorted(names)
    assert "list_byod_connectors" not in names
    assert "run_byod_connector" not in names
    assert "search_leads" in names
    assert all(tool["input_schema"]["type"] == "object" for tool in payload["tools"])
    expected_hash = (root / "contracts" / "official-tool-manifest.sha256").read_text().strip()
    assert hashlib.sha256(first.stdout.encode()).hexdigest() == expected_hash
