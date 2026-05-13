# splat-pp - Splatoon 3 Post Printer

Convert black-and-white PNG images into Arduino sketches that automatically draw on Splatoon 3's Plaza Post canvas, using a Teensy 4.0 microcontroller emulating a Nintendo Switch Pro Controller (Hori HoriPAD S).

![Example Image](example.png)

---

## How it works

`splat-pp.py` reads a 320×120 pixel B&W PNG and converts it into a sequence of D-Pad moves and A button presses that trace every black pixel on the canvas.

The drawing sequence is encoded as a fcompact bytecode array stored in the Arduino sketch's flash memory (`PROGMEM`). A small interpreter loop (~30 lines of C) reads and executes each opcode at runtime. Even a fully dense image produces only ~70 KB of data and a few hundred bytes of machine code, well within the Teensy 4.0's limits.

### Drawing strategy

Pixels are visited using a "snake scan" (boustrophedon): left-to-right on even rows, right-to-left on odd rows. This minimises total cursor travel and keeps draw time as short as possible.

### Bytecode format

Each instruction is 1–2 bytes:

| Opcode | Hex | Arguments | Action |
|--------|-----|-----------|--------|
| `OP_DRAW` | `0x00` | — | Press A (stamp pixel) |
| `OP_UP` | `0x01` | `n` (1 byte) | Move cursor up n steps |
| `OP_DOWN` | `0x02` | `n` (1 byte) | Move cursor down n steps |
| `OP_LEFT` | `0x03` | `n` (1 byte) | Move cursor left n steps |
| `OP_RIGHT` | `0x04` | `n` (1 byte) | Move cursor right n steps |

Moves larger than 255 steps are split into multiple instructions automatically.

---

## Requirements

### Hardware

- Teensy 4.0 microcontroller
- USB cable (Teensy → Nintendo Switch or PC)
- A momentary push button wired between GPIO pin 0 and GND (or bridge the pins directly)

### Software

- Ubuntu/Debian Linux
- Python 3.11+
- Git
- `arduino-cli`
- `teensy_loader_cli`
- Python packages: `pillow`, `numpy`

```bash
pip install pillow numpy
```

---

## Setup

Run the setup script once. It installs and patches everything needed to compile and flash sketches from the command line. No Arduino IDE required!

```bash
chmod +x setup-nsgadget.sh
./setup-nsgadget.sh
```

The script is safe to re-run. Each step is guarded and skipped if already complete.

### What the script does

