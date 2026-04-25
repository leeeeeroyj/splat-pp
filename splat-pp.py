#!/usr/bin/env python3
"""
Convert a 320x120 black and white PNG image to Arduino macro code for Splatoon 3 drawing.
Compatible with Teensy 4.0 and NSGadget library setup.
Optimized version with for loops to reduce memory usage.
"""

import sys
import os
import argparse
from PIL import Image
import numpy as np

class PNGToArduinoMacro:
    def __init__(self, duration=25, debug=False):
        """
        Initialize the PNG to Arduino macro converter
        
        Args:
            duration: Duration in milliseconds for button presses and movements (optimal: 25ms for Switch timing)
            debug: Whether to print debug information
        """
        self.duration = duration
        self.debug = debug
        self.max_width = 320
        self.max_height = 120
        
    def convert_image(self, image_path, output_path=None, function_name="drawImage"):
        """
        Convert a PNG image to Arduino macro function
        
        Args:
            image_path: Path to the PNG image
            output_path: Path to save the Arduino code (optional)
            function_name: Name for the generated function
        """
        try:
            # Load and process the image
            img = Image.open(image_path).convert('1')  # Convert to 1-bit B&W
            width, height = img.size
            
            print(f"Processing image: {image_path}")
            print(f"Image dimensions: {width}x{height}")
            
            if width > self.max_width or height > self.max_height:
                print(f"Warning: Image dimensions exceed {self.max_width}x{self.max_height}")
                print("Image will be cropped to fit canvas size")
                
            # Convert to numpy array (0 = black, 1 = white)
            pixels = np.array(img)
            
            # Generate the Arduino function
            arduino_code = self._generate_arduino_function(pixels, width, height, function_name)
            
            # Determine output path (default to macro/ directory)
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = "macro"
                # Ensure output directory exists
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{base_name}.ino")
            
            # Ensure output directory exists for arbitrary output_path
            out_dir = os.path.dirname(output_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            # Write to file
            with open(output_path, 'w') as f:
                f.write(arduino_code)
            
            # Calculate statistics
            black_pixels = np.sum(pixels == 0)
            estimated_time = self._estimate_execution_time(pixels, width, height)
            
            print(f"Arduino macro saved to: {output_path}")
            print(f"Function name: {function_name}")
            print(f"Black pixels to draw: {black_pixels}")
            print(f"Estimated execution time: {estimated_time:.1f} minutes")
            
            if self.debug:
                self._print_debug_info(pixels, width, height)
                
            return True
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return False
    
    def _generate_arduino_function(self, pixels, width, height, function_name):
        """Generate the complete Arduino function code with optimized for loops"""
        
        # Function header and documentation
        code = f"""// Auto-generated macro function for drawing image
// Canvas size: {min(width, self.max_width)}x{min(height, self.max_height)}
// Duration: {self.duration}ms per action

void {function_name}(unsigned int duration = {self.duration}) {{
"""
        
        # Generate optimized drawing commands
        drawing_commands = self._generate_optimized_pattern(pixels, width, height)
        
        # Add the drawing commands to the function
        for command in drawing_commands:
            code += f"  {command}\n"
        
        # Close the function
        code += "}\n"
        
        return code
    
    def _generate_optimized_pattern(self, pixels, width, height):
        """Generate optimized drawing commands - only visit and draw black pixels
        
        Algorithm:
        1. Identify all drawable rows (rows with at least one black pixel)
        2. Alternate direction between drawable rows (L->R, R->L, L->R...)
        3. For each row, move to first black pixel, draw consecutive pixels, skip white gaps
        4. Move directly to next drawable row (skip entirely empty rows)
        """
        commands = []
        
        # Find all drawable rows with their black pixel positions
        drawable_rows = []
        for row in range(min(height, self.max_height)):
            black_positions = [col for col in range(min(width, self.max_width))
                             if pixels[row, col] == 0]
            if black_positions:
                drawable_rows.append((row, black_positions))
        
        if not drawable_rows:
            commands.append("// No black pixels found in image")
            return commands
        
        # Track current cursor position
        current_row = 0
        current_col = 0
        
        for draw_idx, (row, black_positions) in enumerate(drawable_rows):
            # Determine direction based on drawable row index (alternating L->R, R->L)
            left_to_right = (draw_idx % 2 == 0)
            
            if self.debug:
                direction = "left-to-right" if left_to_right else "right-to-left"
                commands.append(f"// Row {row} (drawable row {draw_idx}): {direction} - {len(black_positions)} pixels")
            
            # Sort positions based on direction
            if not left_to_right:
                black_positions.reverse()
            
            # Move to this row
            if draw_idx == 0:
                # Initial positioning: move down to first drawable row
                if row > 0:
                    if row == 1:
                        commands.append("setDPad(DPAD_DOWN, duration);")
                    else:
                        commands.append(f"for(int i = 0; i < {row}; i++) setDPad(DPAD_DOWN, duration);")
                current_row = row
            else:
                # Move down from previous drawable row to this row (skip empty rows)
                prev_row = drawable_rows[draw_idx - 1][0]
                row_diff = row - prev_row
                if row_diff == 1:
                    commands.append("setDPad(DPAD_DOWN, duration);")
                else:
                    commands.append(f"for(int i = 0; i < {row_diff}; i++) setDPad(DPAD_DOWN, duration);")
                current_row = row
            
            # Move to first black pixel in this row
            first_pixel_col = black_positions[0]
            if first_pixel_col != current_col:
                col_diff = first_pixel_col - current_col
                if col_diff > 0:  # Move right
                    if col_diff == 1:
                        commands.append("setDPad(DPAD_RIGHT, duration);")
                    else:
                        commands.append(f"for(int i = 0; i < {col_diff}; i++) setDPad(DPAD_RIGHT, duration);")
                else:  # Move left
                    col_diff = abs(col_diff)
                    if col_diff == 1:
                        commands.append("setDPad(DPAD_LEFT, duration);")
                    else:
                        commands.append(f"for(int i = 0; i < {col_diff}; i++) setDPad(DPAD_LEFT, duration);")
            current_col = first_pixel_col
            
            # Draw all black pixels in this row
            i = 0
            while i < len(black_positions):
                # Find consecutive sequence of black pixels
                sequence_start = i
                sequence_end = i
                
                while (sequence_end + 1 < len(black_positions) and 
                       black_positions[sequence_end + 1] == black_positions[sequence_end] + 1):
                    sequence_end += 1
                
                sequence_length = sequence_end - sequence_start + 1
                
                if sequence_length == 1:
                    # Single pixel
                    commands.append("pressButton(BUTTON_A_INDEX, duration, duration);")
                else:
                    # Multiple consecutive pixels - use for loop
                    commands.append(f"for(int i = 0; i < {sequence_length}; i++) {{")
                    commands.append("  pressButton(BUTTON_A_INDEX, duration, duration);")
                    commands.append("  if(i < " + str(sequence_length - 1) + ") setDPad(" + 
                                  ("DPAD_RIGHT" if left_to_right else "DPAD_LEFT") + ", duration);")
                    commands.append("}")
                
                current_col = black_positions[sequence_end]
                
                # Move to next sequence if there is one
                if sequence_end + 1 < len(black_positions):
                    next_pos = black_positions[sequence_end + 1]
                    col_diff = next_pos - current_col
                    
                    if col_diff > 0:  # Move right
                        if col_diff == 1:
                            commands.append("setDPad(DPAD_RIGHT, duration);")
                        else:
                            commands.append(f"for(int i = 0; i < {col_diff}; i++) setDPad(DPAD_RIGHT, duration);")
                    elif col_diff < 0:  # Move left
                        col_diff = abs(col_diff)
                        if col_diff == 1:
                            commands.append("setDPad(DPAD_LEFT, duration);")
                        else:
                            commands.append(f"for(int i = 0; i < {col_diff}; i++) setDPad(DPAD_LEFT, duration);")
                    
                    current_col = next_pos
                
                i = sequence_end + 1
        
        return commands
    
    def _estimate_execution_time(self, pixels, width, height):
        """Estimate the total execution time in minutes
        
        Accounts for:
        - Black pixel drawing time (press + release per pixel)
        - D-Pad movement overhead
        - Only drawable rows (skips empty rows)
        - Real-world overhead buffer
        """
        # Count black pixels
        black_pixels = np.sum(pixels == 0)
        
        # Find all drawable rows
        drawable_rows = []
        for row in range(min(height, self.max_height)):
            if np.any(pixels[row, :min(width, self.max_width)] == 0):
                drawable_rows.append(row)
        
        # Drawing time: each black pixel takes 2 duration periods (press + release)
        pixel_time = black_pixels * (self.duration * 2) / 1000.0  # Convert ms to seconds
        
        # Movement time: estimate D-Pad movements
        movement_count = 0
        
        # Initial positioning to first drawable row
        if drawable_rows:
            movement_count += drawable_rows[0]  # Down movements to first row
            
            # For each drawable row, estimate movements
            for idx, row in enumerate(drawable_rows):
                black_positions = [col for col in range(min(width, self.max_width))
                                 if pixels[row, col] == 0]
                
                if black_positions:
                    # Horizontal movement to first pixel
                    movement_count += black_positions[0]  # Conservative estimate
                    
                    # Movements within row (between black pixels)
                    for i in range(len(black_positions) - 1):
                        gap = black_positions[i + 1] - black_positions[i]
                        movement_count += max(1, gap - 1)  # Gap between consecutive black pixels
                    
                    # Movement to next drawable row
                    if idx < len(drawable_rows) - 1:
                        next_row = drawable_rows[idx + 1]
                        movement_count += (next_row - row)
        
        movement_time = movement_count * (self.duration / 1000.0)
        
        # Add 15% safety buffer for real-world overhead and USB timing uncertainties
        total_time = (pixel_time + movement_time) * 1.15
        
        return total_time / 60  # Return in minutes
    
    def _print_debug_info(self, pixels, width, height):
        """Print debug information about the image"""
        print(f"\nDEBUG INFO:")
        print(f"Total pixels: {width * height}")
        print(f"Black pixels: {np.sum(pixels == 0)}")
        print(f"White pixels: {np.sum(pixels == 1)}")
        
        # Count non-empty rows
        non_empty_rows = 0
        max_consecutive = 0
        total_sequences = 0
        
        for row in range(min(height, self.max_height)):
            row_has_black = False
            consecutive_count = 0
            current_consecutive = 0
            
            for col in range(min(width, self.max_width)):
                if pixels[row, col] == 0:
                    row_has_black = True
                    current_consecutive += 1
                else:
                    if current_consecutive > 0:
                        consecutive_count = max(consecutive_count, current_consecutive)
                        max_consecutive = max(max_consecutive, current_consecutive)
                        total_sequences += 1
                        current_consecutive = 0
            
            # Handle case where row ends with black pixels
            if current_consecutive > 0:
                consecutive_count = max(consecutive_count, current_consecutive)
                max_consecutive = max(max_consecutive, current_consecutive)
                total_sequences += 1
            
            if row_has_black:
                non_empty_rows += 1
        
        print(f"Rows with black pixels: {non_empty_rows}/{min(height, self.max_height)}")
        print(f"Longest consecutive sequence: {max_consecutive} pixels")
        print(f"Total pixel sequences: {total_sequences}")
        print(f"Average sequence length: {np.sum(pixels == 0) / max(1, total_sequences):.1f}")
    
    def generate_test_pattern(self, pattern_type, output_path=None):
        """Generate a test pattern and convert it to Arduino macro"""
        
        # Create test pattern
        pixels = np.ones((self.max_height, self.max_width), dtype=np.uint8)  # White background
        
        if pattern_type == "checkerboard":
            # Create checkerboard pattern
            for row in range(self.max_height):
                for col in range(self.max_width):
                    if (row + col) % 2 == 0:
                        pixels[row, col] = 0  # Black
        
        elif pattern_type == "stripes":
            # Create horizontal stripes
            for row in range(self.max_height):
                if row % 4 < 2:  # Every 4 rows, make 2 black
                    pixels[row, :] = 0
        
        elif pattern_type == "border":
            # Create border - perfect test for for loop optimization
            pixels[0, :] = 0  # Top
            pixels[-1, :] = 0  # Bottom
            pixels[:, 0] = 0  # Left
            pixels[:, -1] = 0  # Right
        
        elif pattern_type == "cross":
            # Create cross pattern
            mid_row = self.max_height // 2
            mid_col = self.max_width // 2
            pixels[mid_row, :] = 0  # Horizontal line
            pixels[:, mid_col] = 0  # Vertical line
        
        # Save test pattern as PNG
        test_img = Image.fromarray((pixels * 255).astype(np.uint8))
        png_path = f"test_{pattern_type}.png"
        test_img.save(png_path)
        print(f"Generated test pattern: {png_path}")
        
        # Convert to Arduino macro (default to macro/ directory without `_macro` suffix)
        if output_path is None:
            output_dir = "macro"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"test_{pattern_type}.ino")

        # Temporarily create the image file and process it
        self.convert_image(png_path, output_path, f"draw{pattern_type.capitalize()}")
        
        return True

