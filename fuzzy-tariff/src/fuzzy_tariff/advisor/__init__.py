"""Stage 2: device-specific advice (start now / wait / must start) and slot planning."""

from fuzzy_tariff.advisor.devices import (
    DEVICE_PROFILES,
    Advice,
    Device,
    DeviceAdvisor,
    DeviceProfile,
    DeviceRequest,
    plan_slots,
    urgency,
)

__all__ = [
    "DEVICE_PROFILES",
    "Advice",
    "Device",
    "DeviceAdvisor",
    "DeviceProfile",
    "DeviceRequest",
    "plan_slots",
    "urgency",
]
