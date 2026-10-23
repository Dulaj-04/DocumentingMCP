# Explain the basic operation of a DAC using a suitable block diagram

The fundamental task of a DAC is to map each possible n-bit binary input code to a unique, proportionate analog output level [@razavi1995]. The generalised functional chain is shown in @fig:block.

```{.diagram #fig:block caption="Functional block diagram of an n-bit DAC"}
flowchart LR
  IN[/Digital Input<br>n-bit word/] --> L[Input Register /<br>Latch]
  L --> SW[Switching<br>Network]
  REF[Reference Voltage<br>$V_{ref}$] --> SW
  SW --> W[Weighting /<br>Summing Circuit]
  W --> A[Output Amplifier<br>Op-Amp]
  A --> OUT((Analog<br>Output))
```

## Block Descriptions:

- **Input Register / Latch -** Captures and holds the n-bit digital word presented by the controlling processor.
- **Switching Network -** Each bit of the digital word controls a corresponding analog switch.
- **Output Amplifier (Op-Amp) -** Converts the summed current to a voltage and buffers the output.

The analog output voltage for an n-bit DAC follows the relation in @eq:dac:

$$V_{out} = V_{ref} \times \frac{D}{2^{n}} \label{eq:dac}$$

where $D$ is the decimal equivalent of the binary input word. The ideal staircase transfer characteristic of a 3-bit DAC with $V_{ref} = 2.5 V$ is plotted in @fig:transfer.

```{.plot #fig:transfer caption="Transfer characteristic of a 3-bit DAC ($V_{ref}$ = 2.5 V)"}
type: step
x_label: Digital input code D
y_label: "$V_{out}$ (V)"
series:
  - label: Ideal output
    x: [0, 1, 2, 3, 4, 5, 6, 7, 8]
    y: [0, 0.3125, 0.625, 0.9375, 1.25, 1.5625, 1.875, 2.1875, 2.1875]
  - label: "Straight-line fit"
    type: line
    expr: "2.5*x/8"
    var: x
    range: [0, 8]
    style: "--"
```

# Explain the working principle of the Binary Weighted Resistor DAC

### Binary Weighted Resistor DAC

## Working Principle

The binary weighted resistor DAC uses an inverting summing amplifier whose input resistors are scaled in powers of two, as drawn in @fig:bw [@sedra2015, p. 1012].

```{.circuit #fig:bw caption="Inverting summing amplifier at the heart of the binary weighted DAC"}
- {type: opamp, id: op}
- {type: line, at: op.in1, dir: left, len: 0.5}
- {type: dot, id: sum}
- {type: resistor, dir: left, label: "$R$", value: "MSB"}
- {type: line, at: sum.center, dir: up, len: 0.75}
- {type: resistor, dir: right, tox: op.out, label: "$R_f$"}
- {type: line, toy: op.out, dir: down}
- {type: line, at: op.in2, dir: left, len: 0.3}
- {type: ground}
- {type: line, at: op.out, dir: right, len: 0.5, label: "$V_{out}$", label_loc: right}
```

The output voltage is

$$V_{out} = -R_{f}\left(\frac{V_{1}}{R} + \frac{V_{2}}{2R} + \cdots + \frac{V_{n}}{2^{n-1}R}\right) \label{eq:bw}$$

## Performance Parameter Analysis

| Parameter | Binary Weighted Resistor DAC | R-2R Ladder DAC |
|---|---|---|
| Resistor values | $n$ different values | Only $R$ and $2R$ |
| Accuracy | Poor beyond 8 bits | High |
| Cost | Higher at high resolution | Lower |

Table: Comparison of the two DAC architectures {#tbl:compare}

As @tbl:compare shows, the R-2R ladder is preferred in integrated converters [@kester2005].

# References
