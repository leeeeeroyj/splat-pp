# splat-pp: PNG to Splatoon 3 Drawing Macro Converter

Convert black and white PNG images (320×120 pixels) into Arduino macros that draw on Splatoon 3's Plaza Post Printer using a Teensy 4.0 microcontroller emulating a Nintendo Switch Pro Controller.

## How It Works

The tool converts a PNG image into a sequence of D-Pad movements and button presses:
- **D-Pad** controls cursor position (up/down/left/right)
- **A button** stamps the brush at the current position
- **Drawing strategy**: Move to each black pixel in the image, draw it, then move to the next

The algorithm optimizes macro size and execution time by:
1. Identifying drawable rows (rows containing ≥1 black pixel)
2. Skipping entirely empty rows (no wasted movement commands)
3. Alternating direction between rows (L→R, R→L, L→R...) to minimize cursor travel
4. Bundling consecutive pixels into efficient for loops

## Setup

```bash
cd 
mkdir -p tools/splat-pp
cd tools/splat-pp

# Create and activate conda environment
conda create --name splat-pp python=3.11 -y
conda activate splat-pp

# Install dependencies
pip install numpy pillow
```

## Usage

### Basic Usage
Convert an image with default 25ms timing:
```bash
python splat-pp.py img/myimage.png
```
Output: `macro/myimage.ino`

### Specify Output File
```bash
python splat-pp.py img/myimage.png custom_output.ino
```

### Custom Duration
Duration controls button press timing in milliseconds. **Default: 25ms (optimal for Nintendo Switch timing)**
```bash
python splat-pp.py img/myimage.png --duration 25
```

Valid range: 20-200ms
- Below 20ms: Risk of missed inputs (USB throttling)
- 25ms: ✅ Recommended (matches Switch polling rate at 60Hz)
- Above 200ms: Too slow, drawing takes very long

### Generate Test Patterns
Useful for calibration and testing:
```bash
python splat-pp.py --test-pattern border      # Border around 320×120 canvas
python splat-pp.py --test-pattern checkerboard
python splat-pp.py --test-pattern stripes
python splat-pp.py --test-pattern cross
```

### Custom Function Name
```bash
python splat-pp.py img/myimage.png --function-name drawMyImage
```

### Debug Output
Show detailed statistics about the image and macro:
```bash
python splat-pp.py img/myimage.png --debug
```

## Deployment to Arduino

### 1. Prepare the Sketch
- Open Arduino IDE
- Copy the contents of `sketch.txt` into a new sketch
- Find the comment: `// PASTE THE drawImage FUNCTION BELOW //`
- Copy your generated `.ino` file contents into that location

### 2. Compile and Upload
- Select Teensy 4.0 as the board
- Compile the sketch
- Press the PROGRAM MODE BUTTON on the Teensy when prompted

**Note**: You may see errors during upload (e.g., "No Teensy boards found"), but the sketch usually uploads successfully if the PROGRAM button was pressed.

### 3. Pair with Switch
- Connect the Teensy to the Switch via USB
- In Splatoon 3, open Plaza Post station
- Force disconnect your current controller (hold pairing button)
- When the "connect controller" screen appears, press the trigger button on the Teensy
- The macro will automatically:
  1. Register the controller
  2. Clear the canvas
  3. Reset to position (0,0)
  4. Draw the image

## Image Requirements

- **Format**: PNG (black and white)
- **Dimensions**: 320×120 pixels (or larger; will be cropped)
- **Colors**: Use pure black (#000000) for pixels to draw, white for empty space
- **File size**: Images are scaled to fit the canvas; larger images will be cropped

## Output Statistics

The script shows:
- **Black pixels to draw**: Total pixels that will be stamped
- **Estimated execution time**: How long the macro will take (in minutes)
- **Debug info** (with `--debug`): Rows, pixel sequences, optimization details

Example:
```
Processing image: becool2.png
Image dimensions: 320x120
Arduino macro saved to: macro/becool2.ino
Function name: drawImage
Black pixels to draw: 15253
Estimated execution time: 31.8 minutes
```

## Troubleshooting

### Issue: Timing warnings appear
**Problem**: Script warns about duration < 20ms or > 200ms
**Solution**: Use 25ms (default) for optimal results

### Issue: Arduino upload fails
**Problem**: "No Teensy boards found" or similar errors
**Solution**: 
- Press PROGRAM MODE BUTTON on Teensy when prompted
- Ensure Teensy drivers are installed
- Try uploading again

### Issue: Macro doesn't execute on Switch
**Problem**: Controller pairs but macro doesn't run
**Solution**:
- Verify controller is properly registered in Switch settings
- Ensure canvas is clear before running macro
- Check that the `.ino` file was correctly inserted into `sketch.txt`

### Issue: Drawing is incomplete or wrong
**Problem**: Only part of the image draws or positions are incorrect
**Solution**:
- Verify image is exactly 320×120 pixels
- Check that image is pure black/white (no gray)
- Try a test pattern first (`--test-pattern border`) to verify positioning

## Hardware Requirements

- **Microcontroller**: Teensy 4.0
- **Arduino IDE**: Latest version with Teensy support
- **Libraries**: NSGamepad (included with Teensy installation)
- **USB Cable**: To connect Teensy to Switch 
