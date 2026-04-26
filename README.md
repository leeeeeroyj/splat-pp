# splat-pp — Splatoon 3 Plaza Post Printer

Convert black-and-white PNG images into Arduino sketches that automatically draw on Splatoon 3's **Post Printer** canvas, using a Teensy 4.0 microcontroller emulating a Nintendo Switch Pro Controller.

![godHead example image](godHead.png)

---

## How it works

`splat-pp.py` reads a 320×120 pixel B&W PNG and converts it into a sequence of D-Pad moves and A button presses that trace every black pixel on the canvas.

The drawing sequence is encoded as a compact **bytecode array** stored in the Arduino sketch's flash memory (`PROGMEM`). A small interpreter loop (~30 lines of C) reads and executes each opcode at runtime. This approach keeps the compiled binary tiny regardless of image complexity — even a fully dense image produces only ~70 KB of data and a few hundred bytes of machine code, well within the Teensy 4.0's limits.

### Drawing strategy

Pixels are visited using a **snake scan** (boustrophedon): left-to-right on even rows, right-to-left on odd rows. This minimises total cursor travel and keeps draw time as short as possible.

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

- **Teensy 4.0** microcontroller
- USB cable (Teensy → Nintendo Switch)
- A momentary pushbutton wired to GPIO pin 0

### Software

- Python 3.11+
- [Arduino IDE](https://www.arduino.cc/en/software) 1.8.x with [Teensyduino](https://www.pjrc.com/teensy/td_download.html)
- Python packages:

```
pip install pillow numpy
```

---

## Usage

```
python splat-pp.py <image.png> [--duration <ms>] [--output <file>] [--preview]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `image.png` | — | Source image (PNG, ideally 320×120) |
| `--duration` | `25` | Milliseconds per action (range: 20–200) |
| `--output` | `drawImage.ino` | Output filename |
| `--preview` | off | Print an ASCII preview of the thresholded image |

### Example

```
python splat-pp.py mypost.png --duration 25 --output drawImage.ino --preview
```

Output:
```
Loading image: mypost.png
  Black pixels: 22,750 / 38,400

ASCII Preview:
+--------------------------------------------------------------------------------+
|   XX   XXXX  XX  ...                                                           |
+--------------------------------------------------------------------------------+

Planning snake-scan move sequence...
  Draw operations: 22,750
Encoding bytecode...
  Bytecode size : 68,318 bytes
  Est. draw time: 3056s (50.9 min)

Done! Written to: drawImage.ino
```

---

## Image requirements

- **Format:** PNG
- **Dimensions:** 320×120 pixels (other sizes are resized automatically)
- **Color:** Pure black (`#000000`) and white only — black pixels are drawn, white pixels are skipped
- **Grayscale input** is accepted and thresholded at 50% brightness automatically

For best results, prepare your image at exactly 320×120 in an image editor and convert to 1-bit B&W before running the script.

---

## Integration with the Arduino sketch

The generated `drawImage.ino` file contains two things: a `PROGMEM` data array holding the encoded moves, and a `drawImage()` function that interprets them. Paste the entire contents into your sketch at the marked location:

```cpp
////////////////////////////////////////
// PASTE THE drawImage FUNCTION BELOW //
////////////////////////////////////////

// → paste drawImage.ino contents here

////////////////////////////////////////
```

The sketch's `runMacro()` function handles everything else automatically:

1. Registers the controller with the Switch (3× A press)
2. Sets the smallest pen size (2× L press)
3. Clears the canvas (L-stick click)
4. Moves the cursor to the top-left corner (analog stick held for 7 seconds)
5. Calls `drawImage()` to draw your image
6. Saves and exits (Minus press)

Press the button wired to GPIO pin 0 to start the macro. The Switch must already be on the Post Printer canvas screen.

---

## Timing

The `--duration` parameter controls how long each individual D-Pad tap or button press is held (in milliseconds). Lower values draw faster but may cause missed inputs on slower connections.

| Duration | Reliability | ~Draw time (half-filled canvas) |
|----------|-------------|----------------------------------|
| 20ms | Marginal | ~25 min |
| 25ms | Good (default) | ~30 min |
| 50ms | Very reliable | ~60 min |

Draw time scales with the number of black pixels in your image. A fully filled 320×120 canvas at 25ms takes roughly 50–60 minutes.

---

## Technical notes

### Why bytecode instead of function calls?

An earlier approach generated one Arduino function call per drawing step. For complex images this produced 60,000+ lines of C, which overflowed the Teensy 4.0's 512 KB ITCM (tightly-coupled instruction memory) region and either failed to compile or took many minutes to do so.

Storing the moves as a `PROGMEM` byte array sidesteps this entirely. Data lives in regular flash (2 MB on the Teensy 4.0); only the ~30-line interpreter loop occupies ITCM. Compile times drop to a few seconds regardless of image complexity.

### Cursor coordinate system

The cursor origin `(0, 0)` is the **top-left** corner of the Post Printer canvas. The sketch's `runMacro()` function ensures the cursor is reset there by holding the left analog stick fully up-left for 7 seconds before `drawImage()` is called.

---

## License

MIT
