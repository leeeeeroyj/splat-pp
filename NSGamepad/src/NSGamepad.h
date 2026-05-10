#pragma once
#include <Arduino.h>

class NSGamepad_ {
public:
  void begin();
  void loop();
  void press(uint8_t button);
  void release(uint8_t button);
  void releaseAll();
  void leftXAxis(uint8_t x);
  void leftYAxis(uint8_t y);
  void rightXAxis(uint8_t x);
  void rightYAxis(uint8_t y);
  void dPad(int8_t dpad);

private:
  void sendReport();
};

extern NSGamepad_ NSGamepad;