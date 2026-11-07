import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from fairmaterials.cli import main


class CLITests(unittest.TestCase):
    def test_cli_end_to_end_and_failure_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def run(*args):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    main(['--root', str(root/'store'), *map(str,args)])
                return json.loads(output.getvalue())
            demo = root/'demo'
            run('demo', demo)
            self.assertEqual(run('validate',demo/'materials.csv',demo/'metadata.json')['measurements'],180)
            dataset = run('ingest',demo/'materials.csv',demo/'metadata.json')['dataset_id']
            self.assertEqual(len(run('search','--data-kind','synthetic')),1)
            self.assertEqual(run('search','--data-kind','experimental'),[])
            self.assertEqual(run('search','--material',"' OR 1=1 --"),[])
            run_id = run('evaluate',dataset,'--outer-folds','3','--inner-folds','2','--bootstrap-samples','20')['run_id']
            run('export',run_id,root/'bundle')
            self.assertEqual(run('verify',root/'bundle','--reproduce')['reproduction'],'passed')
            artifact = run('artifact-add',dataset,demo/'materials.csv','--kind','raw_data','--description','Synthetic CSV','--run-id',run_id)['artifact_id']
            self.assertEqual(len(run('artifact-list',dataset)),1)
            run('artifact-get',artifact,root/'recovered.csv')
            self.assertTrue(run('audit')['ok'])
            run('backup',root/'backup')
            self.assertTrue(run('restore',root/'backup',root/'restored')['audit']['ok'])
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                run('validate',root/'missing.csv',demo/'metadata.json')
            self.assertEqual(error.exception.code,2)
            # Audit must signal failure to scripts, rather than returning successful exit status.
            obj = next((root/'store/objects').rglob('materials.csv'))
            obj.write_text('corrupt')
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(['--root',str(root/'store'),'audit'])
            self.assertEqual(error.exception.code,1)


if __name__ == '__main__':
    unittest.main()
