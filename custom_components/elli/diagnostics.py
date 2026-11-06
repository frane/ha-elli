"""Diagnostics: what the wallbox reports, including the raw EEBUS data it serves."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import ElliConfigEntry
from .eebus import EebusCoordinator

TO_REDACT = {"serial", "serialNumber", "identificationValue", "ski", "host", "macAddress"}


def _eebus_device(coordinator: EebusCoordinator) -> dict[str, Any] | None:
    """Entities, features and their data as the wallbox served them, for bug reports."""
    client = coordinator.client
    device = client._device() if client is not None else None  # noqa: SLF001
    if device is None:
        return None
    return {
        "device_type": device.device_type,
        "use_cases": device.use_cases(),
        "entities": [
            {
                "address": list(entity.entity),
                "type": entity.type,
                "features": [
                    {
                        "id": feature.id,
                        "type": feature.type,
                        "role": feature.role,
                        "functions": sorted(feature.operations),
                        "data": feature.data,
                    }
                    for feature in entity.features
                ],
            }
            for entity in device.entities
        ],
    }


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ElliConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    result: dict[str, Any] = {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "status": asdict(data) if data is not None else None,
    }
    if isinstance(coordinator, EebusCoordinator):
        result["eebus"] = _eebus_device(coordinator)
    return async_redact_data(result, TO_REDACT)
