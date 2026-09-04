"""
factura - single-page PDF invoice generator that reproduces a fixed layout 1:1.

The layout (font, sizes, absolute coordinates) is hard-coded to match the original
invoice template. Static data (seller, buyer, bank details, notes) lives in a private
config file outside the repository; only the amounts, date, number and service
description change per invoice.

Examples:
    factura --ron 12650 --eur 2355.09
    factura --ron 12650 --curs 5.3714 --scop "WEB PLATFORM DEVELOPMENT" --data "15 Septembrie 2026"
    factura --ron 5750 --eur 1074.39 --numar 1563970 --open
    factura --ron 8000 --eur 1500 --set client.1="CUI: 99999999"
    factura --config      # print the config.json path
    factura --edit        # open config.json in the default editor

The invoice number auto-increments from config.json unless given explicitly.
The default date is today, formatted in Romanian.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

__version__ = "1.1.0"

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
CONFIG_EXAMPLE = HERE / "config.example.json"  # placeholder template shipped with the package


def config_dir() -> Path:
    """Private config location, outside the package: %APPDATA%/factura or ~/.config/factura."""
    if env := os.environ.get("FACTURA_CONFIG_DIR"):
        return Path(env)
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "factura"


CONFIG = config_dir() / "config.json"

# Page geometry (points). Extracted from the original template; do not change.
PAGE_W, PAGE_H = 595.2755737304688, 841.8897705078125  # A4
LEFT, RIGHT = 62.0, 533.2755737304688
COL2 = 300.0
CENTER = (LEFT + RIGHT) / 2
WRAP_W = 205.0  # seller/buyer column width; reproduces the original line breaks
GRAY = (0.733333, 0.733333, 0.733333)

MONTHS_RO = ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie", "Iulie",
             "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"]


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("LS", FONTS / "LiberationSerif-Regular.ttf"))
    pdfmetrics.registerFont(TTFont("LS-B", FONTS / "LiberationSerif-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("LS-I", FONTS / "LiberationSerif-Italic.ttf"))


def fmt_money(v: float, cur: str) -> str:
    """12650.5 -> '12.650,50 RON' (Romanian number format)."""
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {cur}"


def parse_num(s: str) -> float:
    """Accept 12650 / 12650.50 / 12650,50 / 12.650,50."""
    s = s.strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def today_ro() -> str:
    d = date.today()
    return f"{d.day} {MONTHS_RO[d.month - 1]} {d.year}"


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    """Word-wrap that may also break after a hyphen, like reportlab's Paragraph."""
    tokens: list[tuple[str, str]] = []  # (separator_before, piece)
    for w in text.split(" "):
        parts = w.split("-")
        for i, part in enumerate(parts):
            piece = part + ("-" if i < len(parts) - 1 else "")
            tokens.append((" " if i == 0 else "", piece))
    lines, cur = [], ""
    for sep, piece in tokens:
        cand = f"{cur}{sep}{piece}" if cur else piece
        if pdfmetrics.stringWidth(cand, font, size) <= width:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = piece
    if cur:
        lines.append(cur)
    return lines


def set_path(cfg: dict, path: str, value: str) -> None:
    """Apply a dotted override: --set client.1=... / --set scop=... / --set mentiuni.0=..."""
    keys = path.split(".")
    obj = cfg
    for k in keys[:-1]:
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    last = keys[-1]
    if isinstance(obj, list):
        obj[int(last)] = value
    else:
        old = obj.get(last)
        obj[last] = type(old)(value) if isinstance(old, (int, float)) else value


