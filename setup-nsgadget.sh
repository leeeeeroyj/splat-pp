#!/usr/bin/env bash
# setup-nsgadget.sh - Complete NSGadget_Teensy 1.60.0 setup
# Patches Teensy core with NSGadget USB descriptors to appear as Hori controller
#
# Usage:
#   chmod +x setup-nsgadget.sh
#   ./setup-nsgadget.sh

set -e

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; exit 1; }

ARDUINO_DIR="$HOME/Arduino"
CORE_DIR="$ARDUINO_DIR/packages/teensy/hardware/avr/1.60.0"
CORE_TEENSY4="$CORE_DIR/cores/teensy4"
LIB_DIR="$ARDUINO_DIR/libraries"
NSGADGET_DIR="$LIB_DIR/NSGadget_Teensy"
TEENSY_URL="https://www.pjrc.com/teensy/package_teensy_index.json"

echo ""
echo "=================================================="
echo "  NSGadget Teensy 4.0 Environment Setup"
echo "=================================================="
echo ""

# ─── Step 1: arduino-cli ──────────────────────────────────────────────────────
info "Step 1: Checking arduino-cli..."
if ! command -v arduino-cli &>/dev/null; then
    info "Installing arduino-cli..."
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
    sudo mv ~/bin/arduino-cli /usr/local/bin/ 2>/dev/null || true
    command -v arduino-cli &>/dev/null || error "arduino-cli install failed"
fi
success "arduino-cli ready"

# ─── Step 2: Configure arduino-cli ───────────────────────────────────────────
info "Step 2: Configuring arduino-cli..."
arduino-cli config init --overwrite &>/dev/null || true
arduino-cli config set directories.data "$ARDUINO_DIR"
arduino-cli config set directories.user "$ARDUINO_DIR"
arduino-cli config add board_manager.additional_urls "$TEENSY_URL" 2>/dev/null || true
success "arduino-cli configured"

# ─── Step 3: Teensy core ─────────────────────────────────────────────────────
info "Step 3: Installing Teensy core 1.60.0..."
arduino-cli core update-index &>/dev/null
arduino-cli core install teensy:avr &>/dev/null
if [ ! -f "$CORE_DIR/boards.txt" ]; then
    error "Teensy core not found at $CORE_DIR"
fi
success "Teensy core 1.60.0 installed"

# Step 4: Backup stock core
# SKIP THIS

# Step 5: Clone NSGadget_Teensy
info "Step 5: Installing NSGadget_Teensy (dmadison fork)..."
mkdir -p "$LIB_DIR"
if [ -d "$NSGADGET_DIR" ]; then
    info "NSGadget_Teensy exists, pulling latest..."
    git -C "$NSGADGET_DIR" pull --quiet 2>/dev/null || true
else
    git clone --quiet https://github.com/dmadison/NSGadget_Teensy "$NSGADGET_DIR"
fi
[ -d "$NSGADGET_DIR" ] || error "Failed to install NSGadget_Teensy"
success "NSGadget_Teensy ready"

# Also copy our custom NSGamepad library
info "Step 5b: Installing local NSGamepad library..."
if [ -d "NSGamepad" ]; then
    cp -rf NSGamepad "$LIB_DIR/NSGamepad"
    success "NSGamepad library installed to $LIB_DIR/NSGamepad"
else
    warn "Local NSGamepad not found, skipping"
fi

# Step 6: Install Bounce2
info "Step 6: Installing Bounce2..."
arduino-cli lib install "Bounce2" &>/dev/null
success "Bounce2 installed"

# Step 7: Patch boards.txt with NSGadget USB option
info "Step 7: Patching boards.txt..."
if [ -f "$NSGADGET_DIR/hardware/teensy/avr/boards.txt" ]; then
    cp "$NSGADGET_DIR/hardware/teensy/avr/boards.txt" "$CORE_DIR/boards.txt"
    # Fix TEENSYDUINO version to 160
    sed -i 's/TEENSYDUINO=[0-9]*/TEENSYDUINO=160/g' "$CORE_DIR/boards.txt"
    grep -q "teensy40.menu.usb.nsgamepad" "$CORE_DIR/boards.txt" || \
        error "NSGamepad USB option not found in boards.txt"
    success "boards.txt patched"
else
    error "NSGadget boards.txt not found at $NSGADGET_DIR/hardware/teensy/avr/boards.txt"
fi

# Step 8: Copy NSGamepad USB core files
info "Step 8: Copying NSGamepad USB descriptors..."
NSGADGET_CORE="$NSGADGET_DIR/hardware/teensy/avr/cores/teensy4"
for f in usb_nsgamepad.c usb_nsgamepad.h usb_inst.cpp usb_desc.c usb_desc.h; do
    SRC="$NSGADGET_CORE/$f"
    if [ ! -f "$SRC" ]; then
        error "Missing: $f (not found in NSGadget repo)"
    fi
    cp "$SRC" "$CORE_TEENSY4/$f"
done
success "USB descriptors copied"

# Step 9: Patch WProgram.h
info "Step 9: Patching WProgram.h..."
WPROGRAM="$CORE_TEENSY4/WProgram.h"
if ! grep -q "usb_nsgamepad.h" "$WPROGRAM"; then
    sed -i '/#include "usb_joystick.h"/a #include "usb_nsgamepad.h"' "$WPROGRAM"
fi
grep -q "usb_nsgamepad.h" "$WPROGRAM" || error "WProgram.h patch failed"
success "WProgram.h patched"

# Step 10: Patch Print.cpp
info "Step 10: Patching Print.cpp..."
PRINT_CPP="$CORE_TEENSY4/Print.cpp"
if ! grep -q "USB_NSGAMEPAD" "$PRINT_CPP"; then
    sed -i 's/if (file >= 0 && file <= 2) file = (int)\&Serial;/#ifndef USB_NSGAMEPAD\n\tif (file >= 0 \&\& file <= 2) file = (int)\&Serial;\n#endif/' "$PRINT_CPP"
fi
success "Print.cpp patched"

# Step 11: Patch yield.cpp
info "Step 11: Patching yield.cpp..."
YIELD_CPP="$CORE_TEENSY4/yield.cpp"
if ! grep -q "USB_NSGAMEPAD" "$YIELD_CPP"; then
    sed -i 's/if (Serial.available()) serialEvent();/#ifndef USB_NSGAMEPAD\n\t\tif (Serial.available()) serialEvent();\n#endif/' "$YIELD_CPP"
fi
success "yield.cpp patched"

# Step 12: udev rules
info "Step 12: Checking Teensy udev rules..."
if [ ! -f /etc/udev/rules.d/00-teensy.rules ]; then
    warn "Installing udev rules..."
    wget -q https://www.pjrc.com/teensy/00-teensy.rules -O /tmp/00-teensy.rules
    sudo mv /tmp/00-teensy.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    warn "Log out and back in for udev rules to take effect"
else
    success "udev rules already installed"
fi

# Step 13: teensy_loader_cli
info "Step 13: Checking teensy_loader_cli..."
if ! command -v teensy_loader_cli &>/dev/null; then
    warn "teensy_loader_cli not found, installing..."
    sudo apt-get install -y teensy-loader-cli &>/dev/null || \
        warn "Could not auto-install. Install manually: sudo apt-get install teensy-loader-cli"
else
    success "teensy_loader_cli found"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}  Setup complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Test compile: python splat-pp.py img/test.png"
echo "  2. Press button on Teensy when prompted"
echo ""
