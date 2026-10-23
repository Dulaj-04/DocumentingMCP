# Define a Digital-to-Analog Converter (DAC) and explain its importance in modern electronic systems

A Digital-to-Analog Converter (DAC) is an electronic circuit that transforms a discrete binary (digital) input code into a corresponding continuous analog quantity - typically an output voltage or current. The magnitude of the analog output is directly proportional to the numerical value represented by the applied digital word.

## Significance in Contemporary Electronic Systems

Modern engineering is fundamentally built on the coexistence of digital processing and real-world analog phenomena. DACs serve as the critical interface between these two domains. Their role is indispensable across a broad range of disciplines:

- **Audio and Multimedia Systems -** Compressed audio streams (e.g., FLAC, MP3) stored as binary data are reconstructed into smooth, continuous waveforms by a DAC before being amplified and delivered to loudspeakers.
- **Telecommunications -** In software-defined radio (SDR) and OFDM-based systems, baseband digital signals must be converted to analog before modulation onto a carrier.
- **Industrial Control and Automation -** Programmable controllers rely on DAC outputs to set analog reference voltages for servo drives, variable-frequency drives (VFDs) and proportional valves.

In each of these contexts the DAC converts an abstract numerical representation into a physical signal that can actuate, transmit, or be perceived.

# Explain the basic operation of a DAC using a suitable block diagram

The fundamental task of a DAC is to map each possible n-bit binary input code to a unique, proportionate analog output level.

![DAC block diagram](dac_block_diagram.png)

## Block Descriptions:

- **Input Register / Latch -** Captures and holds the n-bit digital word presented by the controlling processor.
- **Switching Network -** Each bit of the digital word controls a corresponding analog switch.
- **Output Amplifier (Op-Amp) -** Converts the summed current to a voltage and buffers the output.

The analog output voltage for an n-bit DAC follows the relation:

$$V_{out} = V_{ref} \times \frac{(\text{Digital Code})}{2^{n}}$$

where the ‘Digital Code’ is the decimal equivalent of the binary input word.

# Explain the working principle of the Binary Weighted Resistor DAC and the R-2R Ladder DAC, and compare their performance

### Binary Weighted Resistor DAC

## Working Principle

The binary weighted resistor DAC employs an inverting summing amplifier whose input resistors are scaled in powers of two. For an n-bit converter the resistor assigned to bit k has the value:

$$R_{k} = 2^{k-1} \times R_{base} \quad ; (k = 1, 2, \ldots, n)$$

The output voltage is:

$$V_{out} = -IR_{f} = -R_{f}\left(\frac{V_{1}}{R} + \frac{V_{2}}{2R} + \frac{V_{3}}{4R} + \cdots + \frac{V_{n}}{2^{n-1}R}\right)$$

## Advantages

- Conceptually straightforward - a direct extension of the weighted summing amplifier.
- Fast settling because current summing is instantaneous once switches settle.

## Limitations

- Practical implementation becomes problematic beyond 8 bits because resistor values span an enormous range.

## Performance Parameter Analysis

| Parameter | Binary Weighted Resistor DAC | R-2R Ladder DAC |
|---|---|---|
| Resolution | Theoretically proportional to bit count, but practically limited by the difficulty of maintaining tight tolerance across a wide resistor range. | Consistent and scalable resolution across all bit counts because accuracy depends only on the 2:1 ratio of R to 2R. |
| Accuracy | Lower for high-bit-count designs due to cumulative mismatch errors. | Inherently higher because only relative matching between R and 2R matters. |
| Linearity | Worsens progressively with bit count as resistor tolerances compound. | Superior linearity is maintained across the full output range. |
| Settling Time | Generally faster; no inter-node signal propagation is required. | Marginally slower; the ladder must re-equilibrate through multiple nodes. |

# A 5-bit Binary Weighted Resistor DAC uses resistor values $R, 2R, 4R, 8R$ and $16R$ with a feedback resistor $R_{f} = \frac{R}{2}$. The reference voltage is $-5V$ and the digital input word is 10110. Find the output voltage.

**Given Data**

- Resistor values: R, 2R, 4R, 8R, 16R (bits 1 through 5, MSB to LSB)
- Digital input word: 10110
- Input voltages: V₁ = −5 V, V₂ = 0 V, V₃ = −5 V, V₄ = −5 V, V₅ = 0 V

**Step 1 - Summing Amplifier Expression**

$$V_{out} = -R_{f}\left(\frac{V_{1}}{R} + \frac{V_{2}}{2R} + \frac{V_{3}}{4R} + \frac{V_{4}}{8R} + \frac{V_{5}}{16R}\right)$$

**Step 2 - Substitute Input Voltages**

$$V_{out} = -\left(\frac{-5}{2} + \frac{0}{4} + \frac{-5}{8} + \frac{-5}{16} + \frac{0}{32}\right) = +3.4375\ \text{V}$$

The positive output voltage arises because the active input voltages are negative (−5 V) and the inverting amplifier negates them.

# References

1. B. Razavi, *Principles of Data Conversion System Design*. IEEE Press, 1995.
2. W. Kester, *The Data Conversion Handbook*. Newnes, 2005.
