import ctypes
import time
from ctypes import wintypes


PHYSICAL_MONITOR_DESCRIPTION_SIZE = 128


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

VCP_BRIGHTNESS_CODE = 0x10


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


def get_brightness(handle: wintypes.HANDLE) -> tuple[int, int, int]:
    min_b = wintypes.DWORD()
    cur_b = wintypes.DWORD()
    max_b = wintypes.DWORD()
    if not dxva2.GetMonitorBrightness(handle, ctypes.byref(min_b), ctypes.byref(cur_b), ctypes.byref(max_b)):
        # Some monitors reject GetMonitorBrightness but still support raw VCP code 0x10.
        return get_brightness_vcp(handle)
    return min_b.value, cur_b.value, max_b.value


def get_brightness_vcp(handle: wintypes.HANDLE) -> tuple[int, int, int]:
    code_type = wintypes.DWORD()
    cur_v = wintypes.DWORD()
    max_v = wintypes.DWORD()
    if not dxva2.GetVCPFeatureAndVCPFeatureReply(
        handle,
        wintypes.BYTE(VCP_BRIGHTNESS_CODE),
        ctypes.byref(code_type),
        ctypes.byref(cur_v),
        ctypes.byref(max_v),
    ):
        _raise_last_error("GetVCPFeatureAndVCPFeatureReply")
    return 0, cur_v.value, max_v.value


def try_get_brightness(handle: wintypes.HANDLE) -> int | None:
    try:
        _min_b, cur_b, _max_b = get_brightness(handle)
        return cur_b
    except Exception:
        return None


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


def main() -> None:
    levels = [20, 60]
    idx = 0

    monitors = enum_physical_monitors()
    if not monitors:
        raise SystemExit("No DDC/CI physical monitors found")

    print(f"Found {len(monitors)} DDC/CI monitor(s):")
    for i, mon in enumerate(monitors):
        print(f"  [{i}] {mon.szPhysicalMonitorDescription}")

    print("Starting brightness toggle test (20% <-> 50% every 5 seconds).")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            level = levels[idx]
            for i, mon in enumerate(monitors):
                try:
                    cur_b = try_get_brightness(mon.hPhysicalMonitor)
                    set_brightness_percent(mon.hPhysicalMonitor, level)
                    time.sleep(0.3)
                    cur2 = try_get_brightness(mon.hPhysicalMonitor)
                    before_s = "n/a" if cur_b is None else str(cur_b)
                    after_s = "n/a" if cur2 is None else str(cur2)
                    print(f"monitor[{i}]: requested={level}% raw_before={before_s} raw_after={after_s}")
                except Exception as exc:
                    print(f"monitor[{i}]: failed ({exc})")

            idx = 1 - idx
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopped brightness toggle test.")
    finally:
        count = wintypes.DWORD(len(monitors))
        arr = (PHYSICAL_MONITOR * len(monitors))(*monitors)
        dxva2.DestroyPhysicalMonitors(count, arr)


if __name__ == "__main__":
    main()
