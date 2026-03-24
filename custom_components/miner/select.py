"""A selector for the miner's mining mode."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pyasic

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MinerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator: MinerCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    await coordinator.async_config_entry_first_refresh()
    if (
        coordinator.miner.supports_power_modes
        and not coordinator.miner.supports_autotuning
    ):
        async_add_entities(
            [
                MinerPowerModeSwitch(
                    coordinator=coordinator,
                )
            ]
        )


class MinerPowerModeSwitch(CoordinatorEntity[MinerCoordinator], SelectEntity):
    """A selector for the miner's mining mode."""

    def __init__(
        self,
        coordinator: MinerCoordinator,
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"{self.coordinator.data['mac']}-power-mode"

    @property
    def name(self) -> str | None:
        return f"{self.coordinator.config_entry.title} power mode"

    @property
    def device_info(self) -> entity.DeviceInfo:
        return entity.DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.data["mac"])},
            manufacturer=self.coordinator.data["make"],
            model=self.coordinator.data["model"],
            sw_version=self.coordinator.data["fw_ver"],
            name=f"{self.coordinator.config_entry.title}",
        )

    @property
    def current_option(self) -> str | None:
        try:
            config = self.coordinator.data.get("config")
            if config and hasattr(config, "mining_mode"):
                return str(config.mining_mode.mode).title()
        except (AttributeError, TypeError):
            pass
        return None

    @property
    def options(self) -> list[str]:
        return ["Normal", "High", "Low"]

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        from pyasic.config.mining import MiningModeHPM, MiningModeLPM, MiningModeNormal

        option_map = {
            "High": MiningModeHPM,
            "Normal": MiningModeNormal,
            "Low": MiningModeLPM,
        }
        cfg = await self.coordinator.miner.get_config()
        cfg.mining_mode = option_map[option]()
        await self.coordinator.miner.send_config(cfg)
