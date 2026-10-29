"""Pytest runner wrapping behave BDD features for spatiograph."""

import subprocess
import sys
from pathlib import Path


def test_behave_bdd_features() -> None:
    pkg_dir = Path(__file__).parent.parent
    feature_file = pkg_dir / "features" / "spatiograph_decomposition.feature"
    venv_bin = Path(sys.executable).parent
    behave_cmd = str(venv_bin / "behave") if (venv_bin / "behave").exists() else "behave"
    cmd = [
        behave_cmd,
        str(feature_file),
    ]
    env = dict(subprocess.os.environ)
    env["PYTHONPATH"] = f"{pkg_dir / 'src'}:{env.get('PYTHONPATH', '')}"

    res = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=pkg_dir.parent)
    assert res.returncode == 0, f"Behave BDD failed:\n{res.stdout}\n{res.stderr}"
