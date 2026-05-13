#!/usr/bin/env bash
# setup-nsgadget.sh - NSGadget_Teensy setup for Teensy core 1.60.0
#
# Usage:
#   chmod +x setup-nsgadget.sh
#   ./setup-nsgadget.sh

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; exit 1; }

ARDUINO_DIR="$HOME/Arduino"
CORE_DIR="$ARDUINO_DIR/packages/teensy/hardware/avr/1.60.0"
CORE_T4="$CORE_DIR/cores/teensy4"
LIB_DIR="$ARDUINO_DIR/libraries"
NSGADGET_DIR="$LIB_DIR/NSGadget_Teensy"
TEENSY_URL="https://www.pjrc.com/teensy/package_teensy_index.json"

echo ""
echo "=================================================="
echo "  splat-pp NSGadget Setup (Teensy core 1.60.0)"
echo "=================================================="
echo ""

# ── Preflight: fix invalid backup directory name if present ───────────────────
# arduino-cli rejects version directory names containing a second dot.
STOCK_DOT="$ARDUINO_DIR/packages/teensy/hardware/avr/1.60.0.stock-backup"
STOCK_HYPHEN="$ARDUINO_DIR/packages/teensy/hardware/avr/1.60.0-stock-backup"
if [ -d "$STOCK_DOT" ]; then
    info "Renaming invalid backup directory (dot -> hyphen)..."
    mv "$STOCK_DOT" "$STOCK_HYPHEN"
    success "Renamed to 1.60.0-stock-backup"
fi

# ── Step 1: arduino-cli ───────────────────────────────────────────────────────
info "Step 1: arduino-cli..."
if ! command -v arduino-cli &>/dev/null; then
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
    sudo mv ~/bin/arduino-cli /usr/local/bin/ 2>/dev/null || true
fi
command -v arduino-cli &>/dev/null || error "arduino-cli not found"
success "arduino-cli ready"

# ── Step 2: Configure ─────────────────────────────────────────────────────────
info "Step 2: Configuring arduino-cli..."
arduino-cli config init --overwrite &>/dev/null || true
arduino-cli config set directories.data "$ARDUINO_DIR"
arduino-cli config set directories.user "$ARDUINO_DIR"
arduino-cli config add board_manager.additional_urls "$TEENSY_URL" 2>/dev/null || true
success "configured"

# ── Step 3: Teensy core ───────────────────────────────────────────────────────
info "Step 3: Teensy core 1.60.0..."
arduino-cli core update-index &>/dev/null
arduino-cli core install teensy:avr &>/dev/null
[ -f "$CORE_DIR/boards.txt" ] || error "Core not found at $CORE_DIR"
success "core installed"

# ── Step 4: Clone NSGadget_Teensy ─────────────────────────────────────────────
info "Step 4: NSGadget_Teensy (dmadison fork)..."
mkdir -p "$LIB_DIR"
if [ -d "$NSGADGET_DIR" ]; then
    git -C "$NSGADGET_DIR" pull --quiet 2>/dev/null || true
else
    git clone --quiet https://github.com/dmadison/NSGadget_Teensy "$NSGADGET_DIR"
fi
[ -d "$NSGADGET_DIR" ] || error "Failed to clone NSGadget_Teensy"
success "NSGadget_Teensy ready"

# ── Step 4b: Remove conflicting NSGamepad wrapper library ─────────────────────
# The sketch calls the NSGamepad singleton from the core directly.
# Any separately-installed NSGamepad library shadows it and breaks the build.
if [ -d "$LIB_DIR/NSGamepad" ]; then
    rm -rf "$LIB_DIR/NSGamepad"
    success "Removed conflicting NSGamepad library"
fi

# ── Step 5: Bounce2 ───────────────────────────────────────────────────────────
info "Step 5: Bounce2..."
arduino-cli lib install "Bounce2" &>/dev/null
success "Bounce2 installed"

# ── Step 6: Copy USB descriptor files into Teensy core ───────────────────────
info "Step 6: Copying NSGamepad USB descriptors into Teensy core..."
NSGADGET_CORE="$NSGADGET_DIR/hardware/teensy/avr/cores/teensy4"
for f in usb_nsgamepad.c usb_nsgamepad.h usb_inst.cpp usb_desc.c usb_desc.h; do
    [ -f "$NSGADGET_CORE/$f" ] || error "Missing: $f (not found in $NSGADGET_CORE)"
    cp "$NSGADGET_CORE/$f" "$CORE_T4/$f"
done
success "USB descriptor files copied"

# ── Step 7: boards.txt – surgical patch, preserve gnu++17 ────────────────────
# IMPORTANT: Do NOT replace boards.txt wholesale. The NSGadget boards.txt uses
# gnu++14 which breaks Teensy 1.60.0 core headers that require C++17.
# We append only the three nsgamepad menu lines to the stock file.
info "Step 7: Patching boards.txt (preserving gnu++17)..."
BOARDS="$CORE_DIR/boards.txt"
grep -q "gnu++17" "$BOARDS" || warn "gnu++17 not found in boards.txt"

if ! grep -q "teensy40.menu.usb.nsgamepad" "$BOARDS"; then
cat >> "$BOARDS" << 'EOF'

# ── NS Gamepad USB type – added by setup-nsgadget.sh ─────────────────────────
teensy40.menu.usb.nsgamepad=NS Gamepad
teensy40.menu.usb.nsgamepad.build.usbtype=USB_NSGAMEPAD
teensy40.menu.usb.nsgamepad.fake_serial=teensy_gateway
EOF
    success "boards.txt patched"
else
    success "boards.txt already has nsgamepad entry"
fi

