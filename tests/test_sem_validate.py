from pathlib import Path
import sys
import numpy as np
import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]/"projects"/"sem-physics-ml"
sys.path.insert(0,str(ROOT))
from validate_sem import read_native_mask, analyze_mask, compare_masks


def test_annotation_scenarios(tmp_path):
    m=np.zeros((52,52),dtype=np.uint8)
    m[16:27,:]=1
    m[23,25:36]=2
    p=tmp_path/"test.tif"
    Image.fromarray(m).save(p)
    r=analyze_mask(read_native_mask(p),size=32)
    assert len(r["scenarios"])==3
    for scenario in r["scenarios"].values():
        assert scenario["conservation"]["node_flux_residual_rmse"]<1e-10
    assert r["scenarios"]["low_contrast"]["modeled_conductivity_proxy"]>r["scenarios"]["high_contrast"]["modeled_conductivity_proxy"]


def test_mask_errors_change_proxy():
    a=np.zeros((40,40),dtype=np.uint8)
    a[10:20,:]=1
    b=a.copy()
    b[:,15:20]=2
    r=compare_masks(a,b,size=32)
    assert r["class_iou"]["1"]<1
    assert r["scenario_change"]["medium_contrast"]["absolute_relative_change"]>0


def test_invalid_class_rejected(tmp_path):
    p=tmp_path/"bad.png"
    Image.fromarray(np.full((7,7),100,dtype=np.uint8)).save(p)
    with pytest.raises(ValueError):read_native_mask(p)
