# Research basis and design decisions

Research reviewed: 7 November 2026. Sources below are primary publications or official specifications and documentation. This is a focused engineering review, not a systematic literature review.

## 1. FAIR stewardship

Wilkinson et al., *The FAIR Guiding Principles for scientific data management and stewardship*, Scientific Data 3, 160018 (2016). DOI: https://doi.org/10.1038/sdata.2016.18

The principles motivate discoverable identifiers, rich metadata, explicit access arrangements, interoperable representations, and reuse context. In this implementation:

| Aim | Implemented support | Remaining institutional work |
| --- | --- | --- |
| Findability | UUID, version, title, keywords, local catalog search | DOI/Handle registration, externally indexed metadata landing pages |
| Accessibility | Local CLI and portable files | Authenticated service, documented access requests, persistent metadata after data removal |
| Interoperability | CSV, JSON Schema, explicit units, JSON-LD export | Domain ontologies, ontology identifiers, community metadata profile review |
| Reusability | License, method provenance, hashes, versioned code | Domain validation, curation, preservation agreements |

The software does not calculate a numerical FAIR score or claim FAIR certification.

## 2. Research object packaging

Research Object Crate specification 1.2: https://www.researchobject.org/ro-crate/specification/1.2/
Introduction: https://www.researchobject.org/ro-crate/specification/1.2/introduction.html

The exporter targets the explicitly versioned 1.2 profile, not a moving latest specification. It emits a metadata descriptor, root Dataset, creator, license entity, and descriptions of the bundled data and run files. JSON-LD provides linked metadata relationships. Checksums are stored separately. Structural generation and bundle integrity are tested; an independent JSON-LD/RO-Crate validator and domain profile validation remain release requirements before claiming certified conformance.

## 3. Leakage and reproducible model evaluation

Official scikit-learn guidance: https://scikit-learn.org/stable/common_pitfalls.html
GroupShuffleSplit: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html
Model persistence considerations: https://scikit-learn.org/stable/model_persistence.html

Decision: split by specimen identity before fitting a preprocessing pipeline. Repeated measurements from one specimen share latent properties, so placing them in both partitions would weaken independence. GroupShuffleSplit's test fraction refers to groups, not an exact fraction of rows. StandardScaler fits only the training partition; Ridge uses fixed alpha and no test-set tuning. A training-mean baseline gives evaluation context. Fixed seeds, recorded partition IDs, pinned dependencies, data hashes, and Git provenance support repeatability.

A single holdout evaluates the workflow and does not establish performance on unseen material families, instruments, laboratories, or time periods. Real deployments should define independent acquisition batches, nested grouped cross-validation for tuning, uncertainty estimates, external validation, and scientifically justified feature sets before examining held-out results.

Portable model parameters are JSON arrays and scalars, avoiding executable pickle artifacts. Prediction uses `(x - mean) / scale @ coefficients + intercept`, in the recorded feature order. Reproduction refits and compares predictions and metrics within 1e-9 relative/absolute tolerances. Identical bytes across platforms are not promised.

## 4. Durable local storage

SQLite transactions: https://www.sqlite.org/lang_transaction.html
Python sqlite3: https://docs.python.org/3/library/sqlite3.html
JSON Schema 2020-12: https://json-schema.org/draft/2020-12

Decision: store data bytes by SHA-256 and use parameterized SQL to maintain catalog relationships. The metadata contract is versioned in source control. Atomic file replacement avoids exposing partial object writes. Filesystem writes and SQL commits are separate durability domains; failures can leave unreferenced files or a catalog run without its convenience manifest copy. The authoritative run JSON is stored in SQL, so export does not depend on that copy. Back up catalog and objects together. Checksums detect accidental corruption but do not authenticate an adversarially modified bundle.

## Research questions supported by this implementation

1. Can the same registered dataset and fixed configuration reproduce held-out predictions?
2. Does grouping prevent overlap of specimen identities between partitions?
3. Can corrupted data and metadata be detected before training or reuse?
4. Can a portable bundle reproduce independently of the original catalog?

These are engineering validation questions. The synthetic dataset is not suitable for new claims about material properties.

## 5. Version 0.2 extensions

Official grouped-validation guidance: https://scikit-learn.org/stable/modules/cross_validation.html
Nested model-selection rationale: https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html
Welch spectral estimation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html
SQLite online backup API: https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup

Decision: parameter selection happens inside each outer training partition with grouped inner folds. The outer test partition remains excluded from scaling and parameter choice. Out-of-fold errors are pooled, and an optional specimen-cluster bootstrap summarizes their conditional variation. The bootstrap resamples fixed errors; it does not refit models and must not be interpreted as full model uncertainty.

Signal analysis uses explicit physical channel units and checks uniform timestamp spacing before computing features. Mean-detrended Hann-window Welch density estimates provide frequency and variance summaries. There is no instrument-driver, calibration, or anti-aliasing implementation. Streaming artifact storage preserves proprietary exports without interpreting them; format-aware adapters require actual source specifications.

Backup uses a consistent SQLite catalog snapshot plus its referenced immutable objects. Staged publication and restore audit support recovery testing without claiming an operational backup service.
