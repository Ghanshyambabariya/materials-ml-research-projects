from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def write_svg(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.strip() + "\n", encoding="utf-8")


def system_architecture_svg() -> str:
    return """<svg width="1400" height="760" viewBox="0 0 1400 760" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1400" y2="760" gradientUnits="userSpaceOnUse">
      <stop stop-color="#07111D"/>
      <stop offset="0.55" stop-color="#0C2430"/>
      <stop offset="1" stop-color="#102418"/>
    </linearGradient>
    <filter id="shadow" x="-15%" y="-15%" width="130%" height="130%">
      <feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#000000" flood-opacity="0.28"/>
    </filter>
    <style>
      .title{font:700 42px Segoe UI,Arial,sans-serif;fill:#F8FAFC}
      .subtitle{font:500 20px Segoe UI,Arial,sans-serif;fill:#C7D2DE}
      .section{font:700 24px Segoe UI,Arial,sans-serif;fill:#F8FAFC}
      .body{font:500 17px Segoe UI,Arial,sans-serif;fill:#D9E4EC}
      .tag{font:700 13px Segoe UI,Arial,sans-serif;letter-spacing:.08em;fill:#88D8CF}
      .small{font:600 14px Segoe UI,Arial,sans-serif;fill:#A9B8C6}
      .card{rx:24;filter:url(#shadow)}
      .line{stroke:#7AD9CF;stroke-width:3;stroke-linecap:round}
      .muted{stroke:#91A3B5;stroke-width:2;stroke-opacity:.45;stroke-dasharray:8 10}
    </style>
  </defs>
  <rect width="1400" height="760" fill="url(#bg)"/>
  <circle cx="1190" cy="96" r="105" stroke="#6CE5D5" stroke-opacity=".16" stroke-width="2"/>
  <circle cx="1278" cy="190" r="68" stroke="#F4C95D" stroke-opacity=".18" stroke-width="2"/>
  <text x="74" y="82" class="title">Materials ML Research Architecture</text>
  <text x="76" y="122" class="subtitle">Data, preprocessing, models, and reports kept as separate reproducible layers.</text>

  <rect x="78" y="190" width="270" height="180" class="card" fill="#10243A" stroke="#3F83C6"/>
  <text x="106" y="228" class="tag">01 INPUTS</text>
  <text x="106" y="268" class="section">Data Layer</text>
  <text x="106" y="304" class="body">image registries</text>
  <text x="106" y="332" class="body">sensor tables</text>
  <text x="106" y="360" class="body">property datasets</text>

  <rect x="405" y="190" width="270" height="180" class="card" fill="#102B31" stroke="#2B8C99"/>
  <text x="433" y="228" class="tag">02 CLEANING</text>
  <text x="433" y="268" class="section">Preprocessing</text>
  <text x="433" y="304" class="body">schema checks</text>
  <text x="433" y="332" class="body">feature extraction</text>
  <text x="433" y="360" class="body">grouped splits</text>

  <rect x="732" y="190" width="270" height="180" class="card" fill="#302815" stroke="#BE9440"/>
  <text x="760" y="228" class="tag">03 MODELS</text>
  <text x="760" y="268" class="section">Model Layer</text>
  <text x="760" y="304" class="body">UNet / DeepLab</text>
  <text x="760" y="332" class="body">Random Forest</text>
  <text x="760" y="360" class="body">encoder registry</text>

  <rect x="1059" y="190" width="270" height="180" class="card" fill="#202944" stroke="#728FE4"/>
  <text x="1087" y="228" class="tag">04 OUTPUTS</text>
  <text x="1087" y="268" class="section">Evaluation</text>
  <text x="1087" y="304" class="body">IoU / F1 / R2</text>
  <text x="1087" y="332" class="body">figures</text>
  <text x="1087" y="360" class="body">Markdown reports</text>

  <path d="M356 280 H397" class="line"/>
  <path d="M683 280 H724" class="line"/>
  <path d="M1010 280 H1051" class="line"/>

  <path d="M213 404 V454" class="muted"/>
  <path d="M540 404 V454" class="muted"/>
  <path d="M867 404 V454" class="muted"/>
  <path d="M1194 404 V454" class="muted"/>

  <rect x="62" y="470" width="290" height="150" class="card" fill="#0D1F32" stroke="#385C8C"/>
  <text x="88" y="510" class="section">Microscopy CV</text>
  <text x="88" y="548" class="body">segmentation masks</text>
  <text x="88" y="576" class="body">active learning</text>
  <text x="88" y="608" class="small">project: sem-segmentation</text>

  <rect x="386" y="470" width="290" height="150" class="card" fill="#102D2D" stroke="#2B8C99"/>
  <text x="412" y="510" class="section">Process Signals</text>
  <text x="412" y="548" class="body">20 kHz force windows</text>
  <text x="412" y="576" class="body">spectral features</text>
  <text x="412" y="608" class="small">project: process-signal-ml</text>

  <rect x="710" y="470" width="290" height="150" class="card" fill="#302815" stroke="#BE9440"/>
  <text x="736" y="510" class="section">Tool Wear</text>
  <text x="736" y="548" class="body">public machining data</text>
  <text x="736" y="576" class="body">grouped validation</text>
  <text x="736" y="608" class="small">project: tool-wear-prediction</text>

  <rect x="1034" y="470" width="290" height="150" class="card" fill="#172E20" stroke="#66B879"/>
  <text x="1060" y="510" class="section">Property ML</text>
  <text x="1060" y="548" class="body">tabular regression</text>
  <text x="1060" y="576" class="body">feature importance</text>
  <text x="1060" y="608" class="small">project: concrete-strength-ml</text>
</svg>"""