def main():
    parser = argparse.ArgumentParser(
        description='Convert 320x120 black and white PNG to Arduino macro for Splatoon 3'
    )
    
    parser.add_argument('input_image', nargs='?', help='Path to input PNG image')
    parser.add_argument('output_file', nargs='?', help='Path to output Arduino file (.ino)')
    parser.add_argument('--duration', type=int, default=25,
                       help='Duration in milliseconds for button presses (default: 25ms - optimal for Switch timing)')
    parser.add_argument('--function-name', default='drawImage',
                       help='Name for the generated Arduino function (default: drawImage)')
    parser.add_argument('--debug', action='store_true',
                       help='Print debug information')
    parser.add_argument('--test-pattern', 
                       choices=['checkerboard', 'stripes', 'border', 'cross'],
                       help='Generate a test pattern instead of processing input image')
    
    args = parser.parse_args()
    
    # Validate duration range (outside 20-200ms risks USB/Switch timing issues)
    if args.duration < 20:
        print(f"Warning: Duration {args.duration}ms is below 20ms (optimal range is 20-200ms)")
        print("         Timing below 20ms may cause missed inputs on Switch due to USB throttling")
    elif args.duration > 200:
        print(f"Warning: Duration {args.duration}ms is above 200ms (optimal range is 20-200ms)")
        print("         Timing above 200ms will be very slow for drawing")
    
    # Create converter
    converter = PNGToArduinoMacro(duration=args.duration, debug=args.debug)
    
    if args.test_pattern:
        # Generate test pattern (default to macro/ directory)
        if args.output_file:
            output_file = args.output_file
        else:
            output_dir = "macro"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"test_{args.test_pattern}.ino")
        converter.generate_test_pattern(args.test_pattern, output_file)
    elif args.input_image:
        # Process input image
        if not os.path.exists(args.input_image):
            print(f"Error: Input image '{args.input_image}' not found")
            return 1
        
        converter.convert_image(args.input_image, args.output_file, args.function_name)
    else:
        # Show usage
        print("Usage examples:")
        print("  python splat-pp.py image.png")
        print("  python splat-pp.py image.png output_macro.ino")
        print("  python splat-pp.py --test-pattern border")
        print("  python splat-pp.py image.png --duration 100 --function-name drawMyImage")
        print("\nRun with --help for more options")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())