def build(cfg: dict, numar: str, data: str, ron: float, eur: float, out: Path) -> None:
    """Draw the invoice onto a single A4 page at fixed coordinates."""
    c = canvas.Canvas(str(out), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Factura {cfg['serie']} {numar}")

    def T(x, y, s, font="LS", size=10):  # left-aligned
        c.setFont(font, size)
        c.drawString(x, PAGE_H - y, s)

    def TC(y, s, font="LS", size=10):  # centered
        c.setFont(font, size)
        c.drawCentredString(CENTER, PAGE_H - y, s)

    def TR(y, s, font="LS", size=10):  # right-aligned
        c.setFont(font, size)
        c.drawRightString(RIGHT, PAGE_H - y, s)

    # Header
    TC(110, cfg["titlu"], "LS-B", 15)
    TC(152, f"Seria: {cfg['serie']}   Nr. Factură: {numar}")
    TC(168, f"Data emiterii: {data}")

    c.setStrokeColorRGB(*GRAY)
    c.setLineWidth(0.7)
    c.line(LEFT, PAGE_H - 190, RIGHT, PAGE_H - 190)

    # Seller / Buyer columns
    T(LEFT, 210, "FURNIZOR (Seller)")
    T(COL2, 210, "CLIENT (Buyer)")
    for x, items in ((LEFT, cfg["furnizor"]), (COL2, cfg["client"])):
        y = 226
        for item in items:
            for line in wrap(item, "LS", 10, WRAP_W):
                T(x, y, line)
                y += 16

    # Services
    T(LEFT, 348, "DESCRIEREA SERVICIILOR", "LS-B")
    T(LEFT, 366, cfg["scop"])
    T(LEFT, 381, cfg["serviciu"], "LS-I")
    T(LEFT, 401, f"U.M.: {cfg['um']}  |  Cantitate: {cfg['cantitate']}  |  "
                 f"Preț unitar: {fmt_money(ron, 'RON')}  |  Valoare încasată: {fmt_money(eur, 'EUR')}")

    # Totals
    tva = cfg["tva_procent"]
    tva_val = ron * tva / 100
    TR(433, f"Subtotal: {fmt_money(ron, 'RON')}")
    TR(448, f"TVA ({tva}%): {fmt_money(tva_val, 'RON')}")
    TR(463, f"Total de plată (RON): {fmt_money(ron + tva_val, 'RON')}", "LS-B")
    TR(478, f"Total încasat în cont (EUR): {fmt_money(eur, 'EUR')}", "LS-B")

    # Payment details
    T(LEFT, 506, "INFORMAȚII PENTRU PLATĂ", "LS-B")
    y = 524
    for item in cfg["plata"]:
        T(LEFT, y, item)
        y += 16

    # Notes
    y = 650
    for m in cfg["mentiuni"]:
        TC(y, m, "LS-I")
        y += 15
    TC(y + 9, cfg["multumire"], "LS-I")

    c.showPage()
    c.save()


def open_file(path: Path, editor: bool = False) -> None:
    """Open a file with the OS default handler; on POSIX use $EDITOR for text files."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif editor:
        subprocess.run([os.environ.get("EDITOR", "nano"), str(path)], check=False)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.run([opener, str(path)], check=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="factura", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ron", help="amount in RON (e.g. 12650 or 12.650,50)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--eur", help="amount received in EUR")
    g.add_argument("--curs", help="RON/EUR exchange rate; EUR = RON / rate")
    ap.add_argument("--numar", "-n", help="invoice number (default: last number in config + 1)")
    ap.add_argument("--data", "-d", help='issue date, e.g. "21 August 2026" (default: today, in Romanian)')
    ap.add_argument("--scop", "-s", help="service description (upper-case line)")
    ap.add_argument("--serviciu", help="italic line below the service description")
    ap.add_argument("--serie", help="invoice series")
    ap.add_argument("--tva", type=float, help="VAT percent (default from config)")
    ap.add_argument("--set", action="append", default=[], metavar="PATH=VALUE",
                    help="override any config field, e.g. client.1=\"CUI: 123\"")
    ap.add_argument("--out", "-o", help="output file or directory")
    ap.add_argument("--open", action="store_true", help="open the PDF after generating it")
    ap.add_argument("--no-save", action="store_true", help="do not update ultimul_numar in config")
    ap.add_argument("--config", action="store_true", help="print the config.json path and exit")
    ap.add_argument("--edit", action="store_true", help="open config.json in the default editor and exit")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = ap.parse_args(argv)

    if not CONFIG.exists():
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(CONFIG_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Created {CONFIG} from the template.\n"
              "Fill in your real data (seller, buyer, bank details, series, ultimul_numar, out_dir) "
              "and run again.\n"
              "Open it with:  factura --edit")
        if a.edit:
            open_file(CONFIG, editor=True)
        return 1
    if a.config:
        print(CONFIG)
        return 0
    if a.edit:
        open_file(CONFIG, editor=True)
        return 0
    if not a.ron or not (a.eur or a.curs):
        ap.error("--ron and one of --eur / --curs are required")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if a.scop:
        cfg["scop"] = a.scop
    if a.serviciu:
        cfg["serviciu"] = a.serviciu
    if a.serie:
        cfg["serie"] = a.serie
    if a.tva is not None:
        cfg["tva_procent"] = int(a.tva) if a.tva == int(a.tva) else a.tva
    for kv in a.set:
        k, _, v = kv.partition("=")
        set_path(cfg, k, v)

    ron = parse_num(a.ron)
    eur = parse_num(a.eur) if a.eur else round(ron / parse_num(a.curs), 2)
    numar = a.numar or str(int(cfg["ultimul_numar"]) + 1)
    data = a.data or today_ro()

    # File name: <prefix>_<number>_<day>_<month>_<year>.pdf
    parts = data.split()
    prefix = cfg.get("prefix_fisier", "Factura")
    stem = f"{prefix}_{numar}"
    if len(parts) == 3:
        stem += f"_{parts[0]}_{parts[1].lower()}_{parts[2]}"
    out = Path(a.out) if a.out else Path(cfg.get("out_dir") or Path.cwd())
    if out.is_dir() or (a.out and a.out.endswith(("/", "\\"))) or not out.suffix:
        out.mkdir(parents=True, exist_ok=True)
        out = out / f"{stem}.pdf"

    register_fonts()
    build(cfg, numar, data, ron, eur, out)

    # Persist the highest invoice number so the next run auto-increments.
    if not a.no_save and numar.isdigit():
        cfg0 = json.loads(CONFIG.read_text(encoding="utf-8"))
        cfg0["ultimul_numar"] = max(int(cfg0["ultimul_numar"]), int(numar))
        CONFIG.write_text(json.dumps(cfg0, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK  {out}\n    No {cfg['serie']} {numar} | {data} | {fmt_money(ron, 'RON')} | "
          f"{fmt_money(eur, 'EUR')} | {cfg['scop']}")
    if a.open:
        open_file(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
