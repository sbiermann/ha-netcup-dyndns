from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from ipaddress import ip_address
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

IPV4_URL = "https://api.ipify.org"
IPV6_URL = "https://api64.ipify.org"


@dataclass
class NetcupDynDnsState:
    ipv4: str | None
    ipv6: str | None
    last_update_result: str
    last_changed: bool


async def _fetch_text(hass: HomeAssistant, url: str) -> str:
    session = async_get_clientsession(hass)
    async with session.get(url, timeout=20) as resp:
        resp.raise_for_status()
        return (await resp.text()).strip()


async def _get_public_ip(hass: HomeAssistant, want_v6: bool) -> str | None:
    try:
        raw = await _fetch_text(hass, IPV6_URL if want_v6 else IPV4_URL)
        ip_address(raw)
        return raw
    except Exception:
        return None


class NetcupDynDnsCoordinator(DataUpdateCoordinator[NetcupDynDnsState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        scan_interval = int(
            entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        )

        super().__init__(
            hass,
            logger=None,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=timedelta(seconds=scan_interval),
        )

        self._last_ipv4: str | None = None
        self._last_ipv6: str | None = None
        self._force_next: bool = False

    def force_next_update(self) -> None:
        self._force_next = True

    async def _async_update_data(self) -> NetcupDynDnsState:
        try:
            return await self._do_update()
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def _do_update(self) -> NetcupDynDnsState:
        data = self.entry.data
        opts = self.entry.options

        domainname = opts.get(CONF_DOMAINNAME, data[CONF_DOMAINNAME])
        hostname = opts.get(CONF_HOSTNAME, data[CONF_HOSTNAME])
        update_v4 = bool(opts.get(CONF_UPDATE_IPV4, data.get(CONF_UPDATE_IPV4, True)))
        update_v6 = bool(opts.get(CONF_UPDATE_IPV6, data.get(CONF_UPDATE_IPV6, False)))

        ipv4 = await _get_public_ip(self.hass, want_v6=False) if update_v4 else None
        ipv6 = await _get_public_ip(self.hass, want_v6=True) if update_v6 else None

        if update_v4 and not ipv4:
            return NetcupDynDnsState(ipv4=None, ipv6=ipv6, last_update_result="Failed to fetch public IPv4", last_changed=False)
        if update_v6 and not ipv6:
            return NetcupDynDnsState(ipv4=ipv4, ipv6=None, last_update_result="Failed to fetch public IPv6", last_changed=False)

        changed = self._force_next
        if update_v4 and ipv4 and ipv4 != self._last_ipv4:
            changed = True
        if update_v6 and ipv6 and ipv6 != self._last_ipv6:
            changed = True

        if not changed:
            return NetcupDynDnsState(ipv4=ipv4, ipv6=ipv6, last_update_result="No change", last_changed=False)

        creds = NetcupCredentials(
            customer_number=int(data[CONF_CUSTOMER_NUMBER]),
            api_key=data[CONF_API_KEY],
            api_password=data[CONF_API_PASSWORD],
        )

        session = async_get_clientsession(self.hass)

        try:
            async with NetcupApiClient(session, creds) as api:
                records = await api.info_dns_records(domainname)

                def _is_target(r: dict[str, Any], rtype: str) -> bool:
                    return (r.get("hostname") == hostname) and (r.get("type") == rtype)

                def _ensure_required_fields(r: dict[str, Any], rtype: str, destination: str) -> None:
                    r["hostname"] = hostname
                    r["type"] = rtype
                    r.setdefault("priority", "0")
                    r["destination"] = destination
                    r["deleterecord"] = False

                def _update_or_add(rtype: str, new_ip: str) -> bool:
                    nonlocal records
                    for r in records:
                        if _is_target(r, rtype):
                            if r.get("destination") != new_ip or self._force_next:
                                _ensure_required_fields(r, rtype, new_ip)
                                return True
                            return False
                    # not found -> add
                    records.append(
                        {
                            "id": None,
                            "hostname": hostname,
                            "type": rtype,
                            "priority": "0",
                            "destination": new_ip,
                            "deleterecord": False,
                        }
                    )
                    return True

                did_change = False
                if update_v4 and ipv4:
                    did_change = _update_or_add("A", ipv4) or did_change
                if update_v6 and ipv6:
                    did_change = _update_or_add("AAAA", ipv6) or did_change

                if did_change:
                    await api.update_dns_records(domainname, records)

        except NetcupApiError as err:
            self._force_next = False
            return NetcupDynDnsState(ipv4=ipv4, ipv6=ipv6, last_update_result=f"Netcup API error: {err}", last_changed=False)

        # success
        if update_v4:
            self._last_ipv4 = ipv4
        if update_v6:
            self._last_ipv6 = ipv6
        self._force_next = False

        return NetcupDynDnsState(ipv4=ipv4, ipv6=ipv6, last_update_result="Updated", last_changed=True)
