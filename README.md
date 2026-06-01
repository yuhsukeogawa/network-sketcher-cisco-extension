# Network Sketcher Cisco Extension — auto-generate network diagrams from Cisco Modeling Labs

Turn a [Cisco Modeling Labs (CML)](https://developer.cisco.com/modeling-labs/)
lab into a documented network diagram automatically. This repository provides
tools that read Cisco platform exports and emit
[Network Sketcher](https://github.com/cisco-open/network-sketcher) CLI commands,
so you can rebuild an accurate L1/L2/L3 topology — devices, links, VLANs, SVIs,
sub-interfaces, IP addressing and VRFs — in seconds instead of drawing it by hand.

The first tool, **`cml_converter`**, converts a CML lab YAML file (plus any
running-configs embedded in it) into a ready-to-run Network Sketcher command
script. It works entirely on local files — **no CML server or API access is
required** — and supports both CML UI exports and CML REST API dumps.

- **Technology stack:** Python 3.10+ (standalone CLI). Uses `PyYAML` and,
  optionally, `ciscoconfparse2` for robust running-config parsing.
- **Status:** 1.0 — validated end-to-end against the live Network Sketcher
  engine and a corpus of 60+ public CML community labs.

---

## Use Case

Network engineers routinely build labs in Cisco Modeling Labs, but turning
those labs into clear, reviewable design documentation is slow and manual.
Network Sketcher solves the documentation side, yet still needs the topology to
be entered through its CLI.

This extension closes that gap: it parses the CML lab (topology + per-device
running-configs) and produces the exact Network Sketcher commands needed to
reproduce the design, organised into Network Sketcher's Phase 1–6 ordering:

- **Phase 1** — areas and device placement
- **Phase 2** — Layer 1 physical links (+ port speed/duplex info)
- **Phase 3** — port-channels, sub-interfaces (dot1q), SVIs/loopbacks, L2 segments
- **Phase 4** — IP addresses and VRFs
- **Phase 6** — device attributes (model, OS, stencil type, routing summary)

Outcome: a faithful, version-controllable network diagram derived directly from
the source of truth (the lab), with hours of manual diagramming eliminated.

---

## Installation

Clone the repo:

```bash
git clone https://github.com/yuhsukeogawa/network-sketcher-cisco-extension.git
cd network-sketcher-cisco-extension
```

Create and activate a Python virtual environment (Python 3.10+ required):

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r cml_converter/requirements.txt
```

---

## Usage

### Step 1 — Export your lab from CML

In the CML UI: **Lab → Export → Download Lab (YAML)**, and save it as
`my_lab.yaml`. If your lab nodes contain running-configs, they are exported
inside the YAML and the converter will use them automatically.

> No CML connectivity is needed at conversion time — the converter only reads
> the local YAML file.

### Step 2 — Run the converter

```bash
python cml_converter/src/convert.py \
    --yaml  my_lab.yaml \
    --out   output/ns_commands.txt
```

Optionally supply running-config text files separately (file stem must match
the CML node `label` exactly, e.g. `spine1.txt` ↔ node `spine1`):

```bash
python cml_converter/src/convert.py \
    --yaml    my_lab.yaml \
    --configs running_configs/ \
    --out     output/ns_commands.txt
```

This writes the following into the `output/` directory:

| File | Description |
|------|-------------|
| `ns_commands.txt` | Network Sketcher CLI commands (Phase 1–6) — **the main deliverable** |
| `ns_model.json` | Intermediate topology model (for debugging) |
| `stencil_mapping.csv` | Device → stencil-type mapping with confidence scores |
| `parse_report.md` | Per-device running-config coverage statistics |

### Step 3 — Run the commands in Network Sketcher

`ns_commands.txt` is a plain-text script: one Network Sketcher CLI command per
line (lines starting with `#` are phase comments and can be ignored). The
commands are already in the correct Phase 1→6 order, so run them top to bottom
against a Network Sketcher master file.

First, install Network Sketcher by following the instructions in the
[cisco-open/network-sketcher](https://github.com/cisco-open/network-sketcher)
repository.

**Option A — Network Sketcher MCP server (recommended)**

If you use the Network Sketcher MCP server, execute the script against a master:

1. Create (or choose) an empty master, e.g. `[MASTER]my_lab.nsm`.
2. Feed the non-comment lines of `ns_commands.txt` to the `run_commands` tool
   (it accepts newline-separated commands and runs each in order).
3. Export the diagram (`build_default_outputs`) to get the L1/L2/L3 HTML viewer
   and device table.

**Option B — Network Sketcher CLI**

Run each command line against your master file (the engine appends the
`--master` argument; consult the Network Sketcher docs for the exact invocation
on your install). Because the commands are pre-ordered by phase, simply piping
the file's command lines in sequence reproduces the full topology, after which
you can export the diagram from Network Sketcher.

> Tip: start from a freshly created empty master so device/area placement in
> Phase 1 lands on a clean canvas.

---

## Supported CML YAML formats

- **CML UI export** (`Lab → Export → Download Lab`) — node-local interface ids
  (`i0`, `i1` …) with links referenced via `n1`/`n2` + `i1`/`i2`.
- **CML REST API dump** — global interface UUIDs with links referenced via
  `interface_a`/`interface_b`.
- Single-file combined dumps with a top-level `topology:` key.

Embedded per-node running-configs are read from `configuration_text` (string),
`configuration` (string), or `configuration` (list of `{name, content}`).

---

## Repository structure (monorepo)

```
network-sketcher-cisco-extension/
├── README.md           ← you are here
├── LICENSE             (Apache 2.0)
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
└── cml_converter/      ← tool 1: CML YAML → NS commands
    ├── README.md
    ├── requirements.txt
    ├── examples/
    └── src/
```

Each tool lives in its own sub-directory with its own `README.md` and
`requirements.txt` so it can be used independently. More tools are planned.

| Tool | Description | Input | Status |
|------|-------------|-------|--------|
| [cml_converter](./cml_converter/) | Convert CML topology YAML → Network Sketcher commands | CML YAML (local file) | ✅ Available |

See [cml_converter/README.md](./cml_converter/README.md) for full tool details.

---

## Known issues

- Devices placed in CML without site/area tags fall into a single `default`
  area; multi-site layouts are inferred heuristically from tags and labels.
- Interface names that are not standard Cisco types (e.g. unusual vendor
  pseudo-ports) are mapped on a best-effort basis; verify exotic ports after
  import.
- The converter models what Network Sketcher can represent directly (L1/L2/L3,
  VLANs, sub-interfaces, VRFs). Control-plane detail (BGP/OSPF/EVPN, etc.) is
  preserved only as a per-device routing-summary attribute, not as objects.

---

## Getting help

- Open an issue on the
  [GitHub issues](https://github.com/yuhsukeogawa/network-sketcher-cisco-extension/issues)
  page describing the problem, the CML YAML format you used, and the relevant
  portion of `parse_report.md`.

## Getting involved

Contributions are welcome — new source converters, broader config coverage, and
additional Network Sketcher command support are all great areas to help with.
See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to set up a dev environment and
submit changes. Please also review [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
and [SECURITY.md](./SECURITY.md).

## Credits and references

- [Network Sketcher](https://github.com/cisco-open/network-sketcher) — the
  open-source Cisco network documentation tool these extensions target.
- [Cisco Modeling Labs](https://developer.cisco.com/modeling-labs/) — the
  network simulation platform used as the data source.
- [CiscoDevNet/cml-community](https://github.com/CiscoDevNet/cml-community) —
  public CML labs used to validate the converter.

## License

This project is licensed under the [Apache License 2.0](./LICENSE).
