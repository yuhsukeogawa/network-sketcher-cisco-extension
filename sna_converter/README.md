# sna_to_nsm — Cisco SNA / NetFlow CSV to Network Sketcher Converter

Convert a [Cisco Secure Network Analytics (SNA / Stealthwatch)](https://www.cisco.com/site/us/en/products/security/security-analytics/secure-network-analytics/index.html)
NetFlow **Flow Search CSV export** into a ready-to-run
[Network Sketcher](https://github.com/cisco-open/network-sketcher) command
script **and** a `[FLOW]` traffic CSV — no SNA server connection required.

> Network Sketcher can draw a topology from device/link data, but it has no
> notion of *who actually talks to whom*. `sna_to_nsm` reconstructs a plausible
> **multi-site Layer 1/2/3 topology** (sites, VLANs/SVIs, firewalls, cores,
> access switches) **and the endpoints** (servers, client segments, Internet
> services) purely from observed NetFlow, then emits the per-flow traffic
> matrix you can paste into a Network Sketcher `[FLOW]` sheet.

---

## Overview

| Item | Detail |
|------|--------|
| **Input** | Cisco SNA Flow Search CSV — **API format** (`searchSubject.* / peer.*`) or **UI export format** (`Subject IP Address`, `Total Bytes`="56.49 M", `Duration`="36min 38s") — auto-detected |
| **Output** | `gen_master_commands.txt` (Network Sketcher CLI), `gen_flow_list.csv` (`[FLOW]` paste sheet), `out_of_scope_ips.csv` (audit) |
| **Dependencies** | Python 3.8+ standard library only — no pip packages |
| **Platforms** | Windows, macOS, Ubuntu/Linux |
| **SNA connectivity** | None — purely local file I/O |

## Quick Start

```bash
# 1. (Optional) install dependencies — there are none, this is a no-op
pip install -r requirements.txt

# 2. Drop one or more SNA Flow CSVs into Input_data/
#    (a ready-made sample_flows.csv is included)

# 3. Convert every CSV in Input_data/  (run from the project folder)
python sna_to_ns_commands.py

# Results appear under Output_data/<csv_name>/
```

### Other ways to run

```bash
# Convert a single CSV (anywhere on disk)
python sna_to_ns_commands.py path/to/flowAnalysis.csv

# Convert every CSV in a specific folder
python sna_to_ns_commands.py path/to/folder

# Use a custom settings file and choose which endpoints to emit
python sna_to_ns_commands.py --config my_config.json --endpoints both

# Custom input/output folders
python sna_to_ns_commands.py --input-dir captures --output-dir results
```

| Option | Default | Meaning |
|--------|---------|---------|
| `input` (positional) | — | A single CSV **file** or a **folder**. If omitted, all CSVs in `--input-dir` are processed |
| `--input-dir` | `Input_data` | Folder scanned for `*.csv` in batch mode |
| `--output-dir` | `Output_data` | Output root; each CSV writes to `<output-dir>/<csv_name>/` |
| `--endpoints` | `both` | `none` / `servers` / `clients` / `both` — which endpoint devices to generate |
| `--config` | `sna_to_ns_config.json` | Path to the settings JSON |
| `--server-min-flows` | `1` | Extra lower bound on flows for a service to be adopted |
| `--no-flow` | off | Skip generating `gen_flow_list.csv` |

## Output files

For each input CSV, a folder `Output_data/<csv_name>/` is created containing:

| File | Description |
|------|-------------|
| `gen_master_commands.txt` | Network Sketcher CLI commands (areas, devices, L1 links, VLANs/SVIs, IPs, attributes) |
| `gen_flow_list.csv` | `[FLOW]` paste sheet: `Source/Destination Device Name` (master names), `TCP/UDP/ICMP`, `Service name(Port)`, `Max. bandwidth(Mbps)` |
| `out_of_scope_ips.csv` | Candidate server IPs that were **not** adopted, with the reason |
| `_normalized_flow.csv` | Present only when the input was UI-format; the normalized intermediate the tool actually processed |

### How `Max. bandwidth(Mbps)` is computed

`Max. bandwidth = total bytes (sent + received) x 8 / session active time (s) / 1,000,000`

For each unique `(Source, Destination, protocol, port)` combination the
**maximum** Mbps across all matching flows is kept. Values below 1 Mbps are
shown as plain decimals (e.g. `0.0476`); zero-duration flows are skipped.

## Running the output in Network Sketcher

`gen_master_commands.txt` is a plain-text script (one command per line). Install
[Network Sketcher](https://github.com/cisco-open/network-sketcher), create an
empty master, and run the command lines in order against it (e.g. via the
`run_commands` interface), then export the diagram. The `gen_flow_list.csv`
content can be pasted into the master's `[Flow_List]` sheet (the `Manually /
Automatic routing path settings` columns are left blank by design).

## Supported SNA CSV formats

The input format is auto-detected from the header row:

- **API format** — machine-readable column names such as
  `searchSubject.ipAddress`, `peer.ipAddress`, `peer.portProtocol.port`,
  `connection.transferBytes`, `activeDuration`.
- **UI export format** — human-readable columns such as `Subject IP Address`,
  `Peer Port/Protocol` (`2055/UDP`), `Total Bytes` (`56.49 M`),
  `Duration` (`36min 38s`). These are normalized automatically (byte
  suffixes K/M/G/T, duration `d/h/min/s`, `port/proto` strings).

## How it works

```
SNA Flow CSV (API or UI format)
   └─► normalize_csv()        detect format, convert UI -> required columns
         └─► inside detection  RFC1918 + auto/declared public ranges
               └─► /24 aggregation (segments) -> /16 regions
                     └─► traffic-graph grouping -> sites (+ DC / spur split)
                           └─► server detection  (SNA orientation: peer = server)
                                 └─► command builder -> gen_master_commands.txt
                                 └─► flow matrix     -> gen_flow_list.csv
```

Site grouping is driven by the settings in `sna_to_ns_config.json`. Highlights:

- **Auto-detection** of inside public ranges, Datacenter regions and isolated
  "spur" sites, all overridable by hand (manual settings win).
- **`site_cidrs`** — define sites explicitly by arbitrary CIDR (any prefix
  length), overriding the automatic `/16` grouping.
- **`name_map`** — rename auto-grouped hub sites to friendly names.

Every parameter in `sna_to_ns_config.json` carries an inline `description` and
`sample` value documenting its meaning and an example setting.

## Directory structure

```
sna_converter/
├── README.md                  (this file)
├── requirements.txt
├── .gitignore
├── sna_to_ns_commands.py      ← entry point
├── sna_to_ns_config.json      ← settings (value / description / sample per key)
├── Input_data/                ← place your SNA CSVs here
│   └── sample_flows.csv        (included example)
└── Output_data/               ← results, one subfolder per input CSV
    └── <csv_name>/
        ├── gen_master_commands.txt
        ├── gen_flow_list.csv
        ├── out_of_scope_ips.csv
        └── _normalized_flow.csv   (UI-format inputs only)
```

## Cisco Technologies

This tool bridges two Cisco technologies:

- **Cisco Secure Network Analytics (SNA / Stealthwatch)** — NetFlow-based
  network visibility and security analytics platform whose Flow Search export
  is the input.
- **Network Sketcher** — open-source Cisco tool for designing and documenting
  network topologies using an AI-native CLI.

## License

Apache License 2.0.
