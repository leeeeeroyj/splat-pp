#!/usr/bin/env bash
# setup-nsgadget.sh
# Sets up arduino-cli + NSGadget_Teensy for Teensy 4.0 on Ubuntu/Debian
# Tested with Teensy core 1.60.0 and dmadison/NSGadget_Teensy fork
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

# ─── Paths ────────────────────────────────────────────────────────────────────
ARDUINO_DIR="$HOME/Arduino"
CORE_DIR="$ARDUINO_DIR/packages/teensy/hardware/avr/1.60.0"
CORE_TEENSY4="$CORE_DIR/cores/teensy4"
LIB_DIR="$ARDUINO_DIR/libraries"
NSGADGET_DIR="$LIB_DIR/NSGadget_Teensy"
NSGADGET_CORE="$NSGADGET_DIR/hardware/teensy/avr/cores/teensy4"
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
    command -v arduino-cli &>/dev/null || error "arduino-cli install failed. Add it to PATH manually."
fi
success "arduino-cli $(arduino-cli version | grep -oP 'Version: \K[^\s]+')"

# ─── Step 2: Configure arduino-cli ───────────────────────────────────────────
info "Step 2: Configuring arduino-cli..."
arduino-cli config init --overwrite &>/dev/null || true
arduino-cli config set directories.data "$ARDUINO_DIR"
arduino-cli config set directories.user "$ARDUINO_DIR"
arduino-cli config set directories.downloads "$ARDUINO_DIR/staging"
arduino-cli config add board_manager.additional_urls "$TEENSY_URL" 2>/dev/null || \
    arduino-cli config set board_manager.additional_urls "[$TEENSY_URL]" 2>/dev/null || true
success "arduino-cli configured → $ARDUINO_DIR"

# ─── Step 3: Teensy core ─────────────────────────────────────────────────────
info "Step 3: Installing Teensy core 1.60.0..."
arduino-cli core update-index &>/dev/null
arduino-cli core install teensy:avr &>/dev/null
if [ ! -f "$CORE_DIR/boards.txt" ]; then
    error "Teensy core not found at $CORE_DIR"
fi
success "Teensy core 1.60.0 installed"

# ─── Step 4: Backup stock core ───────────────────────────────────────────────
BACKUP_DIR="$ARDUINO_DIR/packages/teensy/hardware/avr/1.60.0.stock"
if [ ! -d "$BACKUP_DIR" ]; then
    info "Step 4: Backing up stock core..."
    cp -r "$CORE_DIR" "$BACKUP_DIR"
    success "Backup saved → $BACKUP_DIR"
else
    success "Step 4: Stock backup already exists, skipping"
fi

# ─── Step 5: NSGadget_Teensy library ─────────────────────────────────────────
info "Step 5: Installing NSGadget_Teensy (dmadison fork)..."
mkdir -p "$LIB_DIR"
if [ -d "$NSGADGET_DIR" ]; then
    warn "NSGadget_Teensy already exists, pulling latest..."
    git -C "$NSGADGET_DIR" pull --quiet
else
    git clone --quiet https://github.com/dmadison/NSGadget_Teensy "$NSGADGET_DIR"
fi
if [ ! -f "$NSGADGET_DIR/library.properties" ]; then
    cat > "$NSGADGET_DIR/library.properties" << 'EOF'
name=NSGadget_Teensy
version=1.0.0
author=gdsports,dmadison
maintainer=dmadison
sentence=Nintendo Switch Gamepad for Teensy
paragraph=Emulate a Nintendo Switch Pro Controller via USB HID
category=Communication
url=https://github.com/dmadison/NSGadget_Teensy
architectures=*
EOF
fi
success "NSGadget_Teensy installed → $NSGADGET_DIR"

# ─── Step 6: Install Bounce2 ─────────────────────────────────────────────────
info "Step 6: Installing Bounce2..."
arduino-cli lib install "Bounce2" &>/dev/null
success "Bounce2 installed"

# ─── Step 7: Patch boards.txt ────────────────────────────────────────────────
info "Step 7: Patching boards.txt..."

# Replace with NSGadget version (adds usb=nsgamepad option)
cp "$NSGADGET_DIR/hardware/teensy/avr/boards.txt" "$CORE_DIR/boards.txt"

# Fix TEENSYDUINO version (NSGadget ships 1.53/1.56, we need 1.60)
sed -i 's/teensy40\.build\.flags\.defs=-D__IMXRT1062__ -DTEENSYDUINO=[0-9]*/teensy40.build.flags.defs=-D__IMXRT1062__ -DTEENSYDUINO=160/' \
    "$CORE_DIR/boards.txt"

# Fix C++ standard (1.60.0 core needs C++17)
sed -i 's/teensy40\.build\.flags\.cpp=-std=gnu++14/teensy40.build.flags.cpp=-std=gnu++17/' \
    "$CORE_DIR/boards.txt"

