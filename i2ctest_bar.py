import struct
from time import sleep

import usb.core
import usb.util


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


def get_feature_report(dev, intf_num: int, length: int = 24) -> bytearray:
    data = dev.ctrl_transfer(
        0xA1,  # bmRequestType: IN | Class | Interface
        0x01,  # bRequest: GET_REPORT
        0x0300,  # wValue: (Feature report << 8) | report_id(0)
        intf_num,
        length,
        timeout=3000,
    )
    return bytearray(data)


def set_feature_report(dev, intf_num: int, payload: bytes) -> None:
    dev.ctrl_transfer(
        0x21,  # bmRequestType: OUT | Class | Interface
        0x09,  # bRequest: SET_REPORT
        0x0300,  # wValue: (Feature report << 8) | report_id(0)
        intf_num,
        payload,
        timeout=3000,
    )


def lux_bar(lux: float, max_lux: float = 10000.0, width: int = 20) -> str:
    clamped = max(0.0, min(lux, max_lux))
    filled = int(round((clamped / max_lux) * width))
    filled = max(0, min(filled, width))
    return "[" + ("#" * filled) + ("_" * (width - filled)) + "]"


def main() -> None:
    vid, pid = 0x16C0, 0x27D9
    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:
        raise SystemExit("device not found")

    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]
    intf_num = intf.bInterfaceNumber

    if dev.is_kernel_driver_active(intf_num):
        dev.detach_kernel_driver(intf_num)
    usb.util.claim_interface(dev, intf_num)

    try:
        feature = get_feature_report(dev, intf_num)
        if len(feature) < 3:
            raise RuntimeError("Feature report too short")

        # Enable active reporting mode.
        feature[1] = 0x02  # reportingState: ALL_EVENTS
        feature[2] = 0x02  # powerState: D0_FULL_POWER
        set_feature_report(dev, intf_num, bytes(feature))
        sleep(1.0)

        print("Press Ctrl+C to stop")
        while True:
            raw = bytes(
                dev.ctrl_transfer(
                    0xA1,  # bmRequestType: IN | Class | Interface
                    0x01,  # bRequest: GET_REPORT
                    0x0100,  # wValue: (Input report << 8) | report_id(0)
                    intf_num,
                    8,
                    timeout=3000,
                )
            )

            _, _, _, lux = parse_report(raw)
            bar = lux_bar(lux)
            line = f"lux={lux:8.2f} {bar}"
            print("\r" + line.ljust(40), end="", flush=True)
            sleep(0.25)
    except KeyboardInterrupt:
        print()
    finally:
        usb.util.release_interface(dev, intf_num)


if __name__ == "__main__":
    main()
