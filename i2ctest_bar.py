from time import sleep
import threading

from winsdk.windows.devices.sensors import LightSensor


def lux_bar(lux: float, max_lux: float = 10000.0, width: int = 40) -> str:
    import math
    clamped = max(0.01, min(lux, max_lux))  # avoid log(0)
    # Logarithmic scale: log10(lux) from 0.2 to max_lux
    min_log = math.log10(0.2)
    max_log = math.log10(max_lux)
    value_log = math.log10(clamped)
    frac = (value_log - min_log) / (max_log - min_log)
    filled = int(round(frac * width))
    filled = max(0, min(filled, width))
    return "[" + ("#" * filled) + ("_" * (width - filled)) + "]"


last_lux = 0.0
lock = threading.Lock()


def on_reading_changed(sensor, args):
    global last_lux
    reading = args.reading
    if reading:
        with lock:
            last_lux = reading.illuminance_in_lux


def main() -> None:
    sensor = LightSensor.get_default()
    if sensor is None:
        raise SystemExit("No light sensor found")

    sensor.report_interval = max(sensor.minimum_report_interval, 250)
    sensor.add_reading_changed(on_reading_changed)

    print("Press Ctrl+C to stop")
    try:
        while True:
            with lock:
                lux = last_lux
            bar = lux_bar(lux)
            line = f"lux={lux:8.2f} {bar}"
            print("\r" + line.ljust(40), end="", flush=True)
            sleep(0.25)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
