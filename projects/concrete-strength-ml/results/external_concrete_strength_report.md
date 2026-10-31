# External Concrete Strength Benchmark

- source: [Concrete Compressive Strength](https://github.com/stedy/Machine-Learning-with-R-datasets)
- cleaned rows: `1005`
- features used: `8`
- train/test split: `753` / `252`
- best held-out model: `xgboost`

## Model Benchmark

| Model | Hold-out MAE | Hold-out RMSE | Hold-out R2 | CV R2 mean +/- std |
|---|---:|---:|---:|---:|
| ridge | 8.9406 | 11.2337 | 0.5644 | 0.5979 +/- 0.0664 |
| random forest | 3.6956 | 5.4103 | 0.8990 | 0.8816 +/- 0.0139 |
| xgboost | 3.5377 | 4.8951 | 0.9173 | 0.8994 +/- 0.0149 |

## SHAP Explainability

- global feature ranking: `shap_concrete/concrete_shap_global.png`
- beeswarm plot: `shap_concrete/concrete_shap_beeswarm.png`
- individual prediction explanation: `shap_concrete/concrete_shap_individual.png`

![External concrete strength benchmark](external_concrete_strength.png)

## Why This Matters

This benchmark compares linear and tree-based regressors for materials-property prediction and uses SHAP to inspect dominant composition/process variables.
