# External Tool Wear Benchmark

- source: [Vicomtech dataset-machine-tool-wear](https://github.com/Vicomtech/dataset-machine-tool-wear)
- rows after cleaning: `2054`
- tools/groups: `13`
- features used: `150`
- group split: train `1385`, test `669`

## Results

- flank-wear regression MAE: `33.4742`
- flank-wear regression RMSE: `51.0834`
- flank-wear regression R2: `0.8680`
- wear-stage accuracy: `0.6547`
- wear-stage macro F1: `0.6472`

![External tool wear benchmark](external_tool_wear_vicomtech.png)

## Why This Matters

This is a real GitHub-hosted machine-tool dataset. It gives the project a direct path from online data extraction to cleaning, preprocessing, grouped train/test splitting, model fitting, and quantitative evaluation.