def active_learning_svg() -> str:
    return """<svg width="1400" height="460" viewBox="0 0 1400 460" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg2" x1="0" y1="0" x2="1400" y2="460" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0B1220"/>
      <stop offset="1" stop-color="#16302C"/>
    </linearGradient>
    <style>
      .title{font:700 38px Segoe UI,Arial,sans-serif;fill:#F8FAFC}
      .label{font:700 22px Segoe UI,Arial,sans-serif;fill:#F8FAFC}
      .text{font:500 16px Segoe UI,Arial,sans-serif;fill:#D7E2EA}
      .num{font:700 13px Segoe UI,Arial,sans-serif;letter-spacing:.08em;fill:#75D8D0}
      .step{filter:drop-shadow(0 10px 14px rgba(0,0,0,.28))}
      .arrow{stroke:#6CE5D5;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
      .loop{stroke:#8FA6B8;stroke-width:2;stroke-dasharray:8 10;stroke-opacity:.55}
    </style>
  </defs>
  <rect width="1400" height="460" rx="30" fill="url(#bg2)"/>
  <text x="64" y="72" class="title">Low-Label SEM Active Learning Loop</text>
  <g class="step">
    <rect x="64" y="150" width="210" height="130" rx="22" fill="#13243B" stroke="#4D89C8"/>
    <text x="94" y="188" class="num">STEP 01</text>
    <text x="94" y="224" class="label">Seed Labels</text>
    <text x="94" y="254" class="text">small labeled subset</text>
  </g>
  <g class="step">
    <rect x="344" y="150" width="210" height="130" rx="22" fill="#122D35" stroke="#2B8C99"/>
    <text x="374" y="188" class="num">STEP 02</text>
    <text x="374" y="224" class="label">Train Model</text>
    <text x="374" y="254" class="text">segmentation baseline</text>
  </g>
  <g class="step">
    <rect x="624" y="150" width="230" height="130" rx="22" fill="#302B1A" stroke="#B9902E"/>
    <text x="654" y="188" class="num">STEP 03</text>
    <text x="654" y="224" class="label">Score Pool</text>
    <text x="654" y="254" class="text">uncertainty ranking</text>
  </g>
  <g class="step">
    <rect x="924" y="150" width="210" height="130" rx="22" fill="#202843" stroke="#6F8FE8"/>
    <text x="954" y="188" class="num">STEP 04</text>
    <text x="954" y="224" class="label">Select</text>
    <text x="954" y="254" class="text">highest uncertainty</text>
  </g>
  <g class="step">
    <rect x="1204" y="150" width="132" height="130" rx="22" fill="#172E20" stroke="#66B879"/>
    <text x="1231" y="188" class="num">STEP 05</text>
    <text x="1231" y="224" class="label">Report</text>
    <text x="1231" y="254" class="text">IoU / F1</text>
  </g>
  <path d="M282 215 H336" class="arrow"/>
  <path d="M562 215 H616" class="arrow"/>
  <path d="M862 215 H916" class="arrow"/>
  <path d="M1142 215 H1196" class="arrow"/>
  <path d="M1030 314 C860 395 520 395 450 314" class="loop"/>
  <text x="520" y="382" class="text">selected samples are added to the labeled set, then the model is trained again</text>
</svg>"""


