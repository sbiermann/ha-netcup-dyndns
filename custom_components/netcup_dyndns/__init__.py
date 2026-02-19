from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS, SERVICE_UPDATE
from .coordinator import NetcupDynDnsCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def _handle_update(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        if entry_id:
            coord: NetcupDynDnsCoordinator | None = hass.data[DOMAIN].get(entry_id)
            if coord:
                coord.force_next_update()
                await coord.async_request_refresh()
            return

        for coord in hass.data[DOMAIN].values():
            coord.force_next_update()
            await coord.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE,
        _handle_update,
        schema=vol.Schema({vol.Optional("entry_id"): cv.string}),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = NetcupDynDnsCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
