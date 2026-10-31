"""Evaluate synthetic-trained ANN on held-out public NASA EBC annotation geometry.

No original SEM U-Net weights or experimentally measured conductivity is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path
import numpy as np
import torch
from methods import audit_resizing
from physics import conductivity, effective_conductivity, solve_temperature
from model import TransportCNN
from validate_sem import read_native_mask, analyze_mask

NASA_REPO = "https://github.com/nasa/pretrained-microscopy-models"
NASA_SAMPLES = {
    "EBC1": "benchmark_segmentation_data/EBC1/test_annot/040617#2_S127(2)0015.tif",
    "EBC2": "benchmark_segmentation_data/EBC2/test_annot/050317#3_S0440016.tif",
    "EBC3": "benchmark_segmentation_data/EBC3/test_annot/050317#3_S0440017.tif",
}
HERE = Path(__file__).resolve().parent


def url_for(path):
    return ("https://raw.githubusercontent.com/nasa/pretrained-microscopy-models/main/"
            +urllib.parse.quote(path,safe="/"))


def load_model(path):
    saved = torch.load(path,map_location="cpu",weights_only=True)
    if saved.get("model_name") != "physics_cnn_flux":
        raise ValueError("Unexpected surrogate checkpoint")
    net = TransportCNN(width=int(saved["width"]))
    net.load_state_dict(saved["model_state"],strict=True)
    net.eval()
    return net,int(saved["size"])


def run(output,model_path,source_dir=None):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    net,model_size=load_model(model_path)
    cases=[]
    for name,path in NASA_SAMPLES.items():
        destination=(Path(source_dir)/(name+".tif")) if source_dir else output/"downloaded"/(name+".tif")
        if not destination.exists():
            destination.parent.mkdir(parents=True,exist_ok=True)
            urllib.request.urlretrieve(url_for(path),destination)
        raw=destination.read_bytes()
        mask=read_native_mask(destination)
        full=analyze_mask(mask,size=72,direction="y")
        full.pop("_mask_for_plot")
        audit=audit_resizing(mask,model_size)
        small=audit.pop("coarse_mask")
        small=np.rot90(small).copy()
        k=conductivity(small,(1.,.4,.05))
        reference=solve_temperature(k)
        with torch.inference_mode():
            predicted=net(torch.tensor(small,dtype=torch.long)[None],
                          torch.tensor(k.copy(),dtype=torch.float32)[None])[0].numpy()
        kr=effective_conductivity(k,reference)
        kp=effective_conductivity(k,predicted)
        cases.append({
            "dataset":name,
            "annotation_url":NASA_REPO+"/blob/main/"+urllib.parse.quote(path,safe="/"),
            "annotation_sha256":hashlib.sha256(raw).hexdigest(),
            "annotation_size":list(mask.shape),
            "original_class_pixels":{str(i):int(np.sum(mask==i)) for i in range(3)},
            "downsample_audit":audit,
            "modeled_y_transport_sensitivity":full["scenarios"],
            "synthetic_model_transfer": {
                "temperature_mae_vs_fvm":float(np.abs(predicted-reference).mean()),
                "proxy_relative_error":float(abs(kp-kr)/max(abs(kr),1e-12)),
                "proxy_fvm":kr,"proxy_cnn":kp
            },
            "limitations":"Real SEM annotation geometry with assumed k and 24px resizing; no original trained segmentation U-Net."
        })
    result={"source":"NASA pretrained-microscopy-models, public test annotations",
            "uses_real_sem_annotation_geometry":True,
            "uses_trained_sem_unet":False,
            "uses_experimental_thermal_properties":False,"cases":cases}
    (output/"nasa_ebc_cases.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    rows=["# NASA EBC mask transfer study","",
          "Real annotation geometries; hypothetical phase conductivities. No trained U-Net checkpoint was used.","",
          "| Dataset | Original crack pixels | All cracks lost at 24px? | CNN temperature MAE | Relative proxy error |",
          "|---|---:|---|---:|---:|"]
    for c in cases:
        stats=c["synthetic_model_transfer"]
        rows.append(f"| {c['dataset']} | {c['original_class_pixels']['2']} | {c['downsample_audit']['crack_lost_entirely']} | {stats['temperature_mae_vs_fvm']:.5f} | {stats['proxy_relative_error']:.1%} |")
    rows+=["","Flow along image y is a provisional orientation, not independently checked from microscopy metadata.",
           "The proxy is not a measured material property. The network was trained only on procedural synthetic masks.",
           "",f"Source: {NASA_REPO}",""]
    (output/"nasa_ebc_cases.md").write_text("\n".join(rows),encoding="utf-8")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=HERE/"results/real_annotations")
    p.add_argument("--model",type=Path,default=HERE/"results/v2/transport_cnn_variable_k.pt")
    p.add_argument("--source-dir",type=Path,default=None)
    args=p.parse_args()
    print(json.dumps({"processed":len(run(args.out,args.model,args.source_dir)["cases"])},indent=2))