1. Installs `arduino-cli`
2. Configures `arduino-cli` to use `~/Arduino` as its data directory
3. Installs the Teensy 4.0 core (v1.60.0)
4. Clones [dmadison/NSGadget_Teensy](https://github.com/dmadison/NSGadget_Teensy)  - Provides the USB HID descriptor files that make the Teensy appear as a Hori HoriPAD S controller
5. Installs the `Bounce2` library
6. Copies the NSGamepad USB descriptor files (`usb_nsgamepad.c/h`, `usb_desc.c/h`, `usb_inst.cpp`) into the Teensy core
7. **Surgically patches `boards.txt`** - appends only the `usb=nsgamepad` USB type entry, preserving the stock `gnu++17` compiler flags that Teensy core 1.60.0 requires
8. **Patches `usb.c`** — adds the missing `usb_nsgamepad_configure()` call to the USB configuration callback. Without this, the HID endpoint never opens and no button reports are sent even though the controller is recognised
9. Patches `WProgram.h` to include `usb_nsgamepad.h`
10. Patches `Print.cpp` and `yield.cpp` to disable Serial references in NSGamepad USB mode
11. Installs Teensy udev rules (allows flashing without `sudo`)
12. Installs `teensy_loader_cli`

> **Note:** After running the script for the first time, log out and back in (or reboot) for the udev rules to take effect.

> **Note:** If you previously had a `~/Arduino/packages/teensy/hardware/avr/1.60.0.stock-backup` directory from an old setup attempt, rename it with a hyphen instead of a dot — arduino-cli chokes on the dot in the directory name:
> ```bash
> mv ~/Arduino/packages/teensy/hardware/avr/1.60.0.stock-backup \
>    ~/Arduino/packages/teensy/hardware/avr/1.60.0-stock-backup
> ```

---

## Usage

```
python splat-pp.py <image.png> [--duration <ms>] [--template <file>]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `image.png` | — | Source image (PNG, ideally 320×120) |
| `--duration` | `25` | Milliseconds per action (range: 20–200) |
| `--template` | `sketch.txt` | Path to Arduino sketch template |

The script handles everything in one run:

1. Converts the image to a bytecode sequence
2. Merges it with the sketch template
3. Compiles the sketch with `arduino-cli`
4. Prompts you to put the Teensy into flash mode, then flashes it

### Example

```bash
python splat-pp.py img/myimage.png
```

Output:
```
Loading image: img/myimage.png
  Black pixels: 22,750 / 38,400
Planning snake-scan move sequence...
  Draw operations: 22,750
Encoding bytecode...
  Bytecode size : 68,318 bytes
  Est. draw time: 3056s (50.9 min)
Merging with template...
  Written to: sketch/myimage/myimage.ino

Compiling myimage...
  Sketch uses 45404 bytes (2%) of program storage space. Maximum is 2031616 bytes.
  Compile successful.

─────────────────────────────────────────
  Ready to flash.
  Press the button on your Teensy, then
  press Enter here to flash...
─────────────────────────────────────────

Cleaning up build directory...

Done! Connect your Teensy to the Switch and head to the plaza post printer!
```

---

## Drawing workflow

1. In Splatoon 3, open the **Plaza Post Printer** and start a new post
2. Press the **sync button** on your real controller to disconnect it.  The controller pairing screen will appear.
3. Plug the Teensy into the Switch via USB
4. Press the **button wired to GPIO pin 0** on the Teensy **once**
5. The macro will automatically:
   - Register the controller with the Switch (3× A press)
   - Select the smallest pen size (2× L press)
   - Clear the canvas (L-stick click)
   - Move the cursor to the top-left corner (analog stick held for 7 seconds)
   - Draw your image
   - Save and exit (Minus press)
6. When finished, disconnect the Teensy and reconnect your real controllers
7. Head back to the Post Printer to review and share your post

---

## Image requirements

- **Format:** PNG
- **Dimensions:** 320×120 pixels (other sizes are resized automatically)
- **Color:** Pure black (`#000000`) pixels are drawn; white pixels are skipped
- **Grayscale** input is accepted and thresholded at 50% brightness automatically

For best results, prepare your image at exactly 320×120 in an image editor and convert to 1-bit B&W before running the script.

---

## Timing

The `--duration` parameter controls how long each D-Pad tap or button press is held (in milliseconds). Lower values draw faster but may cause missed inputs.

| Duration | Reliability | ~Draw time (half-filled canvas) |
|----------|-------------|----------------------------------|
| 20ms | Marginal | ~25 min |
| 25ms | Good (default) | ~30 min |
| 50ms | Very reliable | ~60 min |

Draw time scales with the number of black pixels. A fully filled 320×120 canvas at 25ms takes roughly 50–60 minutes.

---

## Technical notes

### The missing `usb_nsgamepad_configure()` call

The core issue that prevented button presses from registering — even when the controller was correctly recognised — was a missing line in `usb.c`. The Teensy core calls each USB device's configure function when the USB host completes enumeration. This sets up the transmit endpoint and DMA buffers. Every other USB type (joystick, keyboard, mouse, etc.) had its configure call registered in `usb.c`. NSGadget's `usb_nsgamepad_configure()` was never added. Without it, `usb_nsgamepad_send()` exits immediately on every call because `usb_configuration` is never set, so every HID report is silently dropped. The setup script now patches this.

### Why `NSGamepad.write()` not `NSGamepad.loop()`

The `usb_nsgamepad_class::loop()` method only transmits if at least 7ms have elapsed since the last send — it's a rate limiter for the main loop, not a send function. Using it inside `pressButton()` causes sends to be silently skipped when called in rapid succession. The sketch uses `NSGamepad.write()` everywhere inside the macro, which always transmits immediately. `NSGamepad.loop()` is only used in the Arduino `loop()` function to keep the USB connection alive between macro runs.

### Why boards.txt is patched surgically, not replaced

The NSGadget `boards.txt` sets `-std=gnu++14`. Teensy core 1.60.0 headers (particularly `IntervalTimer.h`) use C++17 features (`std::is_arithmetic_v`, `if constexpr`) that fail to compile under `gnu++14`. The setup script appends only the three `nsgamepad` menu lines to the stock `boards.txt`, leaving the `gnu++17` flags intact.

### Why bytecode instead of function calls

An earlier approach generated one Arduino function call per drawing step. For complex images this produced 60,000+ lines of C, which overflowed the Teensy 4.0's 512 KB ITCM region. Storing moves as a `PROGMEM` byte array sidesteps this — data lives in flash (2 MB), only the ~30-line interpreter occupies ITCM. Compile times drop to a few seconds regardless of image complexity.

### NSGadget_Teensy and the Teensy core

NSGadget_Teensy is not a standard Arduino library. It patches USB descriptor and driver files directly into the Teensy core to make the device report as a Nintendo Switch-compatible Hori HoriPAD S controller. The setup script uses the [dmadison/NSGadget_Teensy](https://github.com/dmadison/NSGadget_Teensy) fork.
