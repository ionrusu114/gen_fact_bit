# factura

[![CI](https://github.com/ionrusu114/gen_fact_bit/actions/workflows/ci.yml/badge.svg)](https://github.com/ionrusu114/gen_fact_bit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)

A tiny command-line tool that generates a single-page PDF invoice in under a second.
The layout, font (Liberation Serif) and every coordinate are fixed to reproduce an
existing invoice template 1:1, so each new invoice looks exactly like the last one.
Only the amounts, date, number and service description change.

All data stays on your machine. The tool never touches the network.

## Install

Requires [uv](https://docs.astral.sh/uv/) (or `pipx`). One command, from anywhere:

```sh
uv tool install git+https://github.com/ionrusu114/gen_fact_bit
```

From a local checkout: `uv tool install .` (add `-e` for an editable install so code
changes apply immediately). Update with `uv tool upgrade factura`, remove with
`uv tool uninstall factura`.

## First run

```sh
factura --ron 1 --eur 1   # creates config.json from the placeholder template and stops
factura --edit            # open config.json and fill in seller, buyer, bank details, series, counter, output dir
factura --config          # print the config.json path
```

The config lives outside the repository, in `%APPDATA%\factura\config.json` on Windows
or `~/.config/factura/config.json` on Linux/macOS. Override the location with the
`FACTURA_CONFIG_DIR` environment variable.

## Usage

```sh
factura --ron 12650 --eur 2355.09                            # number = last + 1, date = today
factura --ron 12650 --curs 5.3714 --scop "WEB PLATFORM DEVELOPMENT"
factura --ron 5750 --eur 1074.39 -n 1563970 -d "15 Septembrie 2026" --open
factura --ron 8000 --eur 1500 --set client.1="CUI: 999" --set tva_procent=19
factura --ron 8000 --eur 1500 -o D:\invoices\
factura --help
```

| Flag | Meaning |
|---|---|
| `--ron` | amount in RON (`12650`, `12650.50` or `12.650,50`) |
| `--eur` / `--curs` | amount received in EUR, or the RON/EUR rate to derive it |
| `-n`, `--numar` | invoice number (default: last number in config + 1) |
| `-d`, `--data` | issue date as free text, e.g. `"1 August 2026"` (default: today, in Romanian) |
| `-s`, `--scop` | service description line |
| `--serviciu` | italic line below the description |
| `--serie` | invoice series |
| `--tva` | VAT percent |
| `--set PATH=VALUE` | override any config field for this run, e.g. `client.1="CUI: 999"` |
| `-o`, `--out` | output file or directory |
| `--open` | open the PDF after generating it |
| `--no-save` | do not persist the invoice counter |
| `--config` / `--edit` | print / open the config file |

Output file: `<out_dir>/<prefix_fisier>_<number>_<day>_<month>_<year>.pdf`
(both `out_dir` and `prefix_fisier` come from the config; an empty `out_dir` means the
current directory).

## Configuration

`config.json` holds everything that does not change between invoices: seller, buyer,
payment details, notes, series, VAT, file-name prefix and output directory, plus
`ultimul_numar`, the invoice counter that is bumped automatically after each run.

Field names and the invoice text itself are in Romanian because that is the language
of the document; the CLI, code and docs are in English.

## Development

```sh
uv sync --group dev
uv run ruff check .
uv run pytest
```

Tests run only against the placeholder template. The layout was verified against the
original template by comparing every text span (position, font, size, text) with PyMuPDF.

## Security

See [SECURITY.md](SECURITY.md). In short: private data lives only in your user config
directory, generated PDFs are git-ignored, CI runs a secret scan on every push, and the
repository ships nothing but placeholder data.

## License

MIT. Liberation Serif fonts are bundled under the SIL Open Font License 1.1
(`factura/fonts/LICENSE-fonts.txt`).
