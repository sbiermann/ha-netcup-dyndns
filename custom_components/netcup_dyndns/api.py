from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

NETCUP_ENDPOINT = "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"


class NetcupApiError(Exception):
    """Raised when the Netcup API returns an error or cannot be reached."""


@dataclass(frozen=True)
class NetcupCredentials:
    customer_number: int
    api_key: str
    api_password: str


class NetcupApiClient:
    def __init__(self, session: aiohttp.ClientSession, creds: NetcupCredentials) -> None:
        self._session = session
        self._creds = creds
        self._session_id: str | None = None

    async def __aenter__(self) -> "NetcupApiClient":
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            await self.logout()
        except NetcupApiError:
            pass

    async def _call(self, action: str, param: dict[str, Any]) -> dict[str, Any]:
        payload = {"action": action, "param": param}
        try:
            async with self._session.post(
                NETCUP_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise NetcupApiError(f"HTTP/JSON error calling {action}: {err}") from err

        if data.get("status") != "success":
            code = data.get("statuscode")
            short = data.get("shortmessage")
            longm = data.get("longmessage")
            raise NetcupApiError(f"Netcup API error ({code}) {short}: {longm}")

        return data

    async def login(self) -> str:
        data = await self._call(
            "login",
            {
                "customernumber": str(self._creds.customer_number),
                "apikey": self._creds.api_key,
                "apipassword": self._creds.api_password,
                "clientrequestid": "",
            },
        )
        responsedata = data.get("responsedata") or {}
        session_id = responsedata.get("apisessionid")
        if not session_id:
            raise NetcupApiError("Login succeeded but no apisessionid returned.")
        self._session_id = session_id
        return session_id

    async def logout(self) -> None:
        if not self._session_id:
            return
        await self._call(
            "logout",
            {
                "customernumber": str(self._creds.customer_number),
                "apikey": self._creds.api_key,
                "apisessionid": self._session_id,
                "clientrequestid": "",
            },
        )
        self._session_id = None

    def _auth(self) -> dict[str, Any]:
        if not self._session_id:
            raise NetcupApiError("Not logged in (missing apisessionid).")
        return {
            "customernumber": str(self._creds.customer_number),
            "apikey": self._creds.api_key,
            "apisessionid": self._session_id,
            "clientrequestid": "",
        }

    async def info_dns_records(self, domainname: str) -> list[dict[str, Any]]:
        data = await self._call(
            "infoDnsRecords",
            {
                "domainname": domainname,
                **self._auth(),
            },
        )
        responsedata = data.get("responsedata") or {}
        recordset = responsedata.get("dnsrecordset") or {}
        records = recordset.get("dnsrecords") or []
        if isinstance(records, dict):
            records = [records]
        return list(records)

    async def update_dns_records(self, domainname: str, records: list[dict[str, Any]]) -> None:
        await self._call(
            "updateDnsRecords",
            {
                "domainname": domainname,
                **self._auth(),
                "dnsrecordset": {"dnsrecords": records},
            },
        )
