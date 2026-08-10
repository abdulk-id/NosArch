#!/usr/bin/env python3

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from enum import IntEnum

from dbus_fast.aio import MessageBus
from dbus_fast.aio.proxy_object import ProxyInterface, ProxyObject
from dbus_fast.constants import BusType
from dbus_fast.introspection import Node
from dbus_fast.signature import Variant

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)

log: logging.Logger = logging.getLogger("nosarch-battery-monitor")

UPOWER_BUS: str = "org.freedesktop.UPower"
DEVICE_INTERFACE: str = "org.freedesktop.UPower.Device"
PROPERTIES_INTERFACE: str = "org.freedesktop.DBus.Properties"
DISPLAY_DEVICE: str = "/org/freedesktop/UPower/devices/DisplayDevice"


# UPower.Device.State
class BatteryState(IntEnum):
    CHARGING = 1
    DISCHARGING = 2
    EMPTY = 3
    FULLY_CHARGED = 4
    PENDING_CHARGE = 5
    PENDING_DISCHARGE = 6


THRESHOLDS: list[tuple[int, str]] = [
    (15, "/usr/lib/nosarch/battery-low.sh"),
    # (5, "/usr/lib/nosarch/battery-critical.sh"),
]


@dataclass(slots=True)
class Battery:
    percentage: int | None = None
    state: BatteryState | None = None


battery: Battery = Battery()

triggered: set[int] = set()


def run_script(script: str, percentage: int) -> None:
    log.info("Executing: %s", script)

    try:
        subprocess.run(
            [script, str(percentage)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        log.error("Script not found: %s", script)
    except subprocess.CalledProcessError as e:
        log.error("Script exited with status %d: %s", e.returncode, e.stderr)
    else:
        log.info("Script completed successfully")


def evaluate() -> None:
    percentage: int | None = battery.percentage
    state: BatteryState | None = battery.state

    if percentage is None or state is None:
        return

    log.debug("Battery: %d%% (%s)", percentage, state.name.lower().replace("_", "-"))

    if state != BatteryState.DISCHARGING:
        if triggered:
            log.debug("Battery is no longer discharging. Resetting triggers")
            triggered.clear()
        return

    for threshold, script in THRESHOLDS:
        if percentage <= threshold:
            if threshold in triggered:
                log.debug(
                    "Threshold %d%% already triggered",
                    threshold,
                )
                continue

            log.info(
                "Crossed %d%% threshold",
                threshold,
            )

            run_script(script, percentage)
            triggered.add(threshold)
        else:
            if threshold in triggered:
                log.info(
                    "Battery above %d%% again. Resetting trigger",
                    threshold,
                )
                triggered.remove(threshold)


async def main() -> None:
    log.debug("Connecting to system bus...")

    bus: MessageBus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    log.debug("Connected to system bus")

    introspection: Node = await bus.introspect(
        UPOWER_BUS,
        DISPLAY_DEVICE,
    )

    proxy_obj: ProxyObject = bus.get_proxy_object(
        UPOWER_BUS,
        DISPLAY_DEVICE,
        introspection,
    )

    proxy_interface: ProxyInterface = proxy_obj.get_interface(PROPERTIES_INTERFACE)

    # Populate initial cache
    battery.percentage = int(
        (
            await proxy_interface.call_get(
                DEVICE_INTERFACE,
                "Percentage",
            )
        ).value
    )

    battery.state = BatteryState(
        (
            await proxy_interface.call_get(
                DEVICE_INTERFACE,
                "State",
            )
        ).value
    )

    log.debug(
        "Initial state: %d%% (state: %s)",
        battery.percentage,
        battery.state.name,
    )

    evaluate()

    def properties_changed(
        interface_name: str, changed: dict[str, Variant], invalidated: list[str]
    ) -> None:
        if interface_name != DEVICE_INTERFACE:
            return

        relevant_props_updated = False

        if "Percentage" in changed:
            log.debug("Percentage changed: %s", int(changed["Percentage"].value))
            battery.percentage = int(changed["Percentage"].value)
            relevant_props_updated = True

        if "State" in changed:
            log.debug("State changed: %s", changed["State"].value)
            battery.state = BatteryState(changed["State"].value)
            relevant_props_updated = True

        if relevant_props_updated:
            evaluate()

    proxy_interface.on_properties_changed(properties_changed)

    log.debug("Waiting for battery events...")

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
