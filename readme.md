# LSS4PY

**LSS4PY** is a Python-native toolbelt for modern Lean Six Sigma practice in service and knowledge-work environments.

It encodes Lean flow thinking, measurement discipline, statistical process control, and structured improvement artifacts into a reproducible, programmable library.

LSS4PY is not a dashboard.  
It is not slideware.  
It is Lean Six Sigma expressed in code.

---

# Why LSS4PY Exists

Traditional Six Sigma literature evolved in manufacturing contexts:

- Stable measurement systems  
- Normally distributed tolerances  
- Physical defect definitions  

Modern service systems operate differently:

- Variation is often temporal  
- Defects are definitional  
- Queueing effects dominate performance  
- Rare but extreme outcomes drive customer pain  

LSS4PY is built to make these realities visible, measurable, and reproducible.

It treats Lean Six Sigma as a computational discipline grounded in:

- Explicit assumptions  
- Structured outputs  
- Reproducible analysis  
- Service-first realism  

---

# Design Philosophy

## 1. Domain-First API

Functions reflect Lean Six Sigma vocabulary directly:

```python
from lss4py import lss

lss.process.ProcessMap(...)
lss.gage_rr_crossed(...)
lss.imr(...)
lss.capability_normal(...)
```

Users think in process terms, not statistical plumbing.

---

## 2. Tidy Data In, Structured Results Out

All tools:

- Accept tidy pandas DataFrames  
- Return structured result objects  
- Produce deterministic output tables  
- Generate consistent visualizations  

This enables:

- Autograding  
- CI validation  
- Auditability  
- Reproducibility  

---

## 3. Measurement Before Mathematics

Capability claims without validated measurement are discouraged by design.

Measurement System Analysis (MSA) is foundational.

---

## 4. Tail-Aware, Not Average-Blind

Percentiles and tail behavior are treated as first-class signals:

- p50 / p90 / p95 / p99  
- Percentile-based capability (roadmap)  
- Service risk interpretation  

Averages alone do not define performance.

---

# Core Capabilities (v0.1 Target)

## Lean Process Modeling

- Define process steps and flows  
- Attach cycle time and WIP  
- Tag waste and value-add  
- Compute Little’s Law metrics  
- Render SVG process maps  

## Seven Basic Quality Tools

- Histogram  
- Pareto  
- Scatter  
- Stratification  
- Check sheets  
- Fishbone diagrams  
- Process maps  

## Statistical Process Control

- IMR charts  
- p and u charts  
- Signal detection  
- Structured chart outputs  

## Capability Analysis

- Cp / Cpk  
- Pp / Ppk  
- Within vs overall variation  

## Measurement System Analysis

- Crossed Gage R&R  
- %GRR  
- ndc  
- Variance components  

## Structured Deliverables

- A3  
- PDCA  
- DMAIC  
- TOML-front-matter validation  
- Quarto rendering integration  

---

# Scope and Boundaries

LSS4PY occupies a specific space in the process-improvement ecosystem.

## Not Process Mining

Libraries such as `pm4py` discover process models from event logs.

LSS4PY assumes the process is defined and focuses on measurement, stability, and improvement.

Process mining answers:

> “What process occurred?”

LSS4PY answers:

> “Given a defined process, how do we validate, improve, and control it?”

Process mining can feed LSS4PY.  
LSS4PY does not replace process mining.

---

## Not a Visualization Framework

LSS4PY builds on matplotlib, seaborn, and graphviz.

It does not replace general-purpose visualization libraries.  
It provides Lean-aware, opinionated visual outputs—not arbitrary plotting APIs.

---

## Not a BPMN or Workflow Engine

LSS4PY provides lightweight Lean process modeling for improvement analysis.

It does not:

- Execute workflows  
- Orchestrate tasks  
- Replace enterprise BPM systems  

---

## Not a Statistical Modeling Library

LSS4PY integrates with numpy, scipy, and statsmodels.

It does not reimplement foundational statistical methods.

---

## Relationship to R’s SixSigma Package

R’s `SixSigma` package implements classical DMAIC statistical tools.

LSS4PY shares that foundation but extends it with:

- Python-native ecosystem integration  
- Tidy DataFrame-first design  
- Lean process modeling  
- Structured deliverable validation  
- Tail-risk-aware service analysis  
- Reproducibility and CI integration  

LSS4PY aims to be a structured improvement framework, not just a statistical toolkit.

---

# Architecture

LSS4PY is a thin integration layer over the scientific Python ecosystem:

- pandas  
- numpy  
- scipy  
- statsmodels  
- graphviz  

It adds Lean semantics and structured outputs without hiding underlying assumptions.

---

# Example (Conceptual)

```python
from lss4py.process import ProcessMap

p = ProcessMap("Client Onboarding")

p.add_step("Request Received", cycle_time=2)
p.add_step("Document Review", cycle_time=6)
p.add_step("Approval", cycle_time=4)

p.connect("Request Received", "Document Review")
p.connect("Document Review", "Approval")

p.calculate_metrics()
p.render("process_map.svg")
```

---

# Installation

## Requirements

- Python 3.14+
- uv
Note: development tooling expects `roadmap-cli` >= 1.0.2 (see dev dependencies).

## Quick Start

Rebuild a clean virtual environment (recommended):

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip build
pip install -e '.[dev]'
```

If you cannot use `python3.14` locally, install the updated dev tool directly into your active environment:

```bash
pip install 'roadmap-cli>=1.0.2'
```

To verify installation:

```bash
PYTHONPATH=src python -c "import lss4py; print('lss4py ready')"
```

---

# Roadmap

## v0.1
- Process modeling  
- Seven tools  
- IMR / p / u charts  
- Capability (normal)  
- Crossed Gage R&R  
- Deliverable schema validation  

## v0.2
- Non-normal capability  
- Advanced SPC rules  
- Parallel-path process modeling  

## v0.3+
- Rare event monitoring  
- DOE helpers  
- Process mining hooks  

---

# Relationship to the Book

LSS4PY is the computational companion to:

**Process Improvement with Python and lss4py**

The book defines the mastery hierarchy (White → Yellow → Green → Black → MBB).  
LSS4PY provides the programmable toolbelt for Green Belt and above.

---

# Project Status

Active early-stage development.

API surface and modules will evolve before v1.0.  
Breaking changes are expected pre-1.0.

---

# Contributing

Contributions are welcome.

Please open an issue describing:

- The process-improvement use case  
- The expected analytical behavior  
- Relevant assumptions and constraints  

Proposals grounded in Lean and service-system realism are strongly preferred.

---

# License

MIT. See `LICENSE.md`.
