# autoBright
Mobile devices actively control their display brightness by adjusting to ambient light levels.  
For a desktop setting there are (expensive) monitors that have integrated ambient light sensors.  
Even cheap monitors can be controlled via [DDC](https://en.wikipedia.org/wiki/Display_Data_Channel) from any operating system.  
  
This project combines a microcontroller based [USB HID ambient light sensor](https://github.com/MatejKocourek/spark-als) with python based DDC control on Windows.  

```
 Ambient Light ☀️/🪟/☁️/💡
        ↓    ↓    ↓
[ Light Sensor (1250 lux) ]
        ↓   USB   ↓
    [ PC / autoBright ]
        ↓ DDC/CI  ↓
   [ Monitor (72%) 🖥️ ]
```  
  
For Linux there is also a well documented project with the same approach: [xythobuz/AutoBrightness](https://github.com/xythobuz/AutoBrightness)

## Overview

To adjuist the monitor brightness main.py uses:
- Windows Sensor API ([LightSensor](https://learn.microsoft.com/en-us/uwp/api/windows.devices.sensors.lightsensor?view=winrt-26100)) for lux input via ```winsdk```
- Windows DXVA2 DDC/CI APIs for monitor brightness output via ```ctypes```
- a system tray icon with manual offset controls via ```pystray```

Further development/integration:
- add the USB HID light sensor function to [TwinkleTray](https://github.com/xanderfrangos/twinkle-tray) or similar software.

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
Win+R, ```shell:startup```, create shortcut with ```python3.12.exe "path\to\autoBright\main.py"``` (if [path variables](https://superuser.com/questions/1399544/how-to-change-default-python-executable-on-windows-10) are set correctly)  

## Hardware
Reading ambient brightness is done with an ATtiny85 and a BH1750 brightness sensor. See [MatejKocourek/spark-als](https://github.com/MatejKocourek/spark-als).  
  
![hardware](./hardware.png "USB-C ATtiny85 and noname SPI BH1750 board assabmled back to back with power and SPI CLK/SDL connected by wires")  
  
The folder ```housing``` includes a 3D printable enclosure.
