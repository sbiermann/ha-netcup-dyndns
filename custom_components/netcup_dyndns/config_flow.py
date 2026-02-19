from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NetcupApiClient, NetcupApiError, NetcupCredentials
from .const import (
    CONF_API_KEY,
    CONF_API_PASSWORD,
    CONF_CUSTOMER_NUMBER,
    CONF_DOMAINNAME,
    CONF_HOSTNAME,
    CONF_SCAN_INTERVAL,
    CONF_UPDATE_IPV4,
    CONF_UPDATE_IPV6,
    DEFAULT_HOSTNAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPDATE_IPV4,
    DEFAULT_UPDATE_IPV6,
    DOMAIN,
)


class NetcupDynDnsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            creds = NetcupCredentials(
                customer_number=int(user_input[CONF_CUSTOMER_NUMBER]),
                api_key=user_input[CONF_API_KEY],
                api_password=user_input[CONF_API_PASSWORD],
            )
            domainname = user_input[CONF_DOMAINNAME]

            session = async_get_clientsession(self.hass)
            try:
                async with NetcupApiClient(session, creds) as api:
                    await api.info_dns_records(domainname)
            except NetcupApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(f"{domainname}:{user_input[CONF_HOSTNAME]}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{domainname} ({user_input[CONF_HOSTNAME]})",
                    data={
                        CONF_CUSTOMER_NUMBER: int(user_input[CONF_CUSTOMER_NUMBER]),
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_API_PASSWORD: user_input[CONF_API_PASSWORD],
                        CONF_DOMAINNAME: domainname,
                        CONF_HOSTNAME: user_input[CONF_HOSTNAME],
                        CONF_UPDATE_IPV4: bool(user_input[CONF_UPDATE_IPV4]),
                        CONF_UPDATE_IPV6: bool(user_input[CONF_UPDATE_IPV6]),
                        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CUSTOMER_NUMBER): vol.Coerce(int),
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_API_PASSWORD): str,
                vol.Required(CONF_DOMAINNAME): str,
                vol.Optional(CONF_HOSTNAME, default=DEFAULT_HOSTNAME): str,
                vol.Optional(CONF_UPDATE_IPV4, default=DEFAULT_UPDATE_IPV4): bool,
                vol.Optional(CONF_UPDATE_IPV6, default=DEFAULT_UPDATE_IPV6): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.Coerce(int),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_options(self, user_input=None):
        return await OptionsFlowHandler(self.hass).async_step_init(user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, hass):
        self.hass = hass

    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}
        entry = self.config_entry

        if user_input is not None:
            creds = NetcupCredentials(
                customer_number=int(entry.data[CONF_CUSTOMER_NUMBER]),
                api_key=entry.data[CONF_API_KEY],
                api_password=entry.data[CONF_API_PASSWORD],
            )
            session = async_get_clientsession(self.hass)
            try:
                async with NetcupApiClient(session, creds) as api:
                    await api.info_dns_records(user_input[CONF_DOMAINNAME])
            except NetcupApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_DOMAINNAME, default=entry.options.get(CONF_DOMAINNAME, entry.data[CONF_DOMAINNAME])): str,
                vol.Optional(CONF_HOSTNAME, default=entry.options.get(CONF_HOSTNAME, entry.data[CONF_HOSTNAME])): str,
                vol.Optional(CONF_UPDATE_IPV4, default=entry.options.get(CONF_UPDATE_IPV4, entry.data.get(CONF_UPDATE_IPV4, True))): bool,
                vol.Optional(CONF_UPDATE_IPV6, default=entry.options.get(CONF_UPDATE_IPV6, entry.data.get(CONF_UPDATE_IPV6, False))): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
