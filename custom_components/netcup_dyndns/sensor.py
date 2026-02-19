from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NetcupDynDnsCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: NetcupDynDnsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            NetcupDynDnsSensor(coordinator, entry, kind="ipv4"),
            NetcupDynDnsSensor(coordinator, entry, kind="ipv6"),
            NetcupDynDnsSensor(coordinator, entry, kind="status"),
        ],
        True,
    )


class NetcupDynDnsSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: NetcupDynDnsCoordinator, entry: ConfigEntry, kind: str) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self.kind = kind

        self._attr_unique_id = f"{entry.entry_id}_{kind}"
        self._attr_name = {"ipv4": "Public IPv4", "ipv6": "Public IPv6", "status": "Update Status"}[kind]

    @property
    def native_value(self):
        data = self.coordinator.data
        if data is None:
            return None
        if self.kind == "ipv4":
            return data.ipv4
        if self.kind == "ipv6":
            return data.ipv6
        return data.last_update_result

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if data is None:
            return {}
        return {"last_changed": data.last_changed}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
