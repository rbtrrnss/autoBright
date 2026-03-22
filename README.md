# autoBright

Small starter project for automatic monitor brightness control based on an external USB HID ambient light sensor.

Current contents:
- `i2ctest.py`: one-shot HID polling and report decode test.
- `i2ctest_bar.py`: live lux meter with a 20-character bar display.

Goal:
- add a Windows host component that reads lux and controls monitor brightness.
