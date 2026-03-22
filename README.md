# autoBright
Ambient Light -> Monitor Auto-Brightness (Windows)

## Overview

This project automatically adjusts monitor brightness from ambient light on Windows.

The main app in main.py uses:
- Windows Sensor API (LightSensor) for lux input
- Windows DXVA2 DDC/CI APIs for monitor brightness output
- a system tray icon with manual offset controls

## Hardware
Reading ambient brightness is done with an ATTiny85 and a BH1750 brightness sensor. See [MatejKocourek/spark-als](https://github.com/MatejKocourek/spark-als).

## Dependencies

Dependencies for main.py:
- python 3.12
- winsdk
- pystray
- Pillow

Install required packages:

```
pip install pystray pillow winsdk
```

If you use conda environment usbhid:

```
conda activate usbhid
python -m pip install pystray pillow winsdk
```


