# Tool-wear model efficiency

Public Vicomtech data. Complete tool groups are held out; model selection uses development tools only.

Samples: 2054. Features: 150. Tools: 13.

| Model | Test RMSE | Test MAE | Test R² | Fit seconds |
|---|---:|---:|---:|---:|
| Random Forest, 300 trees | 51.557 | 33.572 | 0.866 | 8.11 |
| extra_trees_160 | 50.746 | 32.121 | 0.870 | 1.13 |

Training speedup on the same runner: 7.18x.
RMSE within 5% of baseline: True. Faster fitting: True.

Measured performance is for prediction, not a proven reduction in machining time or scrap.
Dataset: https://github.com/Vicomtech/dataset-machine-tool-wear
