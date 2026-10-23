# Show the main equations used in DAC and amplifier analysis

The output of an $n$-bit DAC with reference $V_{ref}$ is

$$V_{out} = V_{ref} \times \frac{\text{Digital Code}}{2^{n}} \tag{1}$$

where the digital code is the decimal value of the input word. For a binary weighted resistor DAC,

$$V_{out} = -R_{f}\left(\frac{V_{1}}{R} + \frac{V_{2}}{2R} + \frac{V_{3}}{4R} + \cdots + \frac{V_{n}}{2^{n-1}R}\right) \tag{2}$$

and the R-2R ladder gives $V_{out} = -V_{ref}\sum_{i=1}^{n} b_{n-i}\,2^{-i}$ in compact form.

## Numerical Example

**Step 1 - Substitute the input voltages**

$$\begin{aligned}
V_{out} &= -\left(\frac{-5}{2} + \frac{0}{4} + \frac{-5}{8} + \frac{-5}{16} + \frac{0}{32}\right) \\
        &= -(-2.5 - 0.625 - 0.3125) \\
        &= 3.4375 V
\end{aligned}$$

## Other Forms

- RMS value: $V_{rms} = \dfrac{V_{m}}{\sqrt{2}}$ and a 50Hz supply has $\omega = 2\pi f = 314.16\ \text{rad/s}$.
- Transistor: $I_{C} = \beta I_{B}$ with $V_{CE} = V_{CC} - I_{C}R_{C}$ and $R_{C} = 2.2 k\Omega$, $C = 10\mu F$.
- Logic: $Y = \overline{A \cdot B} + A\oplus B$.

$$Z = R + jX = |Z|\angle\theta, \quad \theta = \tan^{-1}\left(\frac{X}{R}\right)$$

$$\mathbf{V} = \begin{bmatrix} Z_{11} & Z_{12} \\ Z_{21} & Z_{22} \end{bmatrix}\mathbf{I}$$

$$u(t) = \begin{cases} 1 & t \ge 0 \\ 0 & t < 0 \end{cases}$$

$$v_{C}(t) = \frac{1}{C}\int_{0}^{t} i(\tau)\,d\tau + v_{C}(0)$$