# ── Step 8: usb.c – add missing usb_nsgamepad_configure() call ───────────────
#
# ROOT CAUSE: The Teensy USB stack calls each device's configure function from
# usb.c when the USB host completes enumeration. This opens the HID transmit
# endpoint. Without it, usb_nsgamepad_send() silently returns -1 on every call
# because usb_configuration is never set. The controller enumerates correctly
# (Switch and PC see it as a Hori HoriPAD S) but all HID reports are dropped.
# Every other USB type had this call registered. NSGadget's was never added.
#
info "Step 8: Patching usb.c (adding usb_nsgamepad_configure call)..."
USB_C="$CORE_T4/usb.c"
[ -f "$USB_C" ] || error "usb.c not found at $USB_C"

if ! grep -q "usb_nsgamepad_configure" "$USB_C"; then
    sed -i '/#if defined(JOYSTICK_INTERFACE)/i\\t\t#if defined(NSGAMEPAD_INTERFACE)\n\t\tusb_nsgamepad_configure();\n\t\t#endif' "$USB_C"
    grep -q "usb_nsgamepad_configure" "$USB_C" || error "usb.c patch failed"
    success "usb.c patched"
else
    success "usb.c already patched"
fi

# ── Step 9: Patch WProgram.h ──────────────────────────────────────────────────
info "Step 9: Patching WProgram.h..."
WPROGRAM="$CORE_T4/WProgram.h"
if ! grep -q "usb_nsgamepad.h" "$WPROGRAM"; then
    if grep -q "usb_joystick.h" "$WPROGRAM"; then
        sed -i '/#include "usb_joystick.h"/a #include "usb_nsgamepad.h"' "$WPROGRAM"
    else
        echo '#include "usb_nsgamepad.h"' >> "$WPROGRAM"
    fi
fi
grep -q "usb_nsgamepad.h" "$WPROGRAM" || error "WProgram.h patch failed"
success "WProgram.h patched"

# ── Step 10: Patch Print.cpp ──────────────────────────────────────────────────
info "Step 10: Patching Print.cpp..."
PRINT="$CORE_T4/Print.cpp"
if ! grep -q "USB_NSGAMEPAD" "$PRINT"; then
    sed -i 's/if (file >= 0 && file <= 2) file = (int)\&Serial;/#ifndef USB_NSGAMEPAD\n\tif (file >= 0 \&\& file <= 2) file = (int)\&Serial;\n#endif/' "$PRINT"
fi
success "Print.cpp patched"

# ── Step 11: Patch yield.cpp ──────────────────────────────────────────────────
info "Step 11: Patching yield.cpp..."
YIELD="$CORE_T4/yield.cpp"
if ! grep -q "USB_NSGAMEPAD" "$YIELD"; then
    sed -i 's/if (Serial.available()) serialEvent();/#ifndef USB_NSGAMEPAD\n\t\tif (Serial.available()) serialEvent();\n#endif/' "$YIELD"
fi
success "yield.cpp patched"

# ── Step 12: udev rules ───────────────────────────────────────────────────────
info "Step 12: udev rules..."
if [ ! -f /etc/udev/rules.d/00-teensy.rules ]; then
    wget -q https://www.pjrc.com/teensy/00-teensy.rules -O /tmp/00-teensy.rules
    sudo mv /tmp/00-teensy.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules && sudo udevadm trigger
    warn "Log out/in for udev rules to take effect"
else
    success "udev rules present"
fi

# ── Step 13: teensy_loader_cli ────────────────────────────────────────────────
info "Step 13: teensy_loader_cli..."
if ! command -v teensy_loader_cli &>/dev/null; then
    sudo apt-get install -y teensy-loader-cli &>/dev/null || \
        warn "Install manually: sudo apt-get install teensy-loader-cli"
else
    success "teensy_loader_cli found"
fi

# ── Step 14: Sanity checks ────────────────────────────────────────────────────
info "Step 14: Sanity checks..."
FAIL=0
chk() { eval "$2" &>/dev/null && success "  $1 ✓" || { warn "  $1 FAILED"; FAIL=1; }; }
chk "boards.txt: gnu++17 intact"          "grep -q 'gnu++17' '$BOARDS'"
chk "boards.txt: nsgamepad USB type"      "grep -q 'teensy40.menu.usb.nsgamepad' '$BOARDS'"
chk "core: usb_nsgamepad.h"               "[ -f '$CORE_T4/usb_nsgamepad.h' ]"
chk "core: usb_nsgamepad.c"               "[ -f '$CORE_T4/usb_nsgamepad.c' ]"
chk "core: usb_desc.h has USB_NSGAMEPAD"  "grep -q 'USB_NSGAMEPAD' '$CORE_T4/usb_desc.h'"
chk "core: usb_inst.cpp has NSGamepad"    "grep -q 'NSGamepad' '$CORE_T4/usb_inst.cpp'"
chk "usb.c: nsgamepad_configure call"     "grep -q 'usb_nsgamepad_configure' '$CORE_T4/usb.c'"
chk "WProgram.h: includes nsgamepad"      "grep -q 'usb_nsgamepad.h' '$CORE_T4/WProgram.h'"
chk "NSGamepad library not installed"     "[ ! -d '$LIB_DIR/NSGamepad' ]"

echo ""
[ "$FAIL" -eq 0 ] && \
    echo -e "${GREEN}  All checks passed!${NC}" || \
    echo -e "${YELLOW}  Completed with warnings – review above${NC}"
echo ""
echo "FQBN: teensy:avr:teensy40:usb=nsgamepad"
echo "Run:  python splat-pp.py img/yourimage.png"
echo ""
