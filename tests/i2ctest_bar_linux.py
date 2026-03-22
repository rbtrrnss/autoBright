import struct
from time import sleep

import hid


def parse_report(report: bytes) -> tuple[int, int, int, float]:
    data = bytes(report)

    # Some hosts prepend report ID 0 even for unnumbered reports.
    if len(data) >= 7 and data[0] == 0:
        data = data[1:]

    if len(data) < 6:
        raise ValueError(f"Report too short: {len(data)} bytes ({data.hex()})")

    state = data[0]
    event = data[1]
    raw_lux_fixed = struct.unpack_from("<I", data, 2)[0]
    lux = raw_lux_fixed / 10000.0
    return state, event, raw_lux_fixed, lux


def lux_bar(lux: float, max_lux: float = 10000.0, width: int = 20) -> str:
    clamped = max(0.0, min(lux, max_lux))
    filled = int(round((clamped / max_lux) * width))
    filled = max(0, min(filled, width))
    return "[" + ("#" * filled) + ("_" * (width - filled)) + "]"


def main() -> None:
    vid, pid = 0x16C0, 0x27D9
    dev = hid.device()
    dev.open(vid, pid)
    if dev is None:
        raise SystemExit("device not found")
    dev.set_nonblocking(True)

    try:
        # Get feature report (report ID 0)
        feature = dev.get_feature_report(0, 24)
        if len(feature) < 3:
            raise RuntimeError("Feature report too short")

        # Enable active reporting mode.
        feature[1] = 0x02  # reportingState: ALL_EVENTS
        feature[2] = 0x02  # powerState: D0_FULL_POWER
        dev.send_feature_report(bytes(feature))
        sleep(1.0)

        print("Press Ctrl+C to stop")
        while True:
            # Read input report
            raw = dev.read(8)
            if raw:
                _, _, _, lux = parse_report(bytes(raw))
                bar = lux_bar(lux)
                line = f"lux={lux:8.2f} {bar}"
                print("\r" + line.ljust(40), end="", flush=True)
            sleep(0.25)
    except KeyboardInterrupt:
        print()
    finally:
        dev.close()


if __name__ == "__main__":
    main()
