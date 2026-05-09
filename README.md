# splat-pp — Splatoon 3 Post Printer

Convert black-and-white PNG images into Arduino sketches that automatically draw on Splatoon 3's Plaza Post canvas, using a Teensy 4.0 microcontroller emulating a Nintendo Switch Pro Controller.

![Example Image](example.png)

---

## How it works

`splat-pp.py` reads a 320×120 pixel B&W PNG and converts it into a sequence of D-Pad moves and A button presses that trace every black pixel on the canvas.

The drawing sequence is encoded as a compact bytecode array stored in the Arduino sketch's flash memory (`PROGMEM`). A small interpreter loop (~30 lines of C) reads and executes each opcode at runtime. This approach keeps the compiled binary tiny regardless of image complexity! Even a fully dense image produces only ~70 KB of data and a few hundred bytes of machine code, well within the Teensy 4.0's limits.

### Drawing strategy

Pixels are visited using a "snake scan" (boustrophedon): left-to-right on even rows, right-to-left on odd rows. This minimizes total cursor travel and keeps draw time as short as possible.

### Bytecode format

Each instruction is 1–3 bytes:

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
- USB cable (Teensy → Nintendo Switch & Programming PC)
- A momentary push button wired to GPIO pin 0 (or hotwire it)

### Software

- Ubuntu/Debian Linux (the setup script targets this environment)
- Python 3.11+
- Git
- Python packages: `pillow`, `numpy`

```
pip install pillow numpy
```

---

## Setup

Environment setup is handled by `setup-nsgadget.sh`. This script installs and configures everything needed to compile and flash sketches from the command line. No Arduino IDE required!

### What the script does

1. Installs `arduino-cli` if not already present
2. Configures `arduino-cli` to use `~/Arduino` as its data directory
3. Installs the Teensy 4.0 core (v1.60.0)
4. Backs up the stock core before modifying it
5. Clones [dmadison/NSGadget_Teensy](https://github.com/dmadison/NSGadget_Teensy) > an updated fork of the NS Gamepad library (Thanks, dude!)
6. Installs the `Bounce2` library
7. Patches the Teensy core to support the `USB_NSGAMEPAD` USB type:
   - Adds `usb=nsgamepad` option to `boards.txt`
   - Fixes `TEENSYDUINO` version flag for compatibility with core 1.60.0
   - Upgrades C++ standard to C++17
   - Copies NSGamepad USB descriptor and driver files into the core
   - Patches `WProgram.h`, `Print.cpp`, and `yield.cpp` for NSGamepad compatibility
8. Installs Teensy udev rules (allows flashing without `sudo`)
9. Installs `teensy_loader_cli`

### Running the setup script

```bash
chmod +x setup-nsgadget.sh
./setup-nsgadget.sh
```

The script is safe to run multiple times. It skips steps that are already complete.

> **Note:** After the script runs for the first time, log out and back in (or reboot) for the udev rules to take effect before flashing.

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
4. Prompts you to press the button on your Teensy, then flashes it

### Example

```bash
python splat-pp.py img/godHead.png
```

Output:
```
Loading image: img/godHead.png
  Black pixels: 22,750 / 38,400
Planning snake-scan move sequence...
  Draw operations: 22,750
Encoding bytecode...
  Bytecode size : 68,318 bytes
  Est. draw time: 3056s (50.9 min)
Merging with template...
  Written to: sketch/godHead/godHead.ino

Compiling godHead...
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

## Image requirements

- **Format:** PNG
- **Dimensions:** 320×120 pixels (other sizes are resized automatically)
- **Color:** Pure black (`#000000`) and white only. Black pixels are drawn, white pixels are skipped
- **Grayscale input** is accepted and thresholded at 50% brightness automatically

For best results, prepare your image at exactly 320×120 in an image editor and convert to 1-bit B&W before running the script.

---

## How the sketch works

The sketch's `runMacro()` function handles everything automatically once triggered:

Default sketch.txt template covers these steps:

1. Registers the controller with the Switch (3× A press)
2. Sets the smallest pen size (2× L press)
3. Clears the canvas (L-stick click)
4. Moves the cursor to the top-left corner (analog stick held for 7 seconds)
5. Calls `drawImage()` to draw your image
6. Saves and exits (Minus press)

Open the post printer in the Splatoon 3 Plaza to start drawing a new post. Press the sync button on your controller to foce a disconnect. The controller screen should pop open. Press the button wired to GPIO pin 0 ONCE to start the macro. Let it run! When it is finished, you can disconnect the Teensy and reconnect your controllers. Head back to the post printer to review and share your post! 

---

## Timing

The `--duration` parameter controls how long each individual D-Pad tap or button press is held (in milliseconds). Lower values draw faster but may cause missed inputs on slower connections.

| Duration | Reliability | ~Draw time (half-filled canvas) |
|----------|-------------|----------------------------------|
| 20ms | Marginal | ~25 min |
| 25ms | Good (default) | ~30 min |
| 50ms | Very reliable | ~60 min |

Draw time scales with the number of black pixels in your image. A fully filled 320×120 canvas at 25ms takes roughly 50 - 60 minutes.

---

## Technical notes

### Why bytecode instead of function calls?

An earlier approach generated one Arduino function call per drawing step. For complex images this produced 60,000+ lines of C, which overflowed the Teensy 4.0's 512 KB ITCM (tightly-coupled instruction memory) region and either failed to compile or took many minutes to do so.

Storing the moves as a `PROGMEM` byte array sidesteps this entirely. Data lives in regular flash (2 MB on the Teensy 4.0); only the ~30-line interpreter loop occupies ITCM. Compile times drop to a few seconds regardless of image complexity.

### Why arduino-cli instead of the Arduino IDE?

`arduino-cli` allows compiling and flashing entirely from the command line, making it easy to integrate into scripts and automated workflows. The `setup-nsgadget.sh` script patches the Teensy 1.60.0 core to support the `USB_NSGAMEPAD` USB type required by NSGadget_Teensy, which the IDE's board manager GUI would normally handle via the USB Type dropdown menu.

### NSGadget_Teensy and the Teensy core

NSGadget_Teensy is not a standard Arduino library. It works by patching USB descriptor and driver files directly into the Teensy core. The setup script uses the [dmadison/NSGadget_Teensy](https://github.com/dmadison/NSGadget_Teensy) fork, which includes compatibility updates through Teensyduino 1.56. Additional patches are applied by the script for compatibility with Teensyduino 1.60.0.

### Cursor coordinate system

The cursor origin `(0, 0)` is the top-left corner of the Post Printer canvas. The sketch's `runMacro()` function ensures the cursor is reset there by holding the left analog stick fully up-left for 7 seconds before `drawImage()` is called.