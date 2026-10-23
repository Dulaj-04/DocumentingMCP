# Aim

- Configure an STM32 microcontroller using STM32CubeIDE to detect active I²C slave devices on the bus and display the detected device addresses on a Digilent PmodCLS 16×2 LCD.

# Apparatus

- NUCLEO-F411RE STM32 development board
- PmodCLS 16×2 LCD
- USB cable
- Jumper wires
- Computer with STM32CubeIDE
- 3.3 V power supply

# Theory

Inter-Integrated Circuit (I²C) is a synchronous serial communication protocol that is typically used for communication between a microcontroller and peripheral devices. It has two signal lines: Serial Data Line (SDA) and Serial Clock Line (SCL). Each device on the bus is identified by its own 7-bit address, and pull-up resistors are required on SDA and SCL to establish the logic-high level.

The PmodCLS is an alphanumeric LCD with two lines of 16 characters. Its I²C address is set by hardware jumpers; in this practical **MD2 = 1, MD1 = 0 and MD0 = 0, which resulted in the I²C address 0x48**. The 8-bit address placed on the bus is the 7-bit address shifted left by one bit:

$$A_{8} = (A_{7} \ll 1) \,|\, R/\overline{W}$$

An ‘I2C_ScanBus()’ routine verified the presence of the LCD using the HAL function `HAL_I2C_IsDeviceReady()`.

# Procedure

1. A new project was created in STM32CubeIDE and the NUCLEO-F411RE board was selected.
2. The RCC and I2C2 peripherals were configured and the clock settings were applied.
3. GND, 3.3 V, SDA (PB3) and SCL (PB10) were connected between the PmodCLS and the STM32 board.
4. An I²C scanning function was added to determine the address of the connected LCD.
5. The program was built and downloaded to the STM32 board.
6. The LCD was initialised and its display was cleared.
7. The cursor position was set and the text was sent to the LCD via I²C.
8. The displayed text was observed and verified on the 16×2 LCD.

# Observation

## Memory Inspection of Message Buffers

![Debugger view of the message buffers](debug_memory.png){width=100%}

| Buffer | Contents | Length (bytes) |
|---|---|---|
| `message1` | KDU UNIVERSITY | 15 |
| `message2` | D/ENG/EE/25/0000 | 17 |

Table: Message buffers observed in the debugger

# Result

- The system successfully established I²C communication and displayed the required text on the external LCD.

![LCD showing the two lines of text](lcd_result.png){width=60%}

# Code

```c
/* Scan the I2C2 bus for any connected slave device */
uint8_t I2C_ScanBus(void) {
    for (uint8_t addr = 1; addr < 128; addr++) {
        // Shift address by 1 bit to form the 8-bit write address
        if (HAL_I2C_IsDeviceReady(&hi2c2, addr << 1, 1, HAL_MAX_DELAY) == HAL_OK) {
            return addr; // Found device address
        }
    }
    return 0; // No device found
}
```

# Discussion

The experiment was completed successfully by connecting a 16×2 Digilent PmodCLS LCD to the STM32 NUCLEO-F411RE using the I²C protocol. Using I²C was beneficial because only two communication wires were required, rather than the many GPIO pins needed for a parallel interface.

The LCD was detected at address 0x48, matching the jumper configuration, which verified that the hardware configuration and the software address detection agreed.

# Conclusion

STM32CubeIDE was successfully used to configure I²C communication on the STM32F411RE. The ‘I2C_ScanBus()’ routine detected the PmodCLS at address 0x48, and the required strings were displayed on both rows of the LCD.
