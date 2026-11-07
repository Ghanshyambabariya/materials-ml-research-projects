import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from jsonschema import ValidationError

from fairmaterials.artifacts import file_digest, list_artifacts, register, retrieve
from fairmaterials.data import canonical, demo, validate
from fairmaterials.evaluation import evaluate, nested
from fairmaterials.experiment import export_bundle, train, verify_bundle
from fairmaterials.operations import audit, backup, restore
from fairmaterials.signals import extract
from fairmaterials.store import Store


class ExtensionsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        demo(self.root / 'demo')
        self.csv = self.root / 'demo/materials.csv'
        self.metadata_path = self.root / 'demo/metadata.json'
        self.metadata = json.loads(self.metadata_path.read_text())
        self.store = Store(self.root / 'store')
        self.identifier = self.store.ingest(self.csv, self.metadata_path)

    def test_rich_metadata_and_legacy_compatibility(self):
        self.metadata.update({'schema_version': '1.1', 'creator_type': 'Person', 'access': 'restricted', 'experiment': {'material': 'SiC', 'batch_id': 'synthetic-batch', 'method': 'Synthetic workflow demonstration only', 'sampling_rate_hz': 20000, 'calibration_date': '2026-11-01', 'modalities': ['force', 'torque'], 'processing_conditions': {'feed_speed': {'value': 2, 'unit': 'mm/s'}}}, 'related_resources': [{'relation': 'protocol', 'identifier': 'https://example.org/protocol'}]})
        self.assertEqual(len(validate(self.metadata, self.csv.read_bytes())), 180)
        self.metadata['experiment']['sampling_rate_hz'] = -1
        with self.assertRaises(ValidationError):
            validate(self.metadata, self.csv.read_bytes())

    def test_metadata_no_self_parent_or_nonfinite_conditions(self):
        self.metadata['parent_identifier'] = self.identifier
        with self.assertRaises(ValueError):
            validate(self.metadata, self.csv.read_bytes())
        self.metadata.pop('parent_identifier')
        self.metadata['experiment'] = {'material':'quartz', 'batch_id':'x', 'method':'Synthetic test only', 'processing_conditions': {'speed': {'value': float('nan'), 'unit':'mm/s'}}}
        with self.assertRaises(ValueError):
            validate(self.metadata, self.csv.read_bytes())

    def artifact(self):
        source = self.root / 'weights.bin'
        source.write_bytes(b'opaque weights, never executed\x00' * 1000)
        return register(self.store, self.identifier, source, 'weights', 'Synthetic test weights'), source

    def test_artifact_roundtrip_stream_hash_and_no_overwrite(self):
        identifier, source = self.artifact()
        rows = list_artifacts(self.store, self.identifier)
        self.assertEqual(rows[0]['id'], identifier)
        target = self.root / 'download.bin'
        retrieve(self.store, identifier, target)
        self.assertEqual(file_digest(source), file_digest(target))
        with self.assertRaises(FileExistsError):
            retrieve(self.store, identifier, target)
        self.assertTrue(audit(self.store)['ok'])

    def test_artifact_corruption_removes_partial_download(self):
        identifier, _ = self.artifact()
        row = list_artifacts(self.store, self.identifier)[0]
        (self.store.root / row['object_path']).write_bytes(b'corrupt')
        target = self.root / 'download.bin'
        with self.assertRaisesRegex(ValueError, 'integrity'):
            retrieve(self.store, identifier, target)
        self.assertFalse(target.exists())
        self.assertFalse(audit(self.store)['ok'])

    def test_artifact_invalid_kind_and_run(self):
        source = self.root / 'input'
        source.write_bytes(b'test')
        for kind, run_id in [('bad', None), ('weights', 'missing')]:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                register(self.store, self.identifier, source, kind, 'test artifact', run_id=run_id)

    def test_run_linked_artifact(self):
        run_id, _ = train(self.store, self.identifier)
        source = self.root / 'architecture.json'
        source.write_text('{"model":"ridge"}')
        register(self.store, self.identifier, source, 'architecture', 'Portable model architecture', run_id=run_id)
        self.assertEqual(list_artifacts(self.store, self.identifier)[0]['run_id'], run_id)

    def test_nested_splits_no_leakage_and_full_reproduction(self):
        run_id, result = evaluate(self.store, self.identifier, outer_folds=3, inner_folds=2, bootstrap_samples=20)
        ids = []
        for fold in result['folds']:
            outer_test = set(fold['test_specimens'])
            self.assertTrue(outer_test.isdisjoint(fold['train_specimens']))
            ids.extend(fold['test_ids'])
            for inner in fold['inner_splits']:
                self.assertTrue(set(inner['train_specimens']).isdisjoint(inner['validation_specimens']))
                self.assertTrue(outer_test.isdisjoint(inner['train_specimens'] + inner['validation_specimens']))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 180)
        self.assertLess(result['metrics']['mae_mpa'], result['baseline_metrics']['mae_mpa'])
        bundle = export_bundle(self.store, run_id, self.root / 'nested-bundle')
        self.assertEqual(verify_bundle(bundle, True)['reproduction'], 'passed')

    def test_nested_repeatable_and_invalid_config(self):
        rows = validate(self.metadata, self.csv.read_bytes())
        a = nested(rows, outer_folds=3, inner_folds=2, bootstrap_samples=20)
        b = nested(rows, outer_folds=3, inner_folds=2, bootstrap_samples=20)
        self.assertEqual(a, b)
        for params in [{'outer_folds': 100}, {'inner_folds': 100}, {'alphas': []}, {'alphas': [0]}, {'bootstrap_samples': 0}, {'seed': -1}]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                nested(rows, **params)

    def signal(self, values=None, rate=20000):
        path = self.root / 'signals.csv'
        time = np.arange(4096) / rate
        force = 3 * np.sin(2*np.pi*1250*time) if values is None else values
        with path.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['time_s', 'Fx'])
            writer.writerows(zip(time, force))
        return path

    def test_signal_known_frequency_amplitude_and_psd(self):
        report = extract(self.signal(), 20000, {'Fx': 'N'})
        self.assertEqual(len(report['windows']), 2)
        channel = report['windows'][0]['channels']['Fx']
        self.assertAlmostEqual(channel['rms'], 3/np.sqrt(2), places=8)
        self.assertAlmostEqual(channel['dominant_frequency_hz'], 1250, places=8)
        self.assertAlmostEqual(channel['variance_from_psd'], 4.5, places=7)

    def test_signal_zero_and_invalid_rate_units_missing_values(self):
        path = self.signal(np.zeros(4096))
        self.assertEqual(extract(path, 20000, {'Fx':'N'})['windows'][0]['channels']['Fx']['crest_factor'], 0)
        for rate, units, window in [(0, {'Fx':'N'}, 2048), (10000, {'Fx':'N'}, 2048), (20000, {'Fx':'V'}, 2048), (20000, {'Fx':'N'}, 3), (20000, {'Fx':'N'}, 10000)]:
            with self.subTest(rate=rate, units=units), self.assertRaises(ValueError):
                extract(path, rate, units, window)
        path.write_text('time_s,Fx\n0,\n')
        with self.assertRaises(ValueError):
            extract(path, 20000, {'Fx':'N'})

    def test_backup_restore_including_run_and_artifact(self):
        train(self.store, self.identifier)
        self.artifact()
        original = audit(self.store)
        self.assertTrue(original['ok'])
        snapshot = self.root / 'backup'
        backup(self.store, snapshot)
        destination = self.root / 'restored'
        self.assertTrue(restore(snapshot, destination)['audit']['ok'])
        restored = Store(destination)
        self.assertEqual(audit(restored), original)
        self.assertEqual(restored.load(self.identifier)[2], self.csv.read_bytes())
        with self.assertRaises(ValueError):
            backup(self.store, snapshot)
        with self.assertRaises(ValueError):
            restore(snapshot, destination)

    def test_backup_corruption_and_traversal_rejected(self):
        snapshot = self.root / 'backup'
        backup(self.store, snapshot)
        manifest = snapshot / 'backup-checksums.json'
        original = json.loads(manifest.read_text())
        manifest.write_bytes(canonical({**original, '../outside': 'bad'}))
        with self.assertRaises((ValueError, OSError)):
            restore(snapshot, self.root / 'restored')
        manifest.write_bytes(canonical(original))
        (snapshot / 'catalog.sqlite').write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            restore(snapshot, self.root / 'restored')

    def test_audit_reports_orphan_and_manifest_mismatch(self):
        run_id, _ = train(self.store, self.identifier)
        orphan = self.store.root / 'objects/orphan.bin'
        orphan.write_bytes(b'orphan')
        report = audit(self.store)
        self.assertTrue(report['ok'])
        self.assertEqual(report['unreferenced_objects'], ['objects/orphan.bin'])
        (self.store.root / 'runs' / run_id / 'manifest.json').write_text('{}')
        self.assertFalse(audit(self.store)['ok'])

    def test_catalog_object_path_escape_rejected(self):
        with self.store.connect() as connection:
            connection.execute('UPDATE datasets SET object_path=? WHERE id=?', ('../outside', self.identifier))
        with self.assertRaises(ValueError):
            self.store.load(self.identifier)


if __name__ == '__main__':
    unittest.main()
