# Research basis and methodology

## FAIR stewardship

Wilkinson et al., *The FAIR Guiding Principles for scientific data management and stewardship*, Scientific Data 3, 160018 (2016). https://doi.org/10.1038/sdata.2016.18

Dataset UUIDs, structured metadata, explicit units, provenance, licenses, and catalog discovery provide the implemented stewardship mechanisms. UUIDs identify immutable snapshots; SHA-256 identifies file content. The catalog is local and has no external persistent-identifier service.

## Research-object representation

Research Object Crate specification 1.2. https://www.researchobject.org/ro-crate/specification/1.2/

The exporter creates a metadata descriptor, root Dataset, typed creator, license entity, and file descriptions using the explicitly versioned RO-Crate 1.2 JSON-LD context. Checksums are separate. Tests cover bundle integrity and reproduction; independent RO-Crate conformance validation is not included.

## Grouped model evaluation

Scikit-learn common pitfalls: https://scikit-learn.org/stable/common_pitfalls.html
Grouped cross-validation: https://scikit-learn.org/stable/modules/cross_validation.html
Nested cross-validation: https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html

Repeated measurements from one specimen remain in the same partition. StandardScaler fits on training data. Holdout evaluation uses a fixed Ridge penalty and a training-mean baseline. Nested evaluation selects the penalty in grouped inner folds and evaluates predictions on grouped outer folds.

Recorded fold identities, parameters, data hashes, software versions, predictions, and Git provenance support reproduction. Verification compares numerical results within 1e-9 relative and absolute tolerance. The specimen-cluster bootstrap resamples fixed out-of-fold errors; its interval describes conditional error variability rather than full model-training uncertainty.

## Signal analysis

SciPy Welch spectral estimation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html

Signal inputs contain calibrated physical values and timestamps. Timestamp spacing is checked against the declared sampling rate. Non-overlapping windows produce time-domain features and mean-detrended Hann-window Welch density estimates. Spectral summaries include dominant frequency, spectral centroid, and PSD-derived variance. Hardware acquisition, calibration, and filtering are not part of this implementation.

## Storage consistency

Python SQLite backup API: https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
SQLite transactions: https://www.sqlite.org/lang_transaction.html
JSON Schema 2020-12: https://json-schema.org/draft/2020-12

Parameterized SQL maintains catalog relationships. Content-addressed files preserve snapshots, and atomic replacement prevents partial object writes. SQLite backup captures the catalog; referenced objects and reconstructed run manifests complete the storage snapshot. Backup restoration includes checksum and catalog audits.

## Validation data

The strength example has 180 synthetic measurements across 60 specimens. The signal example is a synthetic 1250 Hz sine wave sampled at 20 kHz. Reported example metrics describe computational workflow behavior, not experimentally established material properties.
