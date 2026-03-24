"""The Miner integration."""
from __future__ import annotations

import sys

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_IP
from .const import DOMAIN
from .const import PYASIC_VERSION

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]


def _ensure_pyasic():
    """Ensure pyasic is installed and at the correct version (runs in executor)."""
    from importlib.metadata import version as pkg_version

    try:
        import pyasic
        if pkg_version("pyasic") != PYASIC_VERSION:
            raise ImportError("Version mismatch")
        if not hasattr(pyasic, "get_miner"):
            raise ImportError("pyasic module incomplete")
        return pyasic
    except Exception:
        pass

    from .patch import install_package
    install_package(f"pyasic=={PYASIC_VERSION}", force_reinstall=True)

    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("pyasic"):
            del sys.modules[mod_name]

    import pyasic
    return pyasic


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Miner from a config entry."""
    pyasic = await hass.async_add_executor_job(_ensure_pyasic)

    from .coordinator import MinerCoordinator
    from .services import async_setup_services

    miner_ip = config_entry.data[CONF_IP]
    miner = await pyasic.get_miner(miner_ip)

    if miner is None:
        raise ConfigEntryNotReady("Miner could not be found.")

    m_coordinator = MinerCoordinator(hass, config_entry)
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = m_coordinator

    await m_coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok
