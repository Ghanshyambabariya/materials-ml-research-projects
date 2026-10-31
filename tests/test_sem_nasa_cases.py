from pathlib import Path
import sys
import pytest

HERE=Path(__file__).resolve().parents[1]/"projects"/"sem-physics-ml"
sys.path.insert(0,str(HERE))
from run_nasa_cases import NASA_SAMPLES, url_for, load_model


def test_test_annotation_paths_and_escaping():
    assert len(NASA_SAMPLES)==3
    assert all("/test_annot/" in path for path in NASA_SAMPLES.values())
    assert all("%23" in url_for(path) for path in NASA_SAMPLES.values())


def test_checkpoint_loader_if_available():
    path=HERE/"results/v2/transport_cnn_variable_k.pt"
    if not path.exists():pytest.skip("Train benchmark_v2 first")
    model,size=load_model(path)
    assert size==24
    assert model is not None
