"""The Techem integration."""


from .const import DOMAIN
from datetime import timedelta, datetime
import logging
from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import httpx_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

UPDATE_INTERVAL = timedelta(hours=6)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Techem from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    coordinator = TechemCoordinator(hass)

    hass.data[DOMAIN][entry.entry_id] = coordinator
    hass.data[DOMAIN]["data"] = entry.data

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class TechemCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Techem data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Techem."""
        try:
            httpx_session = httpx_client.get_async_client(self.hass)
            data = self.hass.data[DOMAIN]["data"]
            if data["tokens"]["payload"]["exp"] < datetime.now().timestamp():
                _LOGGER.debug("Refreshing token")
                refresh_body = (
                    '{"query":"mutation tokenRefresh($refreshToken: String!) { refreshToken(refreshToken: $refreshToken) { payload, refreshExpiresIn, token, refreshToken } }","variables":{"refreshToken":"'
                    + data["tokens"]["refreshToken"]
                    + '"}}'
                )

                refresh_headers = {
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Referer": "https://app.techem.dk/",
                    "Content-Type": "application/json",
                }

                refresh_response = await httpx_session.post(
                    "https://techemadmin.dk/graphql",
                    headers=refresh_headers,
                    data=refresh_body,
                    timeout=10.0,
                )

                mergedTokens = self.hass.data[DOMAIN]["data"]["tokens"]
                mergedTokens.update(refresh_response.json()["data"]["refreshToken"])
                self.hass.data[DOMAIN]["data"]["tokens"].update(mergedTokens)
            starttime_past_week = self.get_time_as_string(7)
            endtime_past_week = self.get_time_as_string(0)
            body_past_week = (
                '{"query":"\\n      query DashboardData($tenancyId: Int!, $periodBegin: String, $periodEnd: String, $compareWith: String!) {\\n        dashboard(tenancyId: $tenancyId, periodBegin: $periodBegin, periodEnd: $periodEnd, compareWith: $compareWith) {\\n          consumptions {\\n            value\\n            comparisonValue\\n            kind\\n            comparePercent\\n          }\\n          climateAverages {\\n            value\\n            valueCompare\\n            kind\\n          }\\n        }\\n      }\\n    ","variables":{"tenancyId":'
                + str(data["tenant_id"])
                + ',"periodBegin":"'
                + starttime_past_week
                + '","periodEnd":"'
                + endtime_past_week
                + '","compareWith":"last_period"},"operationName":"DashboardData"}'
            )

            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://app.techem.dk/",
                "Referer": "https://app.techem.dk/",
                "Authorization": f"JWT {data['tokens']['token']}",
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            }

            response_past_week_raw = await httpx_session.post(
                "https://techemadmin.dk/graphql",
                headers=headers,
                data=body_past_week,
                timeout=10.0,
            )

            response_past_week = response_past_week_raw.json()["data"]["dashboard"][
                "consumptions"
            ]

            starttime_this_year = self.get_time_as_string_year()[0]
            endtime_this_year = self.get_time_as_string_year()[1]
            body_this_year = (
                '{"query":"\\n      query DashboardData($tenancyId: Int!, $periodBegin: String, $periodEnd: String, $compareWith: String!) {\\n        dashboard(tenancyId: $tenancyId, periodBegin: $periodBegin, periodEnd: $periodEnd, compareWith: $compareWith) {\\n          consumptions {\\n            value\\n            comparisonValue\\n            kind\\n            comparePercent\\n          }\\n          climateAverages {\\n            value\\n            valueCompare\\n            kind\\n          }\\n        }\\n      }\\n    ","variables":{"tenancyId":'
                + str(data["tenant_id"])
                + ',"periodBegin":"'
                + starttime_this_year
                + '","periodEnd":"'
                + endtime_this_year
                + '","compareWith":"last_period"},"operationName":"DashboardData"}'
            )

            response_this_year_raw = await httpx_session.post(
                "https://techemadmin.dk/graphql",
                headers=headers,
                data=body_this_year,
                timeout=10.0,
            )

            response_this_year = response_this_year_raw.json()["data"]["dashboard"][
                "consumptions"
            ]

            return {
                "past_week": response_past_week,
                "this_year": response_this_year,
            }

        except ConnectionError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def get_time_as_string(self, n: int) -> str:
        today = datetime.now()
        date = today - timedelta(days=n)

        return f"{date.year}-{date.month:02d}-{date.day:02d}"

    def get_time_as_string_year(self) -> tuple[str, str]:
        today = datetime.now()
        stop = f"{today.year}-{today.month:02d}-{today.day:02d}"

        firstDay = datetime(today.year, 1, 1)
        start = f"{firstDay.year}-{firstDay.month:02d}-{firstDay.day:02d}"

        return start, stop
