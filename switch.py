"""Switch setup for our Integration."""

# from datetime import datetime
import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Device, DeviceType
from .const import DOMAIN
from .coordinator import PiwigoWallDisplayCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Binary Sensors."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator: PiwigoWallDisplayCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    # ----------------------------------------------------------------------------
    # Here we enumerate the switches in your data value from your
    # DataUpdateCoordinator and add an instance of your switch class to a list
    # for each one.
    # This maybe different in your specific case, depending on how your data is
    # structured
    # ----------------------------------------------------------------------------
    # print("setting up socket")
    switches = [
        PiwigoWallDisplaySwitch(coordinator, device, "state")
        for device in coordinator.data.devices
        if device.device_type == DeviceType.SOCKET  # for device in coordinator.data
        # if device.get("device_type") == "SOCKET"
    ]

    # Create the binary sensors.
    async_add_entities(switches)


class PiwigoWallDisplaySwitch(CoordinatorEntity, SwitchEntity):
    """Implementation of a switch.

    This inherits our PiwigoWallDisplayBaseEntity to set common properties.
    See base.py for this class.

    https://developers.home-assistant.io/docs/core/entity/switch
    """

    _attr_device_class = SwitchDeviceClass.SWITCH

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PiwigoWallDisplayCoordinator, device: Device, parameter: str
    ) -> None:
        """Initialise entity."""
        super().__init__(coordinator)
        self.device = device
        self.device_id = device.device_id
        self.parameter = parameter

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        self.device = self.coordinator.get_device_by_id(
            self.device.device_type, self.device.device_unique_id
        )
        _LOGGER.debug("Device: %s", self.device)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""

        # ----------------------------------------------------------------------------
        # Identifiers are what group entities into the same device.
        # If your device is created elsewhere, you can just specify the indentifiers
        # parameter to link an entity to a device.
        # If your device connects via another device, add via_device parameter with
        # the indentifiers of that device.
        #
        # Device identifiers should be unique, so use your integration name (DOMAIN)
        # and a device uuid, mac address or some other unique attribute.
        # ----------------------------------------------------------------------------
        return DeviceInfo(
            name=f"Wall Display Options{self.device.device_id}",
            manufacturer="ACME Manufacturer",
            model="piwigo",
            sw_version="1.0",
            identifiers={
                (
                    DOMAIN,
                    f"{self.coordinator.data.controller_name}-{self.device.device_id}",
                )
            },
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.device.name  # self.parameter.replace("_", " ").title()

    @property
    def unique_id(self) -> str:
        """Return unique id."""

        # ----------------------------------------------------------------------------
        # All entities must have a unique id across your whole Home Assistant server -
        # and that also goes for anyone using your integration who may have many other
        # integrations loaded.
        #
        # Think carefully what you want this to be as changing it later will cause HA
        # to create new entities.
        #
        # It is recommended to have your integration name (DOMAIN), some unique id
        # from your device such as a UUID, MAC address etc (not IP address) and then
        # something unique to your entity (like name - as this would be unique on a
        # device)
        #
        # If in your situation you have some hub that connects to devices which then
        # you want to create multiple sensors for each device, you would do something
        # like.
        #
        # f"{DOMAIN}-{HUB_MAC_ADDRESS}-{DEVICE_UID}-{ENTITY_NAME}""
        #
        # This is even more important if your integration supports multiple instances.
        # ----------------------------------------------------------------------------
        return f"{DOMAIN}-{self.device.device_unique_id}"

    @property
    def is_on(self) -> bool | None:
        """Return if the binary sensor is on."""
        # This needs to enumerate to true or false
        # self_device=dict(self.device)
        return self.device.state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        # print(f"Time Zone= {self.hass.config.time_zone}")
        await self.hass.async_add_executor_job(self.coordinator.api.connect)
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_data,
            self.device,
            "true",  # self.device_id, self.parameter, "ON"
        )
        # ----------------------------------------------------------------------------
        # Use async_refresh on the DataUpdateCoordinator to perform immediate update.
        # Using self.async_update or self.coordinator.async_request_refresh may delay update due
        # to trying to batch requests.
        # ----------------------------------------------------------------------------
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.hass.async_add_executor_job(self.coordinator.api.connect)
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_data,
            self.device,
            "false",  # self.device_id, self.parameter, "OFF"
        )
        # ----------------------------------------------------------------------------
        # Use async_refresh on the DataUpdateCoordinator to perform immediate update.
        # Using self.async_update or self.coordinator.async_request_refresh may delay update due
        # to trying to batch requests.
        # ----------------------------------------------------------------------------
        await self.coordinator.async_refresh()

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        # Add any additional attributes you want on your sensor.
        attrs = {}
        #    attrs["last_rebooted"] = self.coordinator.get_device_parameter(
        #        self.device_id, "last_reboot"
        #    )
        # attrs["last_seen"] = datetime.utcnow()
        attrs["simple_name"] = self.device.simple_name
        if self.device.piwigo_id != 0:
            attrs["Album_Id"] = self.device.piwigo_id
            attrs["Parent_Album_Id"] = self.device.piwigo_parent_id
        # print(self.device)
        return attrs
