import struct

import usb.core
import usb.util

from time import sleep


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
        print(f"feature(before): {feature.hex()}")
        if len(feature) < 3:
            raise RuntimeError("Feature report too short")

        # Feature layout starts with: connectionType, reportingState, powerState...
        # Set reporting to ALL_EVENTS and power to D0_FULL_POWER.
        feature[1] = 0x02
        feature[2] = 0x02
        set_feature_report(dev, intf_num, bytes(feature))
        sleep(1.0)

        feature_after = get_feature_report(dev, intf_num)
        print(f"feature(after):  {feature_after.hex()}")

        for i in range(100):
            # HID class request: GET_REPORT (Input report, id 0)
            raw = bytes(
                dev.ctrl_transfer(
                    0xA1,  # bmRequestType: IN | Class | Interface
                    0x01,  # bRequest: GET_REPORT
                    0x0100,  # wValue: (Input report << 8) | report_id(0)
                    intf_num,  # wIndex: interface number
                    8,  # max bytes to read
                    timeout=3000,
                )
            )

            state, event, raw_lux, lux = parse_report(raw)
            #print(f"raw report bytes: {raw.hex()}")
            print(f"state={state} event={event} raw={raw_lux} lux={lux:.4f}")
            sleep(0.5)  # Give the device time to update its state after the request
    finally:
        usb.util.release_interface(dev, intf_num)


if __name__ == "__main__":
    main()