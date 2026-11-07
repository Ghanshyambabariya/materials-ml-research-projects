"""Demonstrate metadata, artifacts, 20 kHz CSV features, nested CV, and recovery."""
import csv
import json
import uuid
from pathlib import Path

import numpy as np

from fairmaterials.artifacts import register, retrieve
from fairmaterials.data import canonical, demo
from fairmaterials.evaluation import evaluate
from fairmaterials.experiment import export_bundle, verify_bundle
from fairmaterials.operations import audit, backup, restore
from fairmaterials.signals import extract
from fairmaterials.store import Store, atomic_write


def main():
    root = Path('workspace/extensions') / str(uuid.uuid4())
    demo(root / 'input')
    metadata_path = root / 'input/metadata.json'
    metadata = json.loads(metadata_path.read_text())
    metadata.update({'schema_version':'1.1', 'access':'open', 'creator_type':'Organization', 'experiment': {'material':'Synthetic SiC example; not measured SiC', 'batch_id':'simulated-batch-01', 'method':'Synthetic 1250 Hz sine wave; no instrument acquisition', 'sampling_rate_hz':20000, 'modalities':['force', 'simulation'], 'processing_conditions': {'demonstration_amplitude': {'value':3, 'unit':'N'}}}})
    metadata_path.write_bytes(canonical(metadata))
    store = Store(root / 'store')
    identifier = store.ingest(root / 'input/materials.csv', metadata_path)
    signal = root / 'input/signal.csv'
    time = np.arange(4096)/20000
    with signal.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['time_s','Fx'])
        writer.writerows(zip(time, 3*np.sin(2*np.pi*1250*time)))
    report = extract(signal, 20000, {'Fx':'N'})
    report_path = root / 'input/signal-features.json'
    atomic_write(report_path, canonical(report))
    run_id, result = evaluate(store, identifier, outer_folds=3, inner_folds=2, bootstrap_samples=50)
    signal_id = register(store, identifier, signal, 'signal', 'Synthetic force CSV at 20 kHz', 'text/csv')
    register(store, identifier, report_path, 'report', 'Signal features linked to source SHA-256', 'application/json', run_id)
    bundle = export_bundle(store, run_id, root / 'evaluation-bundle')
    verify_bundle(bundle, True)
    retrieve(store, signal_id, root / 'recovered-signal.csv')
    snapshot = root / 'backup'
    backup(store, snapshot)
    recovery = restore(snapshot, root / 'restored-store')
    print(json.dumps({'root':str(root), 'dataset_id':identifier, 'evaluation_run_id':run_id, 'metrics':result['metrics'], 'uncertainty':result['uncertainty'], 'signal_dominant_frequency_hz':report['windows'][0]['channels']['Fx']['dominant_frequency_hz'], 'audit':audit(store), 'recovery':recovery['audit']}, indent=2))


if __name__ == '__main__':
    main()
