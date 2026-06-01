# Contributing

Thank you for considering contributing to the Network Sketcher Cisco Extension
Tools!

## How to Contribute

### Reporting Bugs

Open a [GitHub Issue](https://github.com/yuhsukeogawa/network-sketcher-cisco-extension/issues)
with:

1. A clear title and description
2. Steps to reproduce the issue
3. Expected vs. actual behaviour
4. Your OS, Python version, and dependency versions (`pip list`)

### Suggesting Features

Open an issue with the label `enhancement`.  Describe:

- The use case and motivation
- The Cisco technology involved
- A rough idea of the API / CLI you envision

### Submitting Pull Requests

1. Fork the repository and create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes.  Follow the existing code style (PEP 8, type hints,
   docstrings).

3. Test your changes manually:
   ```bash
   python cml_converter/src/convert.py --yaml cml_converter/examples/sample_topology.yaml --out /tmp/test_out.txt
   ```

4. Commit with a clear message:
   ```bash
   git commit -m "feat: add support for XYZ YAML format"
   ```

5. Push your branch and open a Pull Request against `main`.

### Adding a New Tool

Place the new tool in its own sub-directory (e.g. `ise_converter/`) with:

- `README.md` — purpose, usage, example
- `requirements.txt` — minimal dependencies
- `src/` — Python source

Add a row to the tools table in the root `README.md`.

## Code Style

- Python 3.10+
- Type annotations on all public functions
- `yaml.safe_load()` for YAML parsing (never `yaml.load()`)
- No hardcoded credentials or network calls in tool logic

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](./LICENSE).
