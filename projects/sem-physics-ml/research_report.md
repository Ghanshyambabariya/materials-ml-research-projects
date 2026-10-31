# SEM Physics-Informed ML — research report

## Existing work

The user's SEM project reports NASA EBC UNetSmall segmentation performance with three classes: background, oxide and crack. The reported foreground IoU is 0.4388, with the crack class harder to segment. The GitHub repository contains results and the expected checkpoint path but not the actual trained weight file or TIFF inputs.

NASA's definitions mean this is **not** a pore-segmentation dataset. Oxide and crack must not be interpreted as interchangeable porosity classes.

## Prediction question

Can a convolutional surrogate use segmented EBC phases to approximate the steady-state 2-D conduction equation ∇·(k∇T)=0, while reducing violations of that equation compared with a data-only CNN?

The physics solver uses a harmonic-mean finite-volume discretization. The architecture enforces left/right temperatures. A differentiable residual of the same discretized equation supplements the numerical-solution loss.

The class conductivities are normalized assumptions (1.0, 0.4, 0.05); the experiment neither estimates measured conductivity nor predicts coating lifetime.

## Controlled experiment

- Artificial phase-mask generator with train/validation/test seeds 17, 18, 19.
- Split sizes: 64 training, 16 validation, 20 test.
- 24x24 masks, 160 epochs, network width 24, seed 17.
- Compare identical CNNs with PDE-loss weights 0 and 0.5; select their checkpoints on validation MSE only.
- On independently generated masks, compare temperature MAE, PDE residual, proxy effective conductivity relative error and physical temperature-bound violations.
- The finite-volume reference is checked against homogeneous analytical solutions and layered conservation tests.

## Interpretation

The physics-regularized model reduces both held-out temperature MAE and the discretized PDE residual in the local synthetic benchmark. This is evidence for a **numerical surrogate**, not evidence of improved SEM classification or validated coating thermal properties.

Limitations: The data generator is simpler than real EBC microscopy; 24x24 sampling can remove thin cracks; the U-Net weights are not in the linked repository; 2-D section morphology cannot directly establish 3-D conduction; interface materials and coefficients have not been calibrated.

Next experimental step: recover the SEM U-Net checkpoint and compare results from predicted masks versus NASA's ground-truth masks on held-out SEM images. Revisit image resolution and quantify uncertainty due to crack segmentation before property interpretation.

References:
- NASA dataset and label mapping: https://github.com/nasa/pretrained-microscopy-models
- MicroNet segmentation publication: https://doi.org/10.1038/s41524-022-00878-5
- 2-D versus 3-D microstructure caution: https://pmc.ncbi.nlm.nih.gov/articles/PMC11620251/
