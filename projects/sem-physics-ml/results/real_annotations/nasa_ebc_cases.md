# NASA EBC mask transfer study

Real annotation geometries; hypothetical phase conductivities. No trained U-Net checkpoint was used.

| Dataset | Original crack pixels | All cracks lost at 24px? | CNN temperature MAE | Relative proxy error |
|---|---:|---|---:|---:|
| EBC1 | 3790 | False | 0.03581 | 50.2% |
| EBC2 | 2232 | True | 0.02140 | 29.8% |
| EBC3 | 2676 | False | 0.02134 | 18.9% |

Flow along image y is a provisional orientation, not independently checked from microscopy metadata.
The proxy is not a measured material property. The network was trained only on procedural synthetic masks.

Source: https://github.com/nasa/pretrained-microscopy-models
