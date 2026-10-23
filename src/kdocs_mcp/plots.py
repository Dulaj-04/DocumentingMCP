"""Engineering plots from data, spreadsheet columns or formulas, styled to sit in the master document."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .ingest import column_data  # noqa: E402

SERIF = ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"]
PALETTE = ["#2C3E7A", "#C0392B", "#1E8449", "#D68910", "#7D3C98", "#117A65", "#5D6D7E"]
DPI = 220


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": SERIF,
            "mathtext.fontset": "stix",
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10.5,
            "axes.edgecolor": "#222222",
            "axes.linewidth": 0.8,
            "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
            "grid.color": "#BFBFBF",
            "grid.linewidth": 0.6,
            "grid.alpha": 0.8,
            "legend.frameon": True,
            "legend.framealpha": 0.95,
            "legend.edgecolor": "#BFBFBF",
            "legend.fontsize": 9,
            "lines.linewidth": 1.6,
            "savefig.dpi": DPI,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.06,
        }
    )


# --------------------------------------------------------------------------- safe formula evaluation

_FUNCS = {
    name: getattr(np, name)
    for name in (
        "sin cos tan arcsin arccos arctan arctan2 sinh cosh tanh exp log log10 log2 sqrt abs "
        "floor ceil sign maximum minimum where clip heaviside real imag angle"
    ).split()
}
_FUNCS.update({"ln": np.log, "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan, "atan2": np.arctan2, "mag": np.abs})
_CONSTS = {"pi": math.pi, "e": math.e, "j": 1j}
_ALLOWED = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load, ast.Constant, ast.Compare,
    ast.IfExp, ast.BoolOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq, ast.And, ast.Or, ast.Tuple,
)


def evaluate(expr: str, variables: dict) -> np.ndarray:
    """Evaluate a numeric formula such as '10*sin(2*pi*50*t)' without executing arbitrary code."""
    expr = expr.replace("^", "**")
    tree = ast.parse(expr, mode="eval")
    names = {**_FUNCS, **_CONSTS, **variables}
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ValueError(f"Not allowed in a formula: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in names:
            raise ValueError(f"Unknown name '{node.id}' in formula '{expr}'")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in _FUNCS):
            raise ValueError(f"Only maths functions can be called in a formula: {ast.unparse(node.func)}")
    return eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, names)  # noqa: S307


# --------------------------------------------------------------------------- plotting


def _series_xy(s: dict, base_dir: Path | None, consts: dict):
    if "file" in s:
        path = Path(s["file"]).expanduser()
        if not path.is_absolute() and base_dir:
            path = base_dir / path
        x = np.array(column_data(path, s["x"], s.get("sheet")))
        y = np.array(column_data(path, s["y"], s.get("sheet")))
        n = min(len(x), len(y))
        return x[:n], y[:n]
    if "expr" in s or "y_expr" in s:
        var = s.get("var", "x")
        lo, hi = s.get("range", [0, 1])
        n = int(s.get("points", 600))
        scale = s.get("spacing", "linear")
        x = np.logspace(math.log10(lo), math.log10(hi), n) if scale == "log" else np.linspace(lo, hi, n)
        with np.errstate(all="ignore"):
            y = evaluate(str(s.get("expr", s.get("y_expr"))), {var: x, **consts})
        y = np.broadcast_to(np.real_if_close(y), x.shape).astype(float)
        return x, y
    if "y" in s:
        y = np.asarray(s["y"], dtype=float)
        x = np.asarray(s["x"], dtype=float) if "x" in s else np.arange(1, len(y) + 1)
        return x, y
    raise ValueError("Each series needs data (x/y), a formula (expr + range) or a file (file + x + y columns).")


def make_plot(spec: dict, out_path: Path, base_dir: Path | None = None) -> Path:
    apply_style()
    kind_default = spec.get("type", "line")
    width = float(spec.get("width", 6.0))
    height = float(spec.get("height", width * 0.58))
    fig, ax = plt.subplots(figsize=(width, height))
    consts = {k: float(v) for k, v in (spec.get("constants") or {}).items()}

    series = spec.get("series") or [spec]
    labelled = False
    for i, s in enumerate(series):
        x, y = _series_xy(s, base_dir, consts)
        kind = s.get("type", kind_default)
        kw = {"label": s.get("label")}
        if s.get("color"):
            kw["color"] = s["color"]
        labelled |= bool(s.get("label"))
        if kind == "scatter":
            ax.scatter(x, y, s=float(s.get("size", 18)), marker=s.get("marker", "o"), zorder=3, **kw)
        elif kind == "bar":
            n = len(series)
            w = float(s.get("bar_width", 0.8)) / n
            offs = (i - (n - 1) / 2) * w
            ax.bar(np.arange(len(y)) + offs if "categories" in spec else x + offs, y, width=w, zorder=3, **kw)
        elif kind == "step":
            ax.step(x, y, where=s.get("where", "post"), linestyle=s.get("style", "-"), **kw)
        elif kind == "stem":
            markerline, stemlines, baseline = ax.stem(x, y, label=kw.get("label"))
            plt.setp(baseline, color="#555555", linewidth=0.8)
        else:
            ax.plot(x, y, linestyle=s.get("style", "-"), marker=s.get("marker") or None, markersize=float(s.get("marker_size", 4)), **kw)

    ax.set_xscale(spec.get("xscale", "linear"))
    ax.set_yscale(spec.get("yscale", "linear"))
    if "categories" in spec:  # after set_*scale, which resets tick labels
        ax.set_xticks(range(len(spec["categories"])), spec["categories"])
    if spec.get("x_label"):
        ax.set_xlabel(spec["x_label"])
    if spec.get("y_label"):
        ax.set_ylabel(spec["y_label"])
    if spec.get("title"):
        ax.set_title(spec["title"])
    if spec.get("xlim"):
        ax.set_xlim(*spec["xlim"])
    if spec.get("ylim"):
        ax.set_ylim(*spec["ylim"])
    for h in spec.get("hlines", []) or []:
        ax.axhline(h["y"], color=h.get("color", "#555555"), linestyle=h.get("style", "--"), linewidth=1, label=h.get("label"))
        labelled |= bool(h.get("label"))
    for v in spec.get("vlines", []) or []:
        ax.axvline(v["x"], color=v.get("color", "#555555"), linestyle=v.get("style", "--"), linewidth=1, label=v.get("label"))
        labelled |= bool(v.get("label"))
    for a in spec.get("annotations", []) or []:
        ax.annotate(
            a["text"], xy=(a["x"], a["y"]), xytext=(a.get("dx", 20), a.get("dy", 15)), textcoords="offset points",
            fontsize=9, arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 0.8},
            bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#BFBFBF", "lw": 0.6},
        )
    if spec.get("grid", True):
        ax.grid(True, which="major")
        if spec.get("xscale") == "log" or spec.get("yscale") == "log":
            ax.grid(True, which="minor", alpha=0.35)
        ax.set_axisbelow(True)
    if labelled and spec.get("legend", True):
        ax.legend(loc=spec.get("legend_loc", "best"))
    ax.spines[["top", "right"]].set_visible(bool(spec.get("box", False)))
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
