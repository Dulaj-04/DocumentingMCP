# Define a Digital-to-Analog Converter (DAC) and explain its importance in modern electronic systems.

A Digital-to-Analog Converter (DAC) is an electronic circuit that transforms a discrete binary input code into a corresponding continuous analog quantity, typically an output voltage or current.

## Significance in Contemporary Electronic Systems

- **Audio and Multimedia Systems** - Compressed audio streams are reconstructed into continuous waveforms by a DAC before amplification.
- **Telecommunications** - In software-defined radio, baseband digital signals are converted to analog before modulation.
- **Industrial Control and Automation** - Controllers use DAC outputs to set analog references for servo drives and VFDs.

# Explain the basic operation of a DAC using a suitable block diagram.

![DAC block diagram](dac_block_diagram.png){width=100%}

The analog output voltage of an $n$-bit DAC is

$$V_{out} = V_{ref} \times \frac{D}{2^{n}}$$

where $D$ is the decimal equivalent of the binary input word.

# Compare the Binary Weighted Resistor DAC and the R-2R Ladder DAC.

## Working Principle

The R-2R ladder output is

$$V_{out} = -V_{ref}\sum_{i=1}^{n} b_{n-i}\,\frac{1}{2^{i}}$$

| Parameter | Binary Weighted | R-2R Ladder |
|---|---|---|
| Resistor values | $n$ different values | Only $R$ and $2R$ |
| Accuracy | Poor beyond 8 bits | High |
| Cost | Higher at high resolution | Lower |

# References

1. B. Razavi, *Principles of Data Conversion System Design*. IEEE Press, 1995.
2. W. Kester, *The Data Conversion Handbook*. Newnes, 2005.