# Verify
grep -q "teensy40.menu.usb.nsgamepad=NS Gamepad" "$CORE_DIR/boards.txt" || \
    error "NSGamepad USB option missing from boards.txt"
grep -q "TEENSYDUINO=160" "$CORE_DIR/boards.txt" || \
    error "TEENSYDUINO version fix failed"
grep -q "gnu++17" "$CORE_DIR/boards.txt" || \
    error "C++17 fix failed"
success "boards.txt patched"

# ─── Step 8: Copy NSGamepad USB core files ───────────────────────────────────
info "Step 8: Copying NSGamepad USB core files..."
for f in usb_nsgamepad.c usb_nsgamepad.h usb_inst.cpp usb_desc.c usb_desc.h; do
    if [ ! -f "$NSGADGET_CORE/$f" ]; then
        error "Missing file in NSGadget repo: $NSGADGET_CORE/$f"
    fi
    cp "$NSGADGET_CORE/$f" "$CORE_TEENSY4/$f"
done
success "NSGamepad core files copied"

# ─── Step 9: Patch WProgram.h ────────────────────────────────────────────────
info "Step 9: Patching WProgram.h..."
WPROGRAM="$CORE_TEENSY4/WProgram.h"
if ! grep -q "usb_nsgamepad.h" "$WPROGRAM"; then
    sed -i 's/#include "usb_joystick.h"/#include "usb_joystick.h"\n#include "usb_nsgamepad.h"/' "$WPROGRAM"
fi
grep -q "usb_nsgamepad.h" "$WPROGRAM" || error "WProgram.h patch failed"
success "WProgram.h patched"

# ─── Step 10: Patch Print.cpp ────────────────────────────────────────────────
info "Step 10: Patching Print.cpp..."
python3 - << 'PYEOF'
import sys
path = __import__('os').path.expanduser(
    '~/Arduino/packages/teensy/hardware/avr/1.60.0/cores/teensy4/Print.cpp')
with open(path) as f:
    content = f.read()
old = '\tif (file >= 0 && file <= 2) file = (int)&Serial;'
new = '#ifndef USB_NSGAMEPAD\n\tif (file >= 0 && file <= 2) file = (int)&Serial;\n#endif'
if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print('patched')
elif '#ifndef USB_NSGAMEPAD' in content:
    print('already patched')
else:
    print('ERROR: could not find target line', file=sys.stderr)
    sys.exit(1)
PYEOF
success "Print.cpp patched"

# ─── Step 11: Patch yield.cpp ────────────────────────────────────────────────
info "Step 11: Patching yield.cpp..."
python3 - << 'PYEOF'
import sys
path = __import__('os').path.expanduser(
    '~/Arduino/packages/teensy/hardware/avr/1.60.0/cores/teensy4/yield.cpp')
with open(path) as f:
    content = f.read()
old = '\t\tif (Serial.available()) serialEvent();'
new = '#ifndef USB_NSGAMEPAD\n\t\tif (Serial.available()) serialEvent();\n#endif'
if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print('patched')
elif '#ifndef USB_NSGAMEPAD' in content:
    print('already patched')
else:
    print('ERROR: could not find target line', file=sys.stderr)
    sys.exit(1)
PYEOF
success "yield.cpp patched"

# ─── Step 12: udev rules ─────────────────────────────────────────────────────
info "Step 12: Checking Teensy udev rules..."
if [ ! -f /etc/udev/rules.d/00-teensy.rules ]; then
    warn "Teensy udev rules not found. Installing..."
    wget -q https://www.pjrc.com/teensy/00-teensy.rules -O /tmp/00-teensy.rules
    sudo mv /tmp/00-teensy.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    warn "Log out and back in (or reboot) for udev rules to take effect"
else
    success "Teensy udev rules already installed"
fi

# ─── Step 13: teensy_loader_cli ──────────────────────────────────────────────
info "Step 13: Checking teensy_loader_cli..."
if ! command -v teensy_loader_cli &>/dev/null; then
    warn "teensy_loader_cli not found. Installing..."
    sudo apt-get install -y teensy-loader-cli &>/dev/null || \
        warn "Could not install teensy-loader-cli via apt. Install manually."
else
    success "teensy_loader_cli found"
fi

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================="
echo -e "${GREEN}  Setup complete!${NC}"
echo "=================================================="
echo ""
echo "Compile a sketch:"
echo "  arduino-cli compile \\"
echo "    --fqbn \"teensy:avr:teensy40:usb=nsgamepad\" \\"
echo "    --build-path /tmp/teensy_build \\"
echo "    /path/to/your/sketch"
echo ""
echo "Upload (press button on Teensy first):"
echo "  teensy_loader_cli --mcu=TEENSY40 -w -v /tmp/teensy_build/sketch.ino.hex"
echo ""
echo "Your sketch must include:"
echo "  #include <usb_nsgamepad.h>   // NOT <NSGamepad.h>"
echo "  #include <Bounce2.h>"
echo ""
