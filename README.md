# Materials ML Projects

This repository contains independent scientific-machine-learning projects for materials images, process signals, machining datasets, and tabular materials properties. Each project has its own data path, methods, outputs, and result page while sharing one tested Python codebase.

Shared code is kept in `src/`, experiment runners are in `scripts/`, configuration files are in `configs/`, and generated outputs are in `reports/`.

![Materials ML research architecture](assets/system_architecture.svg)

## Technical Scope

| Area | Demonstrated |
|---|---|
| Computer vision | U-Net microscopy segmentation |
| Tabular ML | Ridge, Random Forest, XGBoost |
| Explainable AI | SHAP and image attribution |
| Benchmarking | R2, RMSE, MAE, F1, IoU, Dice |
| Scientific Python | NumPy, Pandas, scikit-learn, PyTorch |
| Reproducibility | configs, scripts, CI, fixed seeds |
| Process data | force/moment feature engineering |
| Materials ML | structure/property prediction |

## Projects

![Project evidence map](assets/project_evidence_map.svg)

| Project | Method Focus | Current Output |
|---|---|---|
| [SEM Segmentation](projects/sem-segmentation) | SEM segmentation, architecture comparison, active learning, and image attribution | IoU/Dice/precision/recall with qualitative outputs |
| [Process Signal ML](projects/process-signal-ml) | 20 kHz force/moment feature extraction and ML modelling | `Fx`, `Fy`, `Fz`, `Mz` feature table and model results |
| [Tool-Wear Prediction](projects/tool-wear-prediction) | grouped-validation wear regression and classification | Vicomtech and Uniwear benchmark reports |
| [Concrete Strength ML](projects/concrete-strength-ml) | tabular preprocessing, Ridge/RF/XGBoost regression, and SHAP | concrete compressive-strength benchmark and explainability report |

## Current Results

| Benchmark | Task | Validation | Result |
|---|---|---|---|
| Vicomtech tool wear | flank-wear regression | held-out tool IDs | R2 `0.8680` |
| Vicomtech tool wear | wear-stage classification | held-out tool IDs | macro F1 `0.6472` |
| Katulu Uniwear | wear-stage classification | held-out experiment tags | macro F1 `0.5205` |
| Concrete strength | compressive-strength regression | random train/test split | XGBoost R2 `0.9173` |
| NASA EBC SEM trained path | semantic segmentation | held-out images | U-Net foreground IoU `0.4388` |
| NASA EBC SEM suite | segmentation smoke test | held-out images | foreground IoU `0.1174` |

Full leaderboard: [reports/materials_ai_leaderboard.md](reports/materials_ai_leaderboard.md)

## Repository Map

```text
projects/                  Short project-specific summaries and copied result figures
src/                       Reusable Python package
scripts/                   Data loading, preprocessing, training, evaluation, and reporting
configs/                   Dataset and benchmark configuration files
reports/                   Generated metrics, figures, leaderboards, and summaries
docs/                      Dataset notes, methodology, project summary, and research notes
tests/                     Smoke tests for data, models, reports, links, and visuals
LICENSE                    MIT license for reuse and extension
```

## Quick Start

```powershell
git clone https://github.com/Ghanshyambabariya/materials-ml-research-projects.git
cd materials-ml-research-projects
python -m pip install -e . pytest timm
python scripts/run_all_benchmarks.py
python -m pytest -q
```

## Useful Notes

- [Project summary](docs/project_summary.md)
- [Research notes](docs/research_notes.md)
- [Research upgrade audit](docs/research_upgrade_audit.md)
- [System design](docs/advanced_system_design.md)
- [Dataset cards](docs/datasets.md)
- [Methodology](docs/methodology.md)

## Current Status

This is an active research workspace. Some parts use real online datasets, and some parts use clearly marked development scaffolds. The microscopy results are baseline measurements, not final performance claims.
