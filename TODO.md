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

SKETCH_PATH = "sketch/"                 # Folder containing the .ino file
BOARD_FQBN  = "teensy:avr:teensy40"     # Fully Qualified Board Name
MCU         = "TEENSY40"                # MicroContollerUnit 

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
See arduino-cli Setup.md for information on the cli setup. 

