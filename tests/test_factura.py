"""Smoke and unit tests. They run against the shipped placeholder template, never real data."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

import factura


@pytest.fixture
def cfg_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the CLI at an isolated config directory."""
    d = tmp_path / "cfg"
    monkeypatch.setenv("FACTURA_CONFIG_DIR", str(d))
    monkeypatch.setattr(factura, "CONFIG", d / "config.json")
    return d


def test_fmt_money_romanian_format():
    assert factura.fmt_money(12650, "RON") == "12.650,00 RON"
    assert factura.fmt_money(2355.09, "EUR") == "2.355,09 EUR"
    assert factura.fmt_money(0, "RON") == "0,00 RON"


@pytest.mark.parametrize("raw,expected", [("12650", 12650.0), ("12650.50", 12650.5),
                                          ("12650,50", 12650.5), ("12.650,50", 12650.5)])
def test_parse_num(raw, expected):
    assert factura.parse_num(raw) == expected


def test_set_path_overrides_nested_values():
    cfg = {"client": ["A", "B"], "tva_procent": 0, "scop": "X"}
    factura.set_path(cfg, "client.1", "CUI: 1")
    factura.set_path(cfg, "tva_procent", "19")
    factura.set_path(cfg, "scop", "Y")
    assert cfg == {"client": ["A", "CUI: 1"], "tva_procent": 19, "scop": "Y"}


def test_first_run_creates_config_from_template_and_exits(cfg_dir: Path, capsys):
    assert factura.main(["--ron", "1", "--eur", "1"]) == 1
    created = json.loads((cfg_dir / "config.json").read_text(encoding="utf-8"))
    template = json.loads(factura.CONFIG_EXAMPLE.read_text(encoding="utf-8"))
    assert created == template
    assert "Created" in capsys.readouterr().out


def test_generates_pdf_and_increments_number(cfg_dir: Path, tmp_path: Path):
    factura.main(["--ron", "1", "--eur", "1"])  # bootstrap config
    out_dir = tmp_path / "out"
    rc = factura.main(["--ron", "6750", "--eur", "1269.20", "-d", "1 August 2026",
                       "--scop", "TEST SCOPE", "-o", str(out_dir) + os.sep])
    assert rc == 0
    pdfs = list(out_dir.glob("*.pdf"))
    assert len(pdfs) == 1
    assert re.fullmatch(r"Factura_1001_1_august_2026\.pdf", pdfs[0].name)
    assert pdfs[0].stat().st_size > 10_000

    fitz = pytest.importorskip("fitz")
    doc = fitz.open(pdfs[0])
    assert len(doc) == 1
    text = doc[0].get_text()
    assert "Nr. Factură: 1001" in text
    assert "Data emiterii: 1 August 2026" in text
    assert "TEST SCOPE" in text
    assert "Total de plată (RON): 6.750,00 RON" in text
    assert "Total încasat în cont (EUR): 1.269,20 EUR" in text
    fonts = {f[3].split("+")[-1] for f in doc[0].get_fonts()}
    assert {"LiberationSerif", "LiberationSerif-Bold", "LiberationSerif-Italic"} <= fonts

    saved = json.loads((cfg_dir / "config.json").read_text(encoding="utf-8"))
    assert saved["ultimul_numar"] == 1001


def test_no_save_keeps_counter(cfg_dir: Path, tmp_path: Path):
    factura.main(["--ron", "1", "--eur", "1"])
    factura.main(["--ron", "10", "--curs", "5", "-n", "5000", "--no-save", "-o", str(tmp_path / "x.pdf")])
    saved = json.loads((cfg_dir / "config.json").read_text(encoding="utf-8"))
    assert saved["ultimul_numar"] == 1000
    assert (tmp_path / "x.pdf").exists()


def test_missing_amounts_is_an_error(cfg_dir: Path):
    factura.main(["--ron", "1", "--eur", "1"])
    with pytest.raises(SystemExit) as e:
        factura.main(["--ron", "5"])
    assert e.value.code == 2
