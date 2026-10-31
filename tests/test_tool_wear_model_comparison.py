from pathlib import Path
import runpy

import numpy as np
import pandas as pd

CODE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "compare_tool_wear_models.py"))


def test_tool_split_has_no_overlap():
    table = pd.DataFrame({"tool": np.repeat(np.arange(12), 5), "Vb": np.arange(60)})
    a, b = CODE["group_split"](table, 0.3, 42)
    assert set(table.iloc[a].tool).isdisjoint(set(table.iloc[b].tool))


def test_model_selection_and_report(tmp_path):
    rng = np.random.default_rng(5)
    table = pd.DataFrame({"tool": np.repeat(np.arange(16), 10), "force": rng.uniform(0, 1, 160)})
    table["Vb"] = 15 * table["force"] + 0.3 * table["tool"]
    table["wear_stage"] = "fixture"
    source = tmp_path / "test.csv"
    table.to_csv(source, index=False)
    report = CODE["run"](source)
    assert report["tools"] == 16
    assert set(report["development_groups"]).isdisjoint(report["test_groups"])
    assert set(report["validation_groups"]).issubset(report["development_groups"])
    CODE["write_report"](report, tmp_path / "output")
    assert (tmp_path / "output" / "model_comparison.md").is_file()
