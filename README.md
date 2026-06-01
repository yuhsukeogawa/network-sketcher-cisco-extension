# Network Sketcher — Cisco Extension Tools

A collection of tools that generate
[Network Sketcher](https://github.com/cisco-open/network-sketcher) commands
from various Cisco data sources.

Network Sketcher is an open-source Cisco tool for designing and documenting
network topologies.  These extensions let you **auto-generate** a Network
Sketcher master file from real Cisco platform exports — saving hours of manual
diagram work.

---

## Tools

| Tool | Description | Input | Status |
|------|-------------|-------|--------|
| [cml_converter](./cml_converter/) | Convert Cisco Modeling Labs topology YAML → NS commands | CML YAML (local file) | ✅ Available |

> More tools are planned.  Contributions are welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## Quick Start

### cml_converter

```bash
# Install dependencies
pip install -r cml_converter/requirements.txt

# Run converter
python cml_converter/src/convert.py \
    --yaml  my_lab.yaml \
    --out   output/ns_commands.txt
```

See [cml_converter/README.md](./cml_converter/README.md) for full usage.

---

## Repository Structure (monorepo)

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
    └── src/
```

Each tool lives in its own sub-directory and has its own `README.md` and
`requirements.txt` so it can be used independently.

---

## Cisco Technologies

- [Cisco Modeling Labs (CML)](https://developer.cisco.com/modeling-labs/) —
  network simulation platform
- [Network Sketcher](https://github.com/cisco-open/network-sketcher) —
  open-source AI-native network documentation tool

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Security

See [SECURITY.md](./SECURITY.md) for how to report vulnerabilities.

## License

[Apache License 2.0](./LICENSE)
