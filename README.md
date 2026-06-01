# Network Sketcher Cisco Extension — bridge Cisco platforms to automatic network diagrams

**Network Sketcher Cisco Extension** is a growing collection of tools that turn
Cisco platform exports into
[Network Sketcher](https://github.com/cisco-open/network-sketcher) CLI commands,
so you can rebuild an accurate L1/L2/L3 topology — devices, links, VLANs, SVIs,
sub-interfaces, IP addressing and VRFs — in seconds instead of drawing it by
hand.

Each tool in this extension targets a different Cisco data source and can be
used independently. The first available tool, **`cml_converter`**, converts a
[Cisco Modeling Labs (CML)](https://developer.cisco.com/modeling-labs/) lab YAML
file (plus any running-configs embedded in it) into a ready-to-run Network
Sketcher command script — entirely from local files, with **no CML server or API
access required**.

- **Technology stack:** Python 3.10+ (standalone CLIs). Uses `PyYAML` and,
  where useful, `ciscoconfparse2` for robust running-config parsing.
- **Status:** Actively developed. `cml_converter` is at 1.0 — validated
  end-to-end against the live Network Sketcher engine and a corpus of 60+ public
  CML community labs. More tools are planned (see the table below).

---

## Tools in this extension

The extension is a monorepo: each tool lives in its own sub-directory with its
own `README.md` and `requirements.txt`, and is documented as a self-contained
section in this file. New tools are added here in parallel as they become
available.

| # | Tool | What it does | Input | Status |
|---|------|--------------|-------|--------|
| 1 | [`cml_converter`](./cml_converter/) | Convert a CML topology YAML (+ embedded running-configs) into Network Sketcher commands | CML lab YAML (local file) | ✅ Available |
| — | _More tools_ | Additional Cisco data sources → Network Sketcher (e.g. other exports / live sources) | — | 🚧 Planned |

> Jump to a tool's section below for its installation and usage instructions.
> Every tool produces Network Sketcher CLI commands, so the
> ["Run the commands in Network Sketcher"](#running-the-output-in-network-sketcher)
> guidance at the end applies to all of them.

---

## Tool 1 — `cml_converter`

Convert a Cisco Modeling Labs lab into Network Sketcher commands. It works
entirely on local files (no CML connectivity at conversion time) and supports
both CML UI exports and CML REST API dumps.

### Use case

Network engineers routinely build labs in Cisco Modeling Labs, but turning those
labs into clear, reviewable design documentation is slow and manual. Network
Sketcher solves the documentation side, yet still needs the topology to be
entered through its CLI.

`cml_converter` closes that gap: it parses the CML lab (topology + per-device
running-configs) and produces the exact Network Sketcher commands needed to
reproduce the design, organised into Network Sketcher's Phase 1–6 ordering:

- **Phase 1** — areas and device placement
- **Phase 2** — Layer 1 physical links (+ port speed/duplex info)
- **Phase 3** — port-channels, sub-interfaces (dot1q), SVIs/loopbacks, L2 segments
- **Phase 4** — IP addresses and VRFs (L3 instances)
- **Phase 6** — device attributes (model, OS, stencil type, routing summary)

(The numbering mirrors Network Sketcher's own command phases; Phase 5 has no
emitted commands in this converter and is intentionally absent.)

Outcome: a faithful, version-controllable network diagram derived directly from
the source of truth (the lab), with hours of manual diagramming eliminated.

> **Why not just use the built-in CML import?**
> The Network Sketcher Offline edition already ships with a CML import feature,
> but that import covers **Layer 1 only** (devices and physical links).
> `cml_converter` is an **extended converter that also reconstructs Layer 2 and
> Layer 3** — VLANs, SVIs, sub-interfaces (dot1q), port-channels, IP addressing
> and VRFs — by parsing the running-configs alongside the topology.

### Installation

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

Install this tool's dependencies:

```bash
pip install -r cml_converter/requirements.txt
```

### Usage

#### Step 1 — Export your lab from CML

In the CML UI: **Lab → Export → Download Lab (YAML)**, and save it as
`my_lab.yaml`. If your lab nodes contain running-configs, they are exported
inside the YAML and the converter will use them automatically.

> No CML connectivity is needed at conversion time — the converter only reads
> the local YAML file.

#### Step 2 — Run the converter

```bash
python -m cml_converter.src.convert \
    --yaml  my_lab.yaml \
    --out   output/ns_commands.txt
```

Optionally supply running-config text files separately (file stem must match
the CML node `label` exactly, e.g. `spine1.txt` ↔ node `spine1`):

```bash
python -m cml_converter.src.convert \
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

Example of the generated `ns_commands.txt` (illustrative, abbreviated):

```text
# Phase: 1 area_location
add area_location "[['WAN_wp_','Campus']]"
# Phase: 1 device_location
add device_location "['Campus',[['core1','core2'],['acc1','acc2']]]"
# Phase: 2 l1_link_bulk
add l1_link_bulk "[['core1','acc1','GigabitEthernet 0/1','GigabitEthernet 0/0'],['core1','core2','GigabitEthernet 0/0','GigabitEthernet 0/0']]"
# Phase: 3 l2_segment_bulk
add l2_segment_bulk "[['acc1','GigabitEthernet 0/0',['Vlan10']]]"
# Phase: 4 ip_address_bulk
add ip_address_bulk "[['core1','Vlan 10',['10.0.10.1/24']]]"
```

#### Step 3 — Run the commands in Network Sketcher

See [Running the output in Network Sketcher](#running-the-output-in-network-sketcher)
below.

### Supported CML YAML formats

- **CML UI export** (`Lab → Export → Download Lab`) — node-local interface ids
  (`i0`, `i1` …) with links referenced via `n1`/`n2` + `i1`/`i2`.
- **CML REST API dump** — global interface UUIDs with links referenced via
  `interface_a`/`interface_b`.
- Single-file combined dumps with a top-level `topology:` key.

Embedded per-node running-configs are read from `configuration_text` (string),
`configuration` (string), or `configuration` (list of `{name, content}`).

### Known issues

- Devices placed in CML without site/area tags fall into a single `default`
  area; multi-site layouts are inferred heuristically from tags and labels.
- Interface names that are not standard Cisco types (e.g. unusual vendor
  pseudo-ports) are mapped on a best-effort basis; verify exotic ports after
  import.
- The converter models what Network Sketcher can represent directly (L1/L2/L3,
  VLANs, sub-interfaces, VRFs). Control-plane detail (BGP/OSPF/EVPN, etc.) is
  preserved only as a per-device routing-summary attribute, not as objects.

---

## Running the output in Network Sketcher

Every tool in this extension emits a plain-text `ns_commands.txt` script: one
Network Sketcher CLI command per line (lines starting with `#` are phase
comments and can be ignored). The commands are already in the correct
Phase 1 → 6 order, so run them top to bottom against a Network Sketcher master
file.

1. Install Network Sketcher by following the instructions in the
   [cisco-open/network-sketcher](https://github.com/cisco-open/network-sketcher)
   repository.
2. Create (or choose) an empty master file, e.g. `[MASTER]my_lab.nsm`. Starting
   from a freshly created empty master keeps Phase 1 device/area placement on a
   clean canvas.
3. Run the non-comment lines of `ns_commands.txt` in order against that master.
4. Export the diagram to get the L1/L2/L3 viewer and device table.

---

## Repository structure (monorepo)

```
network-sketcher-cisco-extension/
├── README.md           ← you are here
├── LICENSE             (Apache 2.0)
├── NOTICE
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
└── cml_converter/      ← Tool 1: CML YAML → NS commands
    ├── README.md
    ├── requirements.txt
    └── src/
# future tools are added here as sibling sub-directories
```

Each tool is self-contained (its own `README.md` and `requirements.txt`) so it
can be installed and used independently of the others.

---

## Getting help

- Open an issue on the
  [GitHub issues](https://github.com/yuhsukeogawa/network-sketcher-cisco-extension/issues)
  page describing the problem, the tool and input format you used, and the
  relevant portion of `parse_report.md` (for `cml_converter`).

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
  network simulation platform used as the data source for `cml_converter`.
- [CiscoDevNet/cml-community](https://github.com/CiscoDevNet/cml-community) —
  public CML labs used to validate the converter.

## License

This project is licensed under the [Apache License 2.0](./LICENSE). See the
[NOTICE](./NOTICE) file for copyright and third-party attributions.
