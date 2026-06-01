# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest `main` | ✅ |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a security issue, please use the GitHub Security Advisory
["Report a Vulnerability"](https://github.com/yuhsukeogawa/network-sketcher-cisco-extension/security/advisories/new)
feature.

You can also email the maintainer directly at the address listed in the GitHub
profile.  Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce the issue
- Any suggested fix or mitigation

We will acknowledge your report within 5 business days and aim to release a
fix within 30 days of validation.

## Security Considerations

This tool processes locally-sourced YAML files and running-config text files.
It does **not**:

- Connect to any external network services
- Store or transmit credentials
- Execute arbitrary code from the YAML input

YAML is loaded with `yaml.safe_load()` to prevent arbitrary code execution via
YAML deserialization attacks.
