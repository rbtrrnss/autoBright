import ctypes
from collections import deque
from math import sqrt
import time
import threading
from ctypes import wintypes
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from winsdk.windows.devices.sensors import LightSensor

PHYSICAL_MONITOR_DESCRIPTION_SIZE = 128
VCP_BRIGHTNESS_CODE = 0x10


class PHYSICAL_MONITOR(ctypes.Structure):
    _fields_ = [
        ("hPhysicalMonitor", wintypes.HANDLE),
        ("szPhysicalMonitorDescription", wintypes.WCHAR * PHYSICAL_MONITOR_DESCRIPTION_SIZE),
    ]


MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(wintypes.RECT),
    wintypes.LPARAM,
)


user32 = ctypes.WinDLL("user32", use_last_error=True)
dxva2 = ctypes.WinDLL("dxva2", use_last_error=True)


offset = 0
running = True
last_lux = 0.0
lock = threading.Lock()

LOOP_INTERVAL_SEC = 1
AVERAGE_WINDOW_SEC = 60
AVERAGE_HISTORY_SIZE = AVERAGE_WINDOW_SEC // LOOP_INTERVAL_SEC


def _raise_last_error(prefix: str) -> None:
    code = ctypes.get_last_error()
    raise OSError(f"{prefix} failed (WinError {code})")


def enum_physical_monitors() -> list[PHYSICAL_MONITOR]:
    hmonitors = []

    @MonitorEnumProc
    def _callback(hmonitor, _hdc, _lprc, _lparam):
        hmonitors.append(hmonitor)
        return True

    if not user32.EnumDisplayMonitors(None, None, _callback, 0):
        _raise_last_error("EnumDisplayMonitors")

    result: list[PHYSICAL_MONITOR] = []
    for hmonitor in hmonitors:
        count = wintypes.DWORD()
        if not dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmonitor, ctypes.byref(count)):
            continue
        if count.value == 0:
            continue

        arr = (PHYSICAL_MONITOR * count.value)()
        if not dxva2.GetPhysicalMonitorsFromHMONITOR(hmonitor, count, arr):
            continue
        result.extend(arr)

    return result


def set_brightness_percent(handle: wintypes.HANDLE, percent: int) -> None:
    percent = max(0, min(100, percent))

    # Prefer direct VCP write; many monitors accept this even when read-back fails.
    if dxva2.SetVCPFeature(handle, wintypes.BYTE(VCP_BRIGHTNESS_CODE), wintypes.DWORD(percent)):
        return

    # Fallback path for monitors that only support high-level brightness API.
    min_b = wintypes.DWORD()
    cur_b = wintypes.DWORD()
    max_b = wintypes.DWORD()
    if not dxva2.GetMonitorBrightness(handle, ctypes.byref(min_b), ctypes.byref(cur_b), ctypes.byref(max_b)):
        _raise_last_error("SetVCPFeature")
    target = int(round(min_b.value + ((max_b.value - min_b.value) * (percent / 100.0))))
    if not dxva2.SetMonitorBrightness(handle, wintypes.DWORD(target)):
        _raise_last_error("SetMonitorBrightness")


def get_brightness_percent(handle: wintypes.HANDLE) -> int:
    # Prefer VCP read (works on many external monitors).
    code_type = wintypes.DWORD()
    cur_v = wintypes.DWORD()
    max_v = wintypes.DWORD()
    if dxva2.GetVCPFeatureAndVCPFeatureReply(
        handle,
        wintypes.BYTE(VCP_BRIGHTNESS_CODE),
        ctypes.byref(code_type),
        ctypes.byref(cur_v),
        ctypes.byref(max_v),
    ):
        if max_v.value > 0:
            return int(round((cur_v.value / max_v.value) * 100))

    # Fallback to high-level brightness API.
    min_b = wintypes.DWORD()
    cur_b = wintypes.DWORD()
    max_b = wintypes.DWORD()
    if not dxva2.GetMonitorBrightness(handle, ctypes.byref(min_b), ctypes.byref(cur_b), ctypes.byref(max_b)):
        _raise_last_error("GetMonitorBrightness")

    span = max_b.value - min_b.value
    if span <= 0:
        return 0
    return int(round(((cur_b.value - min_b.value) / span) * 100))

def brighter(icon, item):
    global offset
    offset += 10

def darker(icon, item):
    global offset
    offset -= 10

def reset(icon, item):
    global offset
    offset = 0

def quit_app(icon, item):
    global running
    running = False
    icon.stop()


def on_reading_changed(sensor, args):
    global last_lux
    reading = args.reading
    if reading:
        with lock:
            last_lux = reading.illuminance_in_lux

def lux_to_brightness(lux):
    # simple mapping (adjust to taste)
    if lux < 10:
        return 5
    if lux < 500:
        #return int(0.0002 * lux**2 + 0.1008 * lux + 0.4014)
        return int(sqrt(lux/500)*100)
    return 100


