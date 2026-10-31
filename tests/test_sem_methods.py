from pathlib import Path
import sys
import numpy as np
import pytest

HERE=Path(__file__).resolve().parents[1]/"projects"/"sem-physics-ml"
sys.path.insert(0,str(HERE))
from methods import directional_solution, phase_descriptors, audit_resizing, per_class_iou


def test_uniform_material_both_directions():
    mask=np.zeros((17,23),dtype=np.uint8)
    for direction in ("x","y"):
        r=directional_solution(mask,(.8,.4,.01),direction)
        assert r["conductivity_proxy"]==pytest.approx(.8,abs=1e-10)
        assert r["conservation"]["flux_balance_relative_error"]<1e-10
        assert r["conservation"]["node_flux_residual_rmse"]<1e-10


def test_layered_direction_changes_result():
    mask=np.zeros((18,18),dtype=np.uint8)
    mask[6:12,:]=1
    along=directional_solution(mask,(1,.1,.01),"x")["conductivity_proxy"]
    through=directional_solution(mask,(1,.1,.01),"y")["conductivity_proxy"]
    assert along>through


def test_conservation_heterogeneous():
    m=np.random.default_rng(5).integers(0,3,(16,18),dtype=np.uint8)
    for d in ("x","y"):
        r=directional_solution(m,direction=d)
        assert r["conservation"]["node_flux_residual_rmse"]<1e-10
        assert r["conservation"]["flux_balance_relative_error"]<1e-10


def test_crack_loss_is_detected():
    m=np.zeros((128,128),dtype=np.uint8)
    m[1,1]=2
    r=audit_resizing(m,8)
    assert r["crack_lost_entirely"]
    assert r["after"]["2"]==0 and r["before"]["2"]>0


def test_mask_components_and_iou():
    m=np.zeros((20,30),dtype=np.uint8)
    m[:,9]=2
    r=phase_descriptors(m)
    assert r["crack_spans_y"]
    assert not r["crack_spans_x"]
    assert per_class_iou(m,m)=={"0":1.,"1":None,"2":1.}