def project_evidence_svg() -> str:
    return """<svg width="1400" height="560" viewBox="0 0 1400 560" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="1400" height="560" rx="30" fill="#F6F8F2"/>
  <style>
    .title{font:800 38px Segoe UI,Arial,sans-serif;fill:#132019}
    .subtitle{font:500 18px Segoe UI,Arial,sans-serif;fill:#506056}
    .h{font:800 23px Segoe UI,Arial,sans-serif;fill:#132019}
    .t{font:500 16px Segoe UI,Arial,sans-serif;fill:#34443A}
    .m{font:800 25px Segoe UI,Arial,sans-serif;fill:#0F5E5C}
    .k{font:700 12px Segoe UI,Arial,sans-serif;letter-spacing:.08em;fill:#607167}
    .card{filter:drop-shadow(0 8px 14px rgba(37,45,35,.12))}
  </style>
  <text x="64" y="70" class="title">Project Evidence Map</text>
  <text x="66" y="104" class="subtitle">Four independent project pages with separate methods and results.</text>

  <rect x="88" y="150" width="270" height="270" rx="24" class="card" fill="#E7F1F1" stroke="#5FA9A5"/>
  <text x="118" y="190" class="k">PROJECT 01</text>
  <text x="118" y="228" class="h">Microscopy CV</text>
  <text x="118" y="264" class="t">SEM segmentation</text>
  <text x="118" y="292" class="t">active learning</text>
  <text x="118" y="320" class="t">prediction panels</text>
  <text x="118" y="376" class="m">IoU 0.1174</text>

  <rect x="394" y="150" width="270" height="270" rx="24" class="card" fill="#EDF0FA" stroke="#859DE5"/>
  <text x="424" y="190" class="k">PROJECT 02</text>
  <text x="424" y="228" class="h">Signal ML</text>
  <text x="424" y="264" class="t">20 kHz windows</text>
  <text x="424" y="292" class="t">spectral features</text>
  <text x="424" y="320" class="t">process metrics</text>
  <text x="424" y="376" class="m">R2 0.9998</text>

  <rect x="700" y="150" width="270" height="270" rx="24" class="card" fill="#FFF4D8" stroke="#D3AA46"/>
  <text x="730" y="190" class="k">PROJECT 03</text>
  <text x="730" y="228" class="h">Tool Wear</text>
  <text x="730" y="264" class="t">real datasets</text>
  <text x="730" y="292" class="t">grouped splits</text>
  <text x="730" y="320" class="t">wear prediction</text>
  <text x="730" y="376" class="m">R2 0.8680</text>

  <rect x="1006" y="150" width="270" height="270" rx="24" class="card" fill="#EAF6E7" stroke="#7EBD6E"/>
  <text x="1036" y="190" class="k">PROJECT 04</text>
  <text x="1036" y="228" class="h">Property ML</text>
  <text x="1036" y="264" class="t">tabular features</text>
  <text x="1036" y="292" class="t">feature ranking</text>
  <text x="1036" y="320" class="t">strength model</text>
  <text x="1036" y="376" class="m">R2 0.8990</text>
</svg>"""


def main() -> None:
    write_svg(ASSETS / "system_architecture.svg", system_architecture_svg())
    write_svg(ASSETS / "active_learning_loop.svg", active_learning_svg())
    write_svg(ASSETS / "project_evidence_map.svg", project_evidence_svg())
    print("wrote project visuals to assets/")


if __name__ == "__main__":
    main()
