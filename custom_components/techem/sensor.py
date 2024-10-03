from __future__ import annotations
import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TechemCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add TechemClimate entities from a config_entry."""
    coordinator: TechemCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    collect = []
    # [{'value': 46.0, 'comparisonValue': 2.0, 'kind': 'energy', 'comparePercent': 2200.0}, {'value': 1.107999999999997, 'comparisonValue': 1.166000000000004, 'kind': 'coldwater', 'comparePercent': -5.0}, {'value': 0.7750000000000021, 'comparisonValue': 0.7099999999999973, 'kind': 'hotwater', 'comparePercent': 9.0}]
    for entry in coordinator.data["past_week"]:
        if entry["kind"] == "energy":
            collect.append(TechemSensor(coordinator, "Heat (past week)", entry["kind"]))
            collect.append(
                TechemSensor(coordinator, "Heat (previous week)", entry["kind"])
            )
        elif entry["kind"] == "coldwater":
            collect.append(
                TechemSensor(coordinator, "Cold water (past week)", "volume")
            )
            collect.append(
                TechemSensor(coordinator, "Cold water (previous week)", "volume")
            )
        elif entry["kind"] == "hotwater":
            collect.append(TechemSensor(coordinator, "Hot water (past week)", "volume"))
            collect.append(
                TechemSensor(coordinator, "Hot water (previous week)", "volume")
            )
    for entry in coordinator.data["this_year"]:
        if entry["kind"] == "energy":
            collect.append(TechemSensor(coordinator, "Heat (this year)", entry["kind"]))
            collect.append(TechemSensor(coordinator, "Heat (previous year)", "volume"))
        elif entry["kind"] == "coldwater":
            collect.append(
                TechemSensor(coordinator, "Cold water (this year)", "volume")
            )
            collect.append(
                TechemSensor(coordinator, "Cold water (previous year)", "volume")
            )
        elif entry["kind"] == "hotwater":
            collect.append(TechemSensor(coordinator, "Hot water (this year)", "volume"))
            collect.append(
                TechemSensor(coordinator, "Hot water (previous year)", "volume")
            )
    async_add_entities(collect)


class TechemSensor(CoordinatorEntity[TechemCoordinator], SensorEntity):
    """Alpha Smart SensorEntity."""

    _attr_state_class = SensorStateClass.TOTAL
    type: str

    def __init__(
        self, coordinator: TechemCoordinator, device_id: str, type: str
    ) -> None:
        """Initialize Alpha Smart SensorEntity."""
        super().__init__(coordinator)
        self._attr_unique_id = device_id
        self._attr_name = device_id
        self.type = type

    @property
    def device_class(self) -> str:
        """Return the device class of the sensor."""
        if self.type == "energy":
            return SensorDeviceClass.ENERGY
        return SensorDeviceClass.VOLUME

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        if self.type == "energy":
            return "kWh"
        elif self.type == "percent":
            return "%"
        return "m³"

    @property
    def native_value(self) -> float:
        """Return the current humidity."""
        arrweek = self.coordinator.data["past_week"]
        arryear = self.coordinator.data["this_year"]
        if self._attr_unique_id == "Heat (past week)":
            return self.find(arrweek, "energy")["value"]
        elif self._attr_unique_id == "Heat (previous week)":
            return self.find(arrweek, "energy")["comparisonValue"]
        elif self._attr_unique_id == "Cold water (past week)":
            return self.find(arrweek, "coldwater")["value"]
        elif self._attr_unique_id == "Cold water (previous week)":
            return self.find(arrweek, "coldwater")["comparisonValue"]
        elif self._attr_unique_id == "Hot water (past week)":
            return self.find(arrweek, "hotwater")["value"]
        elif self._attr_unique_id == "Hot water (previous week)":
            return self.find(arrweek, "hotwater")["comparisonValue"]
        elif self._attr_unique_id == "Heat (this year)":
            return self.find(arryear, "energy")["value"]
        elif self._attr_unique_id == "Heat (previous year)":
            return self.find(arryear, "energy")["comparisonValue"]
        elif self._attr_unique_id == "Cold water (this year)":
            return self.find(arryear, "coldwater")["value"]
        elif self._attr_unique_id == "Cold water (previous year)":
            return self.find(arryear, "coldwater")["comparisonValue"]
        elif self._attr_unique_id == "Hot water (this year)":
            return self.find(arryear, "hotwater")["value"]
        elif self._attr_unique_id == "Hot water (previous year)":
            return self.find(arryear, "hotwater")["comparisonValue"]

    def find(self, arr, kind):
        for x in arr:
            if x["kind"] == kind:
                return x
