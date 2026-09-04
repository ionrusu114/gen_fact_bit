# Security Policy

## Data handling

This tool runs entirely offline. It never sends data anywhere.

- Personal and financial data (seller, buyer, IBAN, invoice counter) is stored only in
  `config.json` in your user config directory (`%APPDATA%\factura` on Windows,
  `~/.config/factura` on Linux/macOS). That file is never part of the repository.
- The repository ships only `factura/config.example.json`, which contains placeholder data.
- Generated PDFs are ignored by git (`*.pdf`).

If you fork this project, keep `config.json` and your PDFs out of version control.

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/ionrusu114/gen_fact_bit/security/advisories/new)
rather than opening a public issue. You should receive a response within 7 days.

## Supported versions

Only the latest release on `main` receives fixes.
