# autoBright
Ambient Light -> Monitor Auto-Brightness (Windows)

## Overview

This project automatically adjusts monitor brightness from ambient light on Windows.

The main app in main.py uses:
- Windows Sensor API (LightSensor) for lux input
- Windows DXVA2 DDC/CI APIs for monitor brightness output
- a system tray icon with manual offset controls

Further development/integration:
- add the USB HID light sensor function to [TwinkleTray](https://github.com/xanderfrangos/twinkle-tray) or similar software.

## Hardware
Reading ambient brightness is done with an ATtiny85 and a BH1750 brightness sensor. See [MatejKocourek/spark-als](https://github.com/MatejKocourek/spark-als).  
  
![hardware](./hardware.png)  
  
The folder ```housing``` includes a 3D printable enclosure.

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

## Autostart on Windows  
Win+R, ```shell:startup```, create shortcut with ```python3.12.exe "path\to\autoBright\main.py"```  
