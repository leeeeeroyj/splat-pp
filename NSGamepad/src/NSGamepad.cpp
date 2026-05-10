#include "NSGamepad.h"
#include <string.h>

// NSGadget USB interface (provided by Teensy core patches from dmadison/NSGadget_Teensy)
extern "C" {
  extern void usb_nsgamepad_configure(void);
  extern int usb_nsgamepad_send(void);
  extern uint8_t usb_nsgamepad_data[8];
}

// Report structure matches Nintendo Switch Pro Controller
// Byte layout: [buttons_lo, buttons_hi, hat, lx, ly, rx, ry, unused]
typedef struct __attribute__((packed)) {
  uint16_t buttons;
  uint8_t  hat;
  uint8_t  lx;
  uint8_t  ly;
  uint8_t  rx;
  uint8_t  ry;
  uint8_t  unused;
} NSGamepadReport_t;

void NSGamepad_::begin() {
  // Initialize NSGadget USB layer
  usb_nsgamepad_configure();
  // Clear report
  memset(usb_nsgamepad_data, 0, sizeof(usb_nsgamepad_data));
  usb_nsgamepad_data[2] = 0xF;  // hat/dpad centered
  usb_nsgamepad_data[3] = 128;  // left x centered
  usb_nsgamepad_data[4] = 128;  // left y centered
  usb_nsgamepad_data[5] = 128;  // right x centered
  usb_nsgamepad_data[6] = 128;  // right y centered
  delay(1500);
}

void NSGamepad_::loop() {
  usb_nsgamepad_send();
}

void NSGamepad_::press(uint8_t b) {
  if (b < 16) {
    uint16_t* buttons = (uint16_t*)&usb_nsgamepad_data[0];
    *buttons |= (uint16_t)1 << b;
  }
}

void NSGamepad_::release(uint8_t b) {
  if (b < 16) {
    uint16_t* buttons = (uint16_t*)&usb_nsgamepad_data[0];
    *buttons &= ~((uint16_t)1 << b);
  }
}

void NSGamepad_::releaseAll() {
  uint16_t* buttons = (uint16_t*)&usb_nsgamepad_data[0];
  *buttons = 0;
  usb_nsgamepad_data[2] = 0xF;  // hat centered
}

void NSGamepad_::leftXAxis(uint8_t x) {
  usb_nsgamepad_data[3] = x;
}

void NSGamepad_::leftYAxis(uint8_t y) {
  usb_nsgamepad_data[4] = y;
}

void NSGamepad_::rightXAxis(uint8_t x) {
  usb_nsgamepad_data[5] = x;
}

void NSGamepad_::rightYAxis(uint8_t y) {
  usb_nsgamepad_data[6] = y;
}

void NSGamepad_::dPad(int8_t d) {
  usb_nsgamepad_data[2] = (d < 0 || d > 8) ? 0xF : (uint8_t)d;
}

NSGamepad_ NSGamepad;