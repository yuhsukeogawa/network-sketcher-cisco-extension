# Network Sketcher Cisco Extension — bridge Cisco platforms to automatic network diagrams

**Network Sketcher Cisco Extension** is a growing collection of tools that turn
Cisco platform exports into
[Network Sketcher](https://github.com/cisco-open/network-sketcher) CLI commands,
so you can rebuild an accurate L1/L2/L3 topology — devices, links, VLANs, SVIs,
sub-interfaces, IP addressing and VRFs — in seconds instead of drawing it by
hand.

Each tool in this extension targets a different Cisco data source and can be
used independently. **`cml_converter`** converts a
[Cisco Modeling Labs (CML)](https://developer.cisco.com/modeling-labs/) lab YAML
file (plus any running-configs embedded in it) into a ready-to-run Network
Sketcher command script — entirely from local files, with **no CML server or API
access required**. **`sna_converter`** turns a
[Cisco Secure Network Analytics (SNA / Stealthwatch)](https://www.cisco.com/site/us/en/products/security/security-analytics/secure-network-analytics/index.html)
NetFlow Flow Search CSV export into Network Sketcher commands **plus** a
`[FLOW]` traffic matrix — also entirely from local files.

- **Technology stack:** Python standalone CLIs. `cml_converter` needs Python
  3.10+ with `PyYAML` (and optionally `ciscoconfparse2`); `sna_converter` runs
  on the Python 3.8+ standard library only (no pip packages).
- **Status:** Actively developed. `cml_converter` is at 1.0 — validated
  end-to-end against the live Network Sketcher engine and a corpus of 60+ public
  CML community labs. `sna_converter` derives a topology and traffic matrix from
  observed NetFlow. More tools are planned (see the table below).

---

## Tools in this extension

The extension is a monorepo: each tool lives in its own sub-directory with its
own `README.md` and `requirements.txt`, and is documented as a self-contained
section in this file. New tools are added here in parallel as they become
available.

| # | Tool | What it does | Input | Status |
|---|------|--------------|-------|--------|
| 1 | [`cml_converter`](./cml_converter/) | Convert a CML topology YAML (+ embedded running-configs) into Network Sketcher commands | CML lab YAML (local file) | ✅ Available |
| 2 | [`sna_converter`](./sna_converter/) | Reconstruct a multi-site L1/L2/L3 topology + endpoints from observed NetFlow, and emit a `[FLOW]` traffic matrix | Cisco SNA Flow Search CSV (local file) | ✅ Available |
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

<img width="1109" height="337" alt="image" src="https://github.com/user-attachments/assets/def702e3-8b6f-44ae-a961-6faeb8a35142" />

<img width="783" height="302" alt="image" src="https://github.com/user-attachments/assets/0211fcd4-42a4-4ad0-9d86-33512530494d" />

<img width="1227" height="588" alt="image" src="https://github.com/user-attachments/assets/43188e91-bb16-4391-ae0d-9c1cafedf5c6" />

[[L1L2L3_DIAGRAM]AllAreas_no_data_1.html](https://github.com/user-attachments/files/28463950/L1L2L3_DIAGRAM.AllAreas_no_data_1.html)

[[DEVICE_TABLE]no_data_1.html](https://github.com/user-attachments/files/28463946/DEVICE_TABLE.no_data_1.html)


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

## Tool 2 — `sna_converter`

Reconstruct a network topology from **observed traffic** instead of a device
inventory. `sna_converter` reads a Cisco Secure Network Analytics (SNA /
Stealthwatch) NetFlow **Flow Search CSV** and produces both a Network Sketcher
command script and a `[FLOW]` traffic matrix — entirely from a local file, with
**no SNA server connection required**.

### Use case

<img width="1425" height="881" alt="image" src="https://github.com/user-attachments/assets/da2ccd66-a6cb-4f86-ae32-c6cfbef6b889" />


CML/config-based tools describe a network you already have defined. In many real
environments the only available source of truth is *flow telemetry* — you know
which hosts talk to which, on which ports and how much, but not the device/link
inventory. `sna_converter` infers a plausible, reviewable topology from that
telemetry:

- **Inside hosts** are identified (RFC1918 plus auto-detected/declared public
  ranges) and aggregated into `/24` segments and `/16` regions.
- **Sites** are formed from the inter-region traffic graph, then split into
  **Datacenter (server-side)** and **client** sites, with isolated **spur**
  sites separated out. A standard per-site device stack is emitted (edge router,
  firewall, core, access switch) with VLANs/SVIs and IP addressing.
- **Endpoints** are placed from SNA flow orientation (`peer = server`):
  inside servers (`SRV_{site}_{ports}_{seq}` — 1 IP = 1 device, named by adopted
  service port list), client segments (`PC_{site}_{n}_{seq}` — 1 segment = 1
  device, where `{n}` is the distinct client IP count observed in that /24), and
  Internet services (`Svc_{proto}{port}_{n}` — aggregated by proto/port, where
  `{n}` is the distinct external server IP count). All Internet service devices
  share a single L2 segment on the `Internet` waypoint (`VlanIntSvc`).
- A **`[FLOW]` traffic matrix** is produced with `Max. bandwidth(Mbps)` derived
  from bytes and session duration, using the master device names.

Outcome: a first-pass, version-controllable topology *and* a traffic sheet built
directly from NetFlow, ready to refine in Network Sketcher.

> **Why not just import device data?**
> There is no device/link inventory in NetFlow. `sna_converter` is the tool for
> when traffic telemetry is all you have: it *derives* the sites, infrastructure
> devices, endpoints and the flow matrix from observed conversations.

### Installation

Clone the repo (same as above) and create a virtual environment if you wish.
`sna_converter` has **no third-party dependencies** — it runs on the Python
3.8+ standard library — so the install step is effectively a no-op:

```bash
pip install -r sna_converter/requirements.txt
```

It runs on **Windows, macOS and Ubuntu/Linux**.

### Usage

#### Step 1 — Export your flows from SNA

In the SNA Manager, run a **Flow Search** for the scope/time range of interest
and export the results to CSV. Both the **API format**
(`searchSubject.* / peer.*` column names) and the **UI export format**
(`Subject IP Address`, `Total Bytes`="56.49 M", `Duration`="36min 38s") are
supported — the format is auto-detected.

#### Step 2 — Run the converter

Run it from the tool's folder so the default `Input_data/` and `Output_data/`
folders resolve correctly:

```bash
cd sna_converter

# Convert every CSV placed in Input_data/  (a sample_flows.csv is included)
python sna_to_ns_commands.py

# …or a single CSV anywhere on disk
python sna_to_ns_commands.py path/to/flowAnalysis.csv

# …or every CSV in a specific folder
python sna_to_ns_commands.py path/to/folder
```

Useful options:

| Option | Default | Meaning |
|--------|---------|---------|
| `input` (positional) | — | A single CSV **file** or a **folder**; if omitted, all CSVs in `--input-dir` are processed |
| `--input-dir` | `Input_data` | Folder scanned for `*.csv` in batch mode |
| `--output-dir` | `Output_data` | Output root; each CSV writes to `<output-dir>/<csv_name>/` |
| `--endpoints` | `both` | `none` / `servers` / `clients` / `both` — which endpoint devices to generate |
| `--config` | `sna_to_ns_config.json` | Path to the settings JSON |
| `--server-min-flows` | `1` | Extra lower bound on flow count for a service to be adopted |
| `--no-flow` | off | Skip generating `gen_flow_list.csv` |

For each input CSV a folder `Output_data/<csv_name>/` is created containing:

| File | Description |
|------|-------------|
| `gen_master_commands.txt` | Network Sketcher CLI commands — **the main deliverable** |
| `gen_flow_list.csv` | `[FLOW]` paste sheet: `Source/Destination Device Name` (master names), `TCP/UDP/ICMP`, `Service name(Port)`, `Max. bandwidth(Mbps)` |
| `out_of_scope_ips.csv` | Candidate server IPs that were **not** adopted, with the reason |
| `_normalized_flow.csv` | Present only for UI-format inputs; the normalized intermediate actually processed |

`Max. bandwidth(Mbps)` is computed as
`total bytes (sent + received) × 8 / session active time (s) / 1,000,000`, taking
the **maximum** across all flows that share the same
`(Source, Destination, protocol, port)`. Sub-1 Mbps values are shown as plain
decimals (e.g. `0.0476`).

Site grouping is controlled by `sna_to_ns_config.json`, where every parameter
carries an inline `description` and `sample` value. Notable settings:

- **auto-detection** of inside public ranges, Datacenter regions and spur sites
  (all overridable by hand; manual settings win),
- **`site_cidrs`** — define sites explicitly by arbitrary CIDR (any prefix
  length), overriding the automatic `/16` grouping,
- **`name_map`** — rename auto-grouped hub sites to friendly names.

#### Step 3 — Run the commands in Network Sketcher

`gen_master_commands.txt` follows the same plain-text format as the other tools;
see [Running the output in Network Sketcher](#running-the-output-in-network-sketcher).
The `gen_flow_list.csv` content can additionally be pasted into the master's
`[Flow_List]` sheet (the routing-path columns are intentionally left blank).
To draw those flows onto the exported PPTX diagram, follow the Network Sketcher
wiki guide
[9‑4. Adding communication flows to the diagram file](https://github.com/cisco-open/network-sketcher/wiki/9%E2%80%904.adding-communication-flows-to-the-diagram-file).

See the [`sna_converter/README.md`](./sna_converter/) for full details.

### Supported SNA CSV formats

The header row is auto-detected:

- **API format** — machine-readable columns (`searchSubject.ipAddress`,
  `peer.ipAddress`, `peer.portProtocol.port`, `connection.transferBytes`,
  `activeDuration`, …).
- **UI export format** — human-readable columns (`Subject IP Address`,
  `Peer Port/Protocol` = `2055/UDP`, `Total Bytes` = `56.49 M`,
  `Duration` = `36min 38s`). These are normalized automatically (byte suffixes
  K/M/G/T, duration `d/h/min/s`, `port/proto` strings).

### Known issues

- The topology is **inferred from traffic**, not a device inventory: sites,
  infrastructure devices and links are a best-effort reconstruction. Review and
  adjust before treating the diagram as authoritative.
- Detection thresholds matter. The defaults suit small-to-medium captures; for
  large captures raise `server_min_bytes` and `subnet_min_flows`, and for lab
  data using benchmark ranges (e.g. `198.18.0.0/15`) declare them via
  `inside_public`. Tune in `sna_to_ns_config.json`.
- Only TCP/UDP services are modeled as endpoints; ICMP/routing protocols
  (e.g. OSPF) are ignored for device/flow generation.
- Server naming concatenates all adopted service ports for an IP, which can
  produce long names when a host exposes many ports.

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
├── cml_converter/      ← Tool 1: CML YAML → NS commands
│   ├── README.md
│   ├── requirements.txt
│   ├── cml_to_ns_config.json    (settings: value / description)
│   └── src/
└── sna_converter/      ← Tool 2: SNA / NetFlow CSV → NS commands + [FLOW] matrix
    ├── README.md
    ├── requirements.txt
    ├── sna_to_ns_commands.py    (entry point)
    ├── sna_to_ns_config.json    (settings: value / description / sample)
    ├── Input_data/              (drop your SNA CSVs here; includes sample_flows.csv)
    └── Output_data/             (results, one subfolder per input CSV)
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
- [Cisco Secure Network Analytics (SNA / Stealthwatch)](https://www.cisco.com/site/us/en/products/security/security-analytics/secure-network-analytics/index.html)
  — the NetFlow analytics platform whose Flow Search export feeds `sna_converter`.
- [CiscoDevNet/cml-community](https://github.com/CiscoDevNet/cml-community) —
  public CML labs used to validate the converter.

## License

This project is licensed under the [Apache License 2.0](./LICENSE). See the
[NOTICE](./NOTICE) file for copyright and third-party attributions.