def make_icon_image(brightness: int) -> Image.Image:
    value = max(0, min(99, int(round(brightness))))
    text = f"{value:02d}"

    img = Image.new("RGB", (128, 128), color=(18, 18, 18))
    draw = ImageDraw.Draw(img)

    on = (245, 245, 245)
    off = (48, 48, 48)

    digit_map = {
        "0": {"a", "b", "c", "d", "e", "f"},
        "1": {"b", "c"},
        "2": {"a", "b", "g", "e", "d"},
        "3": {"a", "b", "g", "c", "d"},
        "4": {"f", "g", "b", "c"},
        "5": {"a", "f", "g", "c", "d"},
        "6": {"a", "f", "g", "e", "c", "d"},
        "7": {"a", "b", "c"},
        "8": {"a", "b", "c", "d", "e", "f", "g"},
        "9": {"a", "b", "c", "d", "f", "g"},
    }

    def draw_digit(x: int, y: int, w: int, h: int, ch: str) -> None:
        t = max(6, w // 7)  # segment thickness
        m = t // 2
        y_mid = y + (h // 2)

        segments = {
            "a": (x + m, y, x + w - m, y + t),
            "d": (x + m, y + h - t, x + w - m, y + h),
            "g": (x + m, y_mid - (t // 2), x + w - m, y_mid + (t // 2)),
            "f": (x, y + m, x + t, y_mid - m),
            "e": (x, y_mid + m, x + t, y + h - m),
            "b": (x + w - t, y + m, x + w, y_mid - m),
            "c": (x + w - t, y_mid + m, x + w, y + h - m),
        }

        enabled = digit_map.get(ch, set())
        for seg, rect in segments.items():
            color = on if seg in enabled else off
            draw.rounded_rectangle(rect, radius=t // 3, fill=color)

    digit_w = 52
    digit_h = 100
    gap = 8
    total_w = (digit_w * 2) + gap
    start_x = (128 - total_w) // 2
    start_y = (128 - digit_h) // 2

    draw_digit(start_x, start_y, digit_w, digit_h, text[0])
    draw_digit(start_x + digit_w + gap, start_y, digit_w, digit_h, text[1])
    return img


sensor = LightSensor.get_default()
if sensor is None:
    raise SystemExit("No light sensor found")

sensor.report_interval = max(sensor.minimum_report_interval, 250)
sensor.add_reading_changed(on_reading_changed)

monitors = enum_physical_monitors()
if not monitors:
    raise SystemExit("No DDC/CI physical monitors found")

print(f"Found {len(monitors)} DDC/CI monitor(s)")

startup_brightness = 50
for mon in monitors:
    try:
        startup_brightness = max(0, min(100, get_brightness_percent(mon.hPhysicalMonitor)))
        break
    except Exception:
        continue

icon_image = make_icon_image(startup_brightness)

menu = pystray.Menu(
    item('Brighter (+10)', brighter),
    item('Darker (-10)', darker),
    item('Reset offset', reset),
    item('Quit', quit_app)
)

icon = pystray.Icon("LuxControl", icon_image, menu=menu)
icon.title = f"LuxControl: {startup_brightness}%"

# Run tray icon in background thread
threading.Thread(target=icon.run, daemon=True).start()

last_icon_brightness = startup_brightness
target_history: deque[int] = deque([startup_brightness] * AVERAGE_HISTORY_SIZE, maxlen=AVERAGE_HISTORY_SIZE)

try:
    while running:
        with lock:
            lux = last_lux

        target_auto = lux_to_brightness(lux)
        target_history.append(target_auto)

        avg_auto = int(round(sum(target_history) / len(target_history)))
        brightness = avg_auto + offset
        brightness = max(0, min(100, brightness))  # clamp to valid range

        for mon in monitors:
            try:
                set_brightness_percent(mon.hPhysicalMonitor, brightness)
            except Exception as exc:
                print(f"Brightness set failed on monitor '{mon.szPhysicalMonitorDescription}': {exc}")

        if brightness != last_icon_brightness:
            icon.icon = make_icon_image(brightness)
            icon.title = f"LuxControl: {brightness}%"
            last_icon_brightness = brightness

        print(
            "Lux:",
            f"{lux:.2f}",
            "-> Target:",
            target_auto,
            "Avg:",
            avg_auto,
            "Out:",
            brightness,
            "(offset:",
            offset,
            ")",
        )
        time.sleep(LOOP_INTERVAL_SEC)
finally:
    count = wintypes.DWORD(len(monitors))
    arr = (PHYSICAL_MONITOR * len(monitors))(*monitors)
    dxva2.DestroyPhysicalMonitors(count, arr)

    