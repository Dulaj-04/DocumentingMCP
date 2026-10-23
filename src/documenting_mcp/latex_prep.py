"""Normalise LaTeX before it is converted to Word equations, so equations follow scientific typesetting
conventions (ISO 80000-2 / IEEE style) and common LaTeX habits do not break the conversion.

- Descriptive subscripts are upright: V_{out} -> V_{\\mathrm{out}}, I_{CE} -> I_{\\mathrm{CE}}.
  Index subscripts stay italic: b_{n-i}, x_{ij}, R_{k}.
- Units after numbers are upright text with a thin space: 5 V -> 5\\,\\text{V}, 10 kHz -> 10\\,\\text{kHz}.
- siunitx (\\SI, \\si, \\qty, \\unit) and \\degree / \\ohm / \\celsius are rewritten to plain LaTeX.
- \\tag{..} is extracted (Word equations cannot hold it) so the caller can typeset a number.
- equation/align environments and \\label/\\nonumber are reduced to what the converter supports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Two-letter lowercase subscripts that are descriptive in EE (everything else of length 2 is
# treated as an index pair such as ij, mn).
_DESCRIPTIVE_2 = {
    "in", "ss", "pk", "pp", "dc", "ac", "th", "eq", "on", "fb", "cm", "dm", "lo", "hi", "av",
    "ph", "ll", "ln", "fl", "nl", "sc", "oc", "sh", "se", "st", "rt", "bw", "id", "op",
}

_UNITS_MULTI = (
    "kV mV uV kA mA uA nA kW MW mW GW VA kVA MVA var kvar Hz kHz MHz GHz ms us ns ps "
    "mH uH nH mF uF nF pF mm cm km dB dBm rpm Nm kg rad kWh Wh Ah mAh pu Wb lm lx Pa kPa kJ"
).split()
_UNITS_SINGLE = "V A W F H S s J N T K C".split()  # need an explicit space after the number...
_UNITS_TIGHT = "V A W".split()  # ...except these, which EE writes as "5V", "2A", "60W"

_SI_UNITS = {
    "volt": "V", "ampere": "A", "amp": "A", "ohm": r"\Omega", "watt": "W", "hertz": "Hz",
    "farad": "F", "henry": "H", "second": "s", "siemens": "S", "joule": "J", "newton": "N",
    "metre": "m", "meter": "m", "kelvin": "K", "coulomb": "C", "tesla": "T", "weber": "Wb",
    "decibel": "dB", "radian": "rad", "degreeCelsius": r"^{\circ}C", "percent": r"\%",
}
_SI_PREFIX = {
    "pico": "p", "nano": "n", "micro": r"\mu ", "milli": "m", "kilo": "k", "mega": "M", "giga": "G",
}

_PROTECTED = re.compile(r"\\(?:text|mathrm|operatorname|mbox|textrm|mathit|mathbf)\s*\{[^{}]*\}")


@dataclass
class PreparedMath:
    latex: str
    tag: str | None = None  # equation number requested with \tag{..}
    notag: bool = False  # \nonumber / \notag present
    label: str | None = None  # \label{eq:...} for cross-references
    number: str | None = None  # assigned by the builder for display equations


def _si_units(spec: str) -> str:
    out = []
    for prefix, unit in re.findall(r"\\(pico|nano|micro|milli|kilo|mega|giga)?\\?([A-Za-z]+)", spec):
        if unit in _SI_PREFIX and not prefix:
            out.append(_SI_PREFIX[unit])
            continue
        sym = _SI_UNITS.get(unit, unit)
        out.append(_SI_PREFIX.get(prefix, "") + sym)
    body = "".join(out) if out else spec
    return r"\mathrm{" + body + "}"


def _rewrite_siunitx(tex: str) -> str:
    tex = re.sub(r"\\(?:SI|qty)\s*\{([^{}]*)\}\s*\{([^{}]*)\}", lambda m: m.group(1) + r"\," + _si_units(m.group(2)), tex)
    tex = re.sub(r"\\(?:si|unit)\s*\{([^{}]*)\}", lambda m: _si_units(m.group(1)), tex)
    tex = re.sub(r"\\num\s*\{([^{}]*)\}", r"\1", tex)
    tex = tex.replace(r"\celsius", r"^{\circ}\mathrm{C}").replace(r"\degree", r"^{\circ}")
    tex = re.sub(r"\\ohm(?![A-Za-z])", r"\\Omega", tex)
    return tex


def _upright_subscripts(seg: str) -> str:
    def repl(m: re.Match) -> str:
        word = m.group(1)
        descriptive = len(word) >= 3 or (word.isupper() and len(word) >= 2) or word in _DESCRIPTIVE_2
        return "_{\\mathrm{" + word + "}}" if descriptive else m.group(0)

    return re.sub(r"_\{([A-Za-z]{2,})\}", repl, seg)


def _upright_units(seg: str) -> str:
    sep = r"(?:\s|\\,|\\ |\\;|\\:|~)"
    multi = "|".join(sorted(map(re.escape, _UNITS_MULTI), key=len, reverse=True))
    single = "|".join(_UNITS_SINGLE)
    seg = re.sub(rf"(\d){sep}*({multi})(?![A-Za-z])", r"\1\\,\\text{\2}", seg)
    seg = re.sub(rf"(\d){sep}+({single})(?![A-Za-z_^])", r"\1\\,\\text{\2}", seg)
    seg = re.sub(rf"(\d)({'|'.join(_UNITS_TIGHT)})(?![A-Za-z_^{{])", r"\1\\,\\text{\2}", seg)
    # 10\mu F, 4.7 \mu H
    seg = re.sub(rf"(\d){sep}*\\mu\s*(F|H|A|V|s|m|W|C)(?![A-Za-z])", r"\1\\,\\text{µ\2}", seg)
    # 10 k\Omega, 2.2\,M\Omega, 50 \Omega
    seg = re.sub(rf"(\d){sep}*(k|M|m)?\s*\\Omega(?![A-Za-z])", lambda m: m.group(1) + r"\," + (r"\text{" + m.group(2) + "}" if m.group(2) else "") + r"\Omega", seg)
    return seg


def _outside_protected(tex: str, fn) -> str:
    parts, last = [], 0
    for m in _PROTECTED.finditer(tex):
        parts.append(fn(tex[last : m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(fn(tex[last:]))
    return "".join(parts)


def prepare(tex: str, *, scientific: bool = True) -> PreparedMath:
    tag = None
    m = re.search(r"\\tag\*?\s*\{([^{}]*)\}", tex)
    if m:
        tag = m.group(1).strip()
        tex = tex[: m.start()] + tex[m.end() :]
    notag = bool(re.search(r"\\(?:nonumber|notag)\b", tex))
    tex = re.sub(r"\\(?:nonumber|notag)\b", "", tex)
    lab = re.search(r"\\label\s*\{([^{}]*)\}", tex)
    tex = re.sub(r"\\label\s*\{[^{}]*\}", "", tex)
    tex = re.sub(r"\\(?:begin|end)\{(?:equation|displaymath)\*?\}", "", tex)
    tex = re.sub(r"\\(begin|end)\{(?:align|eqnarray|flalign)\*?\}", r"\\\1{aligned}", tex)
    tex = _rewrite_siunitx(tex)
    if scientific:
        tex = _outside_protected(tex, lambda s: _upright_units(_upright_subscripts(s)))
    return PreparedMath(latex=tex.strip(), tag=tag, notag=notag, label=lab.group(1).strip() if lab else None)
