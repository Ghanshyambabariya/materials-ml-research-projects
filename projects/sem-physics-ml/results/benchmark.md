# Physics-informed SEM transport: synthetic benchmark

The mask generator is synthetic; no pretrained SEM checkpoint was used in this benchmark.
NASA EBC phase names are background, oxide, crack. Conductivities are illustrative ratios (1.0, 0.4, 0.05).

Steady-state equation: ∇·(k∇T) = 0. Left/right temperature fixed; upper/lower edges insulated.

| Test metric | CNN (data only) | CNN + finite-volume physics loss |
|---|---:|---:|
| Mean absolute temperature error | 0.008196 | 0.007878 |
| PDE residual RMSE | 0.012433 | 0.008725 |
| Relative effective-conductivity error | 7.270% | 6.171% |
| Unphysical temperature fraction | 0.000% | 0.000% |

Uniform-temperature-profile baseline MAE: 0.032434.

Data uses a numerical finite-volume solver for labels, and its residual also provides physics guidance.
**Important:** These are modeled, dimensionless transport results. They do not establish experimental thermal conductivity, oxidation lifetime or actual SEM performance.
