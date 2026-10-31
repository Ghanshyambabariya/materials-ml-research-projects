# Tool-wear model efficiency

Public Vicomtech data. Complete tool groups are held out; model selection uses development tools only.

Samples: 2054. Features: 150. Tools: 13.

| Model | Test RMSE | Test MAE | Test R² | Fit seconds |
|---|---:|---:|---:|---:|
| Random Forest, 300 trees | 37.237 | 29.596 | 0.758 | 6.62 |
| extra_trees_160 | 38.516 | 30.570 | 0.742 | 0.95 |

Training speedup on the same runner: 6.94x.
RMSE within 5% of baseline: True. Faster fitting: True.

Measured performance is for prediction, not a proven reduction in machining time or scrap.
Dataset: https://github.com/Vicomtech/dataset-machine-tool-wear
