"""Compare identical CNNs: data-only, PDE-regularized and PDE + boundary flux."""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from matplotlib import pyplot as plt
from model import TransportCNN, physics_residual
from physics import conductivity, effective_conductivity, solve_temperature, synthetic_masks
from methods import orient

HERE = Path(__file__).resolve().parent


def examples(count, size, seed):
    masks = synthetic_masks(count,size,seed)
    rng = np.random.default_rng(seed+10000)
    labels, conductivities, targets, case_labels = [], [], [], []
    for i, mask in enumerate(masks):
        direction = "x" if i%2 == 0 else "y"
        values = (1.,float(rng.uniform(.15,.75)),float(rng.uniform(.015,.12)))
        phase = orient(mask,direction)
        k = conductivity(phase,values)
        labels.append(phase.copy())
        conductivities.append(k)
        targets.append(solve_temperature(k))
        case_labels.append({"direction":direction,"k":values})
    return (torch.tensor(np.stack(labels),dtype=torch.long),
            torch.tensor(np.stack(conductivities),dtype=torch.float32),
            torch.tensor(np.stack(targets),dtype=torch.float32),case_labels)


def sample_metrics(net,batch):
    labels,k,target,_ = batch
    net.eval()
    with torch.no_grad():
        pred = net(labels,k)
        residual = physics_residual(pred,k)
        mae = (pred-target).abs().mean(dim=(1,2)).numpy()
        rmse = residual.square().mean(dim=(1,2)).sqrt().numpy()
    relative = []
    for i in range(len(k)):
        conductivity_map = k[i].numpy()
        reference = effective_conductivity(conductivity_map,target[i].numpy())
        estimated = effective_conductivity(conductivity_map,pred[i].numpy())
        relative.append(abs(estimated-reference)/max(abs(reference),1e-10))
    return {"temperature_mae":float(mae.mean()),
            "pde_residual_rmse":float(rmse.mean()),
            "relative_proxy_error":float(np.mean(relative))}


def fit(train,val,seed,alpha,epochs,width=16,flux_weight=0.):
    torch.manual_seed(seed)
    network = TransportCNN(width)
    optimizer = torch.optim.Adam(network.parameters(),lr=.002)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=epochs)
    x,k,t,_ = train
    xv,kv,tv,_ = val
    best=float("inf")
    state=None
    history=[]
    tic=time.perf_counter()
    for epoch in range(epochs):
        network.train()
        for ids in torch.randperm(len(x)).split(16):
            pred=network(x[ids],k[ids])
            mse=(pred-t[ids]).square().mean()
            pde=physics_residual(pred,k[ids]).square().mean()
            bounds=(torch.relu(-pred).square()+torch.relu(pred-1).square()).mean()
            loss=mse+alpha*pde+.5*bounds
            if flux_weight:
                face=2*k[ids,:,0]*k[ids,:,1]/(k[ids,:,0]+k[ids,:,1])
                scale=k.shape[-1]-1
                flux=(face*(pred[:,:,0]-pred[:,:,1])).mean(dim=1)*scale
                desired=(face*(t[ids,:,0]-t[ids,:,1])).mean(dim=1)*scale
                loss=loss+flux_weight*((flux-desired)/(desired.abs()+1e-6)).square().mean()
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(network.parameters(),2.)
            optimizer.step()
        scheduler.step()
        network.eval()
        with torch.no_grad():
            validation_mse=float((network(xv,kv)-tv).square().mean())
        if validation_mse<best:
            best=validation_mse
            state={name:w.detach().clone() for name,w in network.state_dict().items()}
        if epoch in (0,epochs//2-1,epochs-1):
            history.append({"epoch":epoch+1,"validation_mse":validation_mse})
    network.load_state_dict(state)
    return network, time.perf_counter()-tic,history


def cpu_inference_speed(network,batch,repeats=10):
    x,k,_,_=batch
    network.eval()
    with torch.no_grad():
        for _ in range(3):network(x,k)
        cnn=[]
        for _ in range(repeats):
            tic=time.perf_counter()
            network(x,k)
            cnn.append(time.perf_counter()-tic)
    solver=[]
    for _ in range(3):
        tic=time.perf_counter()
        for Ki in k.numpy():solve_temperature(Ki)
        solver.append(time.perf_counter()-tic)
    return {"cnn_batch_median_s":float(np.median(cnn)),
            "finite_volume_batch_median_s":float(np.median(solver)),
            "cnn_vs_solver_speed_ratio":float(np.median(solver)/np.median(cnn)),
            "batch_size":len(x),
            "hardware":os.environ.get("GITHUB_RUNNER_NAME","local CPU"),
            "note":"24x24 CPU batch; excludes training and synthetic-data generation."}


def plot_results(output,batch,network,trials):
    masks,k,target,_=batch
    with torch.no_grad():
        pred=network(masks[:1],k[:1])[0].numpy()
    reference=target[0].numpy()
    fig,axes=plt.subplots(1,4,figsize=(13,3.5),layout="constrained")
    panels=((masks[0].numpy(),"Synthetic mask","viridis"),
            (reference,"Numerical reference","inferno"),
            (pred,"Physics + flux CNN","inferno"),
            (abs(reference-pred),"Absolute difference","magma"))
    for ax,(data,title,cmap) in zip(axes,panels):
        ax.imshow(data,cmap=cmap)
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.savefig(output/"temperature_fields.png",dpi=150)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4),layout="constrained")
    for col,(name,label) in enumerate((("cnn","CNN"),("physics_cnn","PDE loss"),("physics_cnn_flux","PDE + flux"))):
        values=[row[name]["test"]["temperature_mae"] for row in trials]
        ax.scatter([col]*len(values),values)
    ax.set_xticks([0,1,2],["CNN","PDE","PDE + flux"])
    ax.set_ylabel("Test temperature MAE")
    fig.savefig(output/"repeatability.png",dpi=150)
    plt.close(fig)


