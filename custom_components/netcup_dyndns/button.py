from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NetcupDynDnsCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: NetcupDynDnsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NetcupDynDnsUpdateButton(coordinator, entry)])


class NetcupDynDnsUpdateButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Update now"
    _attr_icon = "mdi:dns"

    def __init__(self, coordinator: NetcupDynDnsCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_update_button"

    async def async_press(self) -> None:
        self.coordinator.force_next_update()
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
