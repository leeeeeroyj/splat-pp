# Initial setup
cd 
mkdir -p tools/splat-pp
cd !$

# Create and activate a new conda env
conda create --name splat-pp python=3.11 -y
conda activate splat-pp

pip install numpy pillow

# Basic usage
python splat-pp.py img/myimage.png

# Specify output file and custom duration
python splat-pp.py myimage.png my_drawing.ino --duration 75

# Generate test pattern for calibration
python splat-pp.py --test-pattern checkerboard

# Custom function name and debug info
python splat-pp.py myimage.png --function-name drawSplatoon --debug


python splat-pp.py img/becool2.png --duration 25

Open Arduino IDE
Copy sketch.txt in to the editor.
copy the your file_macro.ino in to the specified area in sketch.txt
Comile and write the sketch to the arduino. I get some errors, but it still works. 

        Opening Teensy Loader...
        Sketch uses 172528 bytes (8%) of program storage space. Maximum is 2031616 bytes.
        Global variables use 205244 bytes (39%) of dynamic memory, leaving 319044 bytes for local variables. Maximum is 524288 bytes.
        No Teensy boards were found on any USB ports of your computer.
        Please press the PROGRAM MODE BUTTON on your Teensy to upload your sketch.
        An error occurred while uploading the sketch

Connect the arduino to the switch.

In Splatoon, open up the Plaza Post station and then force disconnect your controller using the pairing button. 

It should bring up the screen to connect a controller. 

Press the button on the arduino. 

It should show a USB controller connect, close that screen, clear the canvas, reset to position (0,0), and then start the print pattern. 