def study(seeds=(5,17,29),epochs=65,size=24,train_count=48,output=HERE/"results/v2"):
    torch.set_num_threads(min(2,torch.get_num_threads()))
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    train=examples(train_count,size,100)
    val=examples(16,size,101)
    test=examples(24,size,102)
    trials=[]
    final_model=None
    for seed in seeds:
        row={"seed":seed}
        for name,alpha,flux_weight in (("cnn",0.,0.),("physics_cnn",.5,0.),("physics_cnn_flux",.5,.002)):
            net,seconds,history=fit(train,val,seed,alpha,epochs,flux_weight=flux_weight)
            row[name]={"train_s":seconds,"history":history,"test":sample_metrics(net,test)}
            if name=="physics_cnn_flux":
                final_model=net
        trials.append(row)
    torch.save({"model_state":final_model.state_dict(),"width":16,"size":size,
                "model_name":"physics_cnn_flux","training_seed":seeds[-1],"epochs":epochs,
                "trained_on":"synthetic procedural masks with variable phase conductivity",
                "not_validated_on_real_sem":True}, output/"transport_cnn_variable_k.pt")
    timing=cpu_inference_speed(final_model,test)
    summary={}
    for metric in ("temperature_mae","pde_residual_rmse","relative_proxy_error"):
        values={name:np.array([r[name]["test"][metric] for r in trials]) for name in
                ("cnn","physics_cnn","physics_cnn_flux")}
        summary[metric]={f"{name}_mean":float(v.mean()) for name,v in values.items()}
        summary[metric].update({f"{name}_sd":float(v.std(ddof=1)) if len(v)>1 else None
                                for name,v in values.items()})
        summary[metric]["flux_better_than_cnn_seeds"]=int((values["physics_cnn_flux"]<values["cnn"]).sum())
        summary[metric]["n_seeds"]=len(seeds)
    result={"experiment_version":2,"torch_version":torch.__version__,"numpy_version":np.__version__,
            "data_provenance":"synthetic procedural masks only","n_train":train_count,
            "n_val":16,"n_test":24,"size":size,"epochs":epochs,
            "training_conditions":"background k=1; oxide k in [0.15,0.75]; crack k in [0.015,0.12]",
            "transport_direction":"both x and y (rotate y maps into x frame)",
            "seeds":trials,"summary":summary,"runtime":timing,
            "limits":"No experimental thermal properties; original U-Net checkpoint unavailable. Repeated seeds use one test set."}
    (output/"benchmark.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    plot_results(output,test,final_model,trials)
    md=["# Synthetic variable-conductivity study","",
        "Three separate seeds on the same synthetic test maps (no measured thermal labels).","",
        "| Metric | Data-only CNN | CNN + PDE | CNN + PDE + flux | Flux improves vs baseline |",
        "|---|---:|---:|---:|---:|"]
    for metric,score in summary.items():
        md.append(f"| {metric} | {score['cnn_mean']:.5f} | {score['physics_cnn_mean']:.5f} | {score['physics_cnn_flux_mean']:.5f} | {score['flux_better_than_cnn_seeds']}/{score['n_seeds']} |")
    md+=["",f"24-mask CPU batch inference: CNN {timing['cnn_batch_median_s']:.5f} s, finite-volume solver {timing['finite_volume_batch_median_s']:.5f} s. Ratio FVM/CNN {timing['cnn_vs_solver_speed_ratio']:.1f}x.",
         "Speed depends on hardware and size, and excludes model training.",
         "Flux loss uses numerical reference flux; this is supervised flux regularization, not an independent physical measurement.",
         "", "![Numerical and predicted fields](temperature_fields.png)",
         "", "![Across-seed temperature errors](repeatability.png)",""]
    (output/"benchmark.md").write_text("\n".join(md),encoding="utf-8")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--epochs",type=int,default=65)
    p.add_argument("--seeds",type=int,nargs="+",default=[5,17,29])
    p.add_argument("--output",type=Path,default=HERE/"results/v2")
    a=p.parse_args()
    if a.epochs<1 or not a.seeds:p.error("epochs and seeds required")
    result=study(seeds=a.seeds,epochs=a.epochs,output=a.output)
    print(json.dumps({"summary":result["summary"],"runtime":result["runtime"]},indent=2))
