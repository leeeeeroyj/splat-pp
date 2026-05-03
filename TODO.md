# Ideas and todos

Compile and upload Arduino sketches from Python without ever opening the Arduino IDE
The key is the **Arduino CLI**, a command-line tool that handles everything the IDE does.

## How it works

**Arduino CLI** (`arduino-cli`) is an official tool from Arduino that lets you:
- Compile sketches
- Upload to boards
- Manage libraries and board packages

You run it from Python using `subprocess`.

## Basic Python example

```python
import subprocess

SKETCH_PATH = "/path/to/your/sketch"   # folder containing the .ino file
BOARD_FQBN  = "arduino:avr:uno"        # Fully Qualified Board Name
PORT        = "/dev/ttyUSB0"           # e.g. COM3 on Windows

# Compile
compile_result = subprocess.run(
    ["arduino-cli", "compile", "--fqbn", BOARD_FQBN, SKETCH_PATH],
    capture_output=True, text=True
)
print(compile_result.stdout)
if compile_result.returncode != 0:
    print("Compile error:", compile_result.stderr)
    exit(1)

# Upload
upload_result = subprocess.run(
    ["arduino-cli", "upload", "-p", PORT, "--fqbn", BOARD_FQBN, SKETCH_PATH],
    capture_output=True, text=True
)
print(upload_result.stdout)
if upload_result.returncode != 0:
    print("Upload error:", upload_result.stderr)
```

## Setup steps

1. **Install Arduino CLI** — download from [arduino.cc/pro/cli](https://arduino.cc/pro/cli) or via a package manager:
   ```bash
   # macOS
   brew install arduino-cli

   # Windows (via Chocolatey)
   choco install arduino-cli
   ```

2. **Install the core for your board** (one-time setup):
   ```bash
   arduino-cli core update-index
   arduino-cli core install arduino:avr   # for Uno, Nano, Mega, etc.
   ```

3. **Find your board's FQBN and port:**
   ```bash
   arduino-cli board list        # shows connected boards and ports
   arduino-cli board listall     # search for your board's FQBN
   ```

## Common FQBNs

| Board | FQBN |
|---|---|
| Uno | `arduino:avr:uno` |
| Nano | `arduino:avr:nano` |
| Mega 2560 | `arduino:avr:mega` |
| Leonardo | `arduino:avr:leonardo` |
| ESP32 | `esp32:esp32:esp32` |

## Port tips by OS
- **Windows:** `COM3`, `COM4`, etc.
- **macOS:** `/dev/cu.usbmodem*` or `/dev/cu.usbserial*`
- **Linux:** `/dev/ttyUSB0` or `/dev/ttyACM0`

You can even auto-detect the port in Python by running `arduino-cli board list` and parsing the output, so the whole pipeline — generate sketch → compile → upload — can be fully automated.