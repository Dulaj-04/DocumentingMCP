"""Block diagrams / flowcharts (Mermaid flowchart syntax, laid out offline) and circuit / logic diagrams
(schemdraw), rendered as PNG figures in the master document's colours."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402

from .plots import SERIF, apply_style  # noqa: E402

NAVY, FILL, DECISION_FILL, TEXT = "#2C3E7A", "#EDF0F8", "#FFF4E0", "#111111"

# =========================================================================== Mermaid flowcharts


@dataclass
class Node:
    id: str
    label: str
    shape: str = "box"  # box | round | diamond | circle | io
    layer: int = 0
    order: float = 0.0
    w: float = 1.0
    h: float = 0.5
    x: float = 0.0
    y: float = 0.0


@dataclass
class Edge:
    src: str
    dst: str
    label: str = ""
    style: str = "solid"  # solid | dotted | thick | line
    back: bool = False


@dataclass
class Graph:
    direction: str = "LR"
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)


_SHAPES = [  # (opening, closing, shape) - longest first
    ("((", "))", "circle"),
    ("([", "])", "round"),
    ("[[", "]]", "box"),
    ("[/", "/]", "io"),
    ("[\\", "\\]", "io"),
    ("{{", "}}", "diamond"),
    ("[", "]", "box"),
    ("(", ")", "round"),
    ("{", "}", "diamond"),
    (">", "]", "box"),
]
_EDGE = re.compile(
    r"\s*(?:--\s*(?P<l1>[^>|-][^>|]*?)\s*-->|-->\s*\|(?P<l2>[^|]*)\|"
    r"|-\.\s*(?P<l3>[^>|.-][^>|]*?)\s*\.->|-\.->\s*\|(?P<l4>[^|]*)\||==>\s*\|(?P<l5>[^|]*)\||"
    r"(?P<op>-\.->|==>|-->|---))\s*"
)


def _clean(label: str) -> str:
    label = label.strip().strip('"').strip("'")
    return re.sub(r"<br\s*/?>", "\n", label).replace("\\n", "\n")


def _parse_node(token: str, g: Graph) -> str | None:
    token = token.strip().rstrip(";")
    if not token:
        return None
    m = re.match(r"^([A-Za-z0-9_\-]+)\s*(.*)$", token, re.S)
    if not m:
        return None
    nid, rest = m.group(1), m.group(2).strip()
    label, shape = None, None
    for op, cl, sh in _SHAPES:
        if rest.startswith(op) and rest.endswith(cl):
            label, shape = rest[len(op) : len(rest) - len(cl)], sh
            break
    node = g.nodes.get(nid)
    if node is None:
        node = g.nodes[nid] = Node(nid, _clean(label) if label is not None else nid, shape or "box")
    elif label is not None:
        node.label, node.shape = _clean(label), shape
    return nid


def parse_mermaid(text: str) -> Graph:
    g = Graph()
    for raw in re.split(r"[\n;]", text):
        line = raw.split("%%")[0].strip()
        if not line:
            continue
        head = re.match(r"^(flowchart|graph)\s*(LR|RL|TB|TD|BT)?", line, re.I)
        if head:
            g.direction = (head.group(2) or "TB").upper().replace("TD", "TB")
            continue
        if re.match(r"^(subgraph|end$|classDef|class |style |linkStyle|click )", line):
            continue
        pieces, last = [], 0
        ops = []
        for m in _EDGE.finditer(line):
            pieces.append(line[last : m.start()])
            label = next((m.group(k) for k in ("l1", "l2", "l3", "l4", "l5") if m.group(k)), "") or ""
            op = m.group("op") or ("-.->" if (m.group("l3") or m.group("l4")) else "==>" if m.group("l5") else "-->")
            ops.append((label.strip(), op))
            last = m.end()
        pieces.append(line[last:])
        groups = [[_parse_node(t, g) for t in p.split("&")] for p in pieces]
        for i, (label, op) in enumerate(ops):
            style = {"-.->": "dotted", "==>": "thick", "---": "line"}.get(op, "solid")
            for a in groups[i]:
                for b in groups[i + 1]:
                    if a and b:
                        g.edges.append(Edge(a, b, _clean(label) if label else "", style))
    if not g.nodes:
        raise ValueError("No nodes found. Use Mermaid flowchart syntax, e.g. 'flowchart LR\\n A[Input] --> B[Output]'.")
    return g


def _layout(g: Graph, fontsize: float) -> None:
    # Break cycles (feedback paths) with a DFS, marking back edges.
    adj = defaultdict(list)
    for e in g.edges:
        adj[e.src].append(e)
    state: dict[str, int] = {}

    def dfs(u: str) -> None:
        state[u] = 1
        for e in adj[u]:
            if state.get(e.dst) == 1:
                e.back = True
            elif e.dst not in state:
                dfs(e.dst)
        state[u] = 2

    for nid in g.nodes:
        if nid not in state:
            dfs(nid)

    # Longest-path layering over the forward edges.
    fwd = [e for e in g.edges if not e.back and e.src != e.dst]
    changed = True
    for _ in range(len(g.nodes) + 1):
        if not changed:
            break
        changed = False
        for e in fwd:
            if g.nodes[e.dst].layer < g.nodes[e.src].layer + 1:
                g.nodes[e.dst].layer = g.nodes[e.src].layer + 1
                changed = True

    # Pull pure sources (e.g. a reference input) right next to the node they feed.
    has_pred = {e.dst for e in fwd}
    for n in g.nodes.values():
        succ_layers = [g.nodes[e.dst].layer for e in fwd if e.src == n.id]
        if n.id not in has_pred and succ_layers:
            n.layer = max(n.layer, min(succ_layers) - 1)

    layers: dict[int, list[Node]] = defaultdict(list)
    for i, n in enumerate(g.nodes.values()):
        n.order = i
        layers[n.layer].append(n)
    preds, succs = defaultdict(list), defaultdict(list)
    for e in fwd:
        preds[e.dst].append(e.src)
        succs[e.src].append(e.dst)
    for sweep in range(6):  # barycentre ordering to reduce crossings
        rng = sorted(layers) if sweep % 2 == 0 else sorted(layers, reverse=True)
        for li in rng:
            nbrs = preds if sweep % 2 == 0 else succs
            for n in layers[li]:
                ps = [g.nodes[p].order for p in nbrs[n.id]]
                if ps:
                    n.order = sum(ps) / len(ps)
            layers[li].sort(key=lambda n: n.order)
            for k, n in enumerate(layers[li]):
                n.order = k

    # Node sizes from text extent (inches).
    char_w, line_h = fontsize / 72 * 0.52, fontsize / 72 * 1.35
    for n in g.nodes.values():
        lines = n.label.split("\n")
        tw = max(len(s) for s in lines) * char_w
        th = len(lines) * line_h
        n.w, n.h = max(tw + 0.26, 0.75), max(th + 0.2, 0.4)
        if n.shape == "diamond":
            n.w, n.h = n.w * 1.45, n.h * 1.7
        elif n.shape == "circle":
            n.w = n.h = max(n.w, n.h) * 1.05

    horizontal = g.direction in ("LR", "RL")
    gap_main, gap_cross = 0.42, 0.25
    size_of = (lambda n: n.h) if horizontal else (lambda n: n.w)
    cross: dict[str, float] = {}

    def pack(nodes, desired):
        # Keep the order, honour desired centres, push apart to avoid overlap, then re-centre the block.
        placed = []
        for n in nodes:
            c = desired[n.id]
            if placed:
                prev = placed[-1]
                c = max(c, cross[prev.id] + size_of(prev) / 2 + gap_cross + size_of(n) / 2)
            cross[n.id] = c
            placed.append(n)
        shift = (sum(desired[n.id] for n in nodes) - sum(cross[n.id] for n in nodes)) / len(nodes)
        for n in nodes:
            cross[n.id] += shift

    for li in sorted(layers):  # initial: evenly centred
        nodes = layers[li]
        total = sum(size_of(n) for n in nodes) + gap_cross * (len(nodes) - 1)
        c, desired = -total / 2, {}
        for n in nodes:
            desired[n.id] = c + size_of(n) / 2
            c += size_of(n) + gap_cross
        pack(nodes, desired)
    for sweep in range(4):  # align nodes with their neighbours so chains run straight
        order = sorted(layers) if sweep % 2 == 0 else sorted(layers, reverse=True)
        nbrs = preds if sweep % 2 == 0 else succs
        for li in order:
            nodes = layers[li]
            desired = {n.id: (sum(cross[m] for m in nbrs[n.id]) / len(nbrs[n.id]) if nbrs[n.id] else cross[n.id]) for n in nodes}
            pack(nodes, desired)

    pos = 0.0
    for li in sorted(layers):
        nodes = layers[li]
        thick = max((n.w if horizontal else n.h) for n in nodes)
        for n in nodes:
            main = pos + thick / 2
            n.x, n.y = (main, -cross[n.id]) if horizontal else (cross[n.id], -main)
        pos += thick + gap_main + (0.25 if any(e.label for e in fwd if g.nodes[e.dst] in nodes) else 0)
    if g.direction in ("RL", "BT"):
        for n in g.nodes.values():
            if horizontal:
                n.x = -n.x
            else:
                n.y = -n.y


def render_flowchart(text: str, out_path: Path, fontsize: float = 11) -> Path:
    apply_style()
    g = parse_mermaid(text)
    _layout(g, fontsize)
    xs = [n.x - n.w / 2 for n in g.nodes.values()] + [n.x + n.w / 2 for n in g.nodes.values()]
    ys = [n.y - n.h / 2 for n in g.nodes.values()] + [n.y + n.h / 2 for n in g.nodes.values()]
    pad = 0.35
    width, height = max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad
    fig = plt.figure(figsize=(width, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.axis("off")

    patches = {}
    for n in g.nodes.values():
        if n.shape == "diamond":
            p = Polygon([(n.x, n.y + n.h / 2), (n.x + n.w / 2, n.y), (n.x, n.y - n.h / 2), (n.x - n.w / 2, n.y)],
                        closed=True, fc=DECISION_FILL, ec=NAVY, lw=1.2)
        elif n.shape == "circle":
            p = Circle((n.x, n.y), n.w / 2, fc=FILL, ec=NAVY, lw=1.2)
        elif n.shape == "io":
            s = 0.15
            p = Polygon([(n.x - n.w / 2 + s, n.y + n.h / 2), (n.x + n.w / 2 + s, n.y + n.h / 2),
                         (n.x + n.w / 2 - s, n.y - n.h / 2), (n.x - n.w / 2 - s, n.y - n.h / 2)],
                        closed=True, fc=FILL, ec=NAVY, lw=1.2)
        else:
            rad = 0.2 if n.shape == "round" else 0.04
            p = FancyBboxPatch((n.x - n.w / 2, n.y - n.h / 2), n.w, n.h, boxstyle=f"round,pad=0,rounding_size={rad}",
                               fc=FILL, ec=NAVY, lw=1.2)
        ax.add_patch(p)
        patches[n.id] = p
        ax.text(n.x, n.y, n.label, ha="center", va="center", fontsize=fontsize, color=TEXT, family="serif",
                linespacing=1.2, zorder=5)

    horizontal = g.direction in ("LR", "RL")
    lane = 0
    for e in g.edges:
        a, b = g.nodes[e.src], g.nodes[e.dst]
        if e.back or e.src == e.dst:
            # Feedback path: leave sideways, run outside every node in between, come back in.
            lane += 1
            span = [n for n in g.nodes.values() if min(a.layer, b.layer) <= n.layer <= max(a.layer, b.layer)]
            if horizontal:
                edge_y = min(n.y - n.h / 2 for n in span) - 0.3 * lane
                pts = [(a.x, a.y - a.h / 2), (a.x, edge_y), (b.x, edge_y), (b.x, b.y - b.h / 2)]
            else:
                edge_x = max(n.x + n.w / 2 for n in span) + 0.3 * lane
                pts = [(a.x + a.w / 2, a.y), (edge_x, a.y), (edge_x, b.y), (b.x + b.w / 2, b.y)]
            ax.plot([p[0] for p in pts[:-1]] + [pts[-1][0]], [p[1] for p in pts[:-1]] + [pts[-1][1]],
                    color="#222222", lw=1.1, linestyle=(0, (3, 3)) if e.style == "dotted" else "-", zorder=3,
                    solid_joinstyle="miter")
            ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=13, color="#222222",
                                         lw=1.1, shrinkA=0, shrinkB=1, zorder=3))
            if e.label:
                mx, my = (pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2
                ax.text(mx, my, e.label, ha="center", va="center", fontsize=fontsize - 1, family="serif", zorder=6,
                        bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none"})
            xs.extend(p[0] for p in pts)
            ys.extend(p[1] for p in pts)
            continue
        rad = 0.0
        if a.layer == b.layer:
            rad = 0.35
        style = {"dotted": (0, (3, 3)), "line": "-", "thick": "-"}.get(e.style, "-")
        arrow = FancyArrowPatch(
            (a.x, a.y), (b.x, b.y), patchA=patches[e.src], patchB=patches[e.dst],
            arrowstyle="-" if e.style == "line" else "-|>", mutation_scale=13,
            connectionstyle=f"arc3,rad={rad}", color="#222222", lw=2.0 if e.style == "thick" else 1.1,
            linestyle=style, shrinkA=1, shrinkB=1, zorder=3,
        )
        ax.add_patch(arrow)
        if e.label:
            mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
            if rad:
                dx, dy = b.x - a.x, b.y - a.y
                mx, my = mx + rad * dy * 0.5, my - rad * dx * 0.5
            ax.text(mx, my, e.label, ha="center", va="center", fontsize=fontsize - 1, family="serif", zorder=6,
                    bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none"})
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    fig.set_size_inches(max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    return out_path


# =========================================================================== circuits (schemdraw)

_ALIASES = {
    "r": "Resistor", "resistor": "Resistor", "res": "Resistor", "pot": "Potentiometer",
    "c": "Capacitor", "capacitor": "Capacitor", "cap": "Capacitor", "ecap": "Capacitor2",
    "l": "Inductor2", "inductor": "Inductor2", "coil": "Inductor2",
    "v": "SourceV", "vsource": "SourceV", "source": "SourceV", "dcsource": "SourceV", "battery": "Battery",
    "i": "SourceI", "isource": "SourceI", "ac": "SourceSin", "acsource": "SourceSin", "sine": "SourceSin",
    "gnd": "Ground", "ground": "Ground", "opamp": "Opamp", "diode": "Diode", "led": "LED", "zener": "Zener",
    "switch": "Switch", "spdt": "SwitchSpdt2", "dot": "Dot", "line": "Line", "wire": "Line", "gap": "Gap",
    "npn": "BjtNpn", "pnp": "BjtPnp", "nmos": "NFet", "pmos": "PFet", "lamp": "Lamp", "motor": "Motor",
    "speaker": "Speaker", "fuse": "Fuse", "meter": "MeterV", "voltmeter": "MeterV", "ammeter": "MeterA",
    "transformer": "Transformer", "label": "Label", "arrow": "Arrow", "vdd": "Vdd", "vss": "Vss",
    "and": "logic.And", "or": "logic.Or", "not": "logic.Not", "nand": "logic.Nand", "nor": "logic.Nor",
    "xor": "logic.Xor", "xnor": "logic.Xnor", "buf": "logic.Buf", "buffer": "logic.Buf",
}


def _element_class(name: str):
    import schemdraw.elements as elm
    import schemdraw.logic as logic

    key = _ALIASES.get(name.lower(), name)
    if key.startswith("logic."):
        return getattr(logic, key.split(".", 1)[1])
    for mod in (elm, logic):
        if hasattr(mod, key):
            return getattr(mod, key)
    raise ValueError(f"Unknown circuit element '{name}'. Try: resistor, capacitor, inductor, vsource, ground, "
                     f"opamp, diode, led, switch, npn, nmos, dot, line, and/or/not/nand/nor/xor.")


def render_circuit(items: list[dict], out_path: Path, unit: float = 2.5, fontsize: float = 11) -> Path:
    """Draw a circuit from a list of elements placed one after another (schemdraw's model).

    Each item: {type, dir(right|left|up|down|theta), len, label, label_loc(top|bot|left|right),
    value(second label), id, at("id.anchor"|"id"|[x,y]), to/tox/toy("id.anchor"), anchor(e.g. in1),
    flip, reverse, push, pop, inputs(for logic gates)}.
    """
    import schemdraw

    schemdraw.use("matplotlib")
    apply_style()
    ids: dict = {}

    def point(ref):
        if isinstance(ref, (list, tuple)):
            return tuple(ref)
        ref = str(ref)
        eid, _, anchor = ref.partition(".")
        if eid not in ids:
            raise ValueError(f"Unknown element id '{eid}' in '{ref}'")
        return getattr(ids[eid], anchor or "end")

    with schemdraw.Drawing(show=False, unit=unit, fontsize=fontsize, font=SERIF[0], lw=1.3) as d:
        d.config(font="serif")
        for it in items:
            if it.get("pop") and len(it) == 1:
                d.pop()
                continue
            cls = _element_class(str(it.get("type", "line")))
            kwargs = {}
            if "inputs" in it:
                kwargs["inputs"] = int(it["inputs"])
            e = cls(**kwargs)
            if "at" in it:
                e = e.at(point(it["at"]))
            if it.get("anchor"):
                e = e.anchor(it["anchor"])
            direction = str(it.get("dir", "")).lower()
            if direction in ("right", "left", "up", "down"):
                e = getattr(e, direction)()
            elif direction:
                e = e.theta(float(direction))
            if "len" in it:
                e = e.length(float(it["len"]) * unit)
            if "to" in it:
                e = e.to(point(it["to"]))
            if "tox" in it:
                e = e.tox(point(it["tox"]) if not isinstance(it["tox"], (int, float)) else it["tox"])
            if "toy" in it:
                e = e.toy(point(it["toy"]) if not isinstance(it["toy"], (int, float)) else it["toy"])
            if it.get("flip"):
                e = e.flip()
            if it.get("reverse"):
                e = e.reverse()
            if it.get("label"):
                e = e.label(str(it["label"]), loc=it.get("label_loc", "top"))
            if it.get("value"):
                e = e.label(str(it["value"]), loc="top" if it.get("label_loc") == "bot" else "bot")
            if it.get("push"):
                d.push()
            d += e
            if it.get("id"):
                ids[str(it["id"])] = e
            if it.get("pop"):
                d.pop()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        d.save(str(out_path), dpi=220)
    return out_path
