# Explain the basic operation of a DAC using a suitable block diagram

A digital-to-analog converter (DAC) takes an n-bit binary number and gives out a voltage that is proportional to that number [@razavi1995]. The main parts of a DAC are shown in @fig:block.

```{.diagram #fig:block caption="Block diagram of an n-bit DAC"}
flowchart LR
  IN[/Digital input<br>n-bit word/] --> L[Input register /<br>latch]
  L --> SW[Switching<br>network]
  REF[Reference voltage<br>$V_{ref}$] --> SW
  SW --> W[Resistor<br>network]
  W --> A[Output<br>op-amp]
  A --> OUT((Analog<br>output))
```

## Block Descriptions:

- **Input register / latch -** holds the digital word steady while it is being converted, so the output does not glitch when the bits change.
- **Switching network -** each bit controls one switch. A 1 connects that branch to $V_{ref}$ and a 0 connects it to ground.
- **Resistor network and op-amp -** the resistors weight each bit according to its position, and the op-amp adds the currents and converts the total into a voltage.

For an n-bit DAC the output voltage is given by @eq:dac:

$$V_{out} = V_{ref} \times \frac{D}{2^{n}} \label{eq:dac}$$

where $D$ is the decimal value of the input code. For a 3-bit DAC with $V_{ref} = 2.5 V$, one step (1 LSB) is about 0.31 V. The ideal staircase output is plotted in @fig:transfer.

```{.plot #fig:transfer caption="Transfer characteristic of a 3-bit DAC with $V_{ref}$ = 2.5 V"}
type: step
x_label: Input code D
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

This DAC is an inverting summing amplifier where the input resistors are R, 2R, 4R and so on, as drawn in @fig:bw [@sedra2015, p. 1012]. The most significant bit goes through the smallest resistor, so it gives the largest current.

```{.circuit #fig:bw caption="Inverting summing amplifier used in the binary weighted DAC"}
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

Adding the current from each branch gives

$$V_{out} = -R_{f}\left(\frac{V_{1}}{R} + \frac{V_{2}}{2R} + \cdots + \frac{V_{n}}{2^{n-1}R}\right) \label{eq:bw}$$

where $V_{1}$ to $V_{n}$ are either $V_{ref}$ or 0 V depending on the bits.

## Comparison with the R-2R Ladder

| Parameter | Binary weighted DAC | R-2R ladder DAC |
|---|---|---|
| Resistor values | $n$ different values | Only $R$ and $2R$ |
| Accuracy | Poor above about 8 bits | Good |
| Cost | Higher for many bits | Lower |

Table: Binary weighted and R-2R ladder DACs compared {#tbl:compare}

From @tbl:compare, the R-2R ladder is easier to make accurately because only two resistor values have to be matched, which is why most integrated DACs use it [@kester2005].

# References
