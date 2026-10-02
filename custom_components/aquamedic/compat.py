"""Imports whose home moved between Home Assistant releases.

Home Assistant 2026.10 replaced voluptuous with probatio (same API, and its
``Invalid`` still derives from the voluptuous one) and typed its own
functions accordingly: a schema built with voluptuous is refused by the type
checker where a probatio one is expected. It also moved the entity enums of
each platform to a ``const`` module and stopped re-exporting them from the
platform package.

Everything is resolved here, once, so the rest of the integration imports
from a single place whatever the installed version:

    from .compat import BinarySensorDeviceClass, vol
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    # The type checker runs against the latest Home Assistant.
    import probatio as vol
    from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
else:
    try:
        import probatio as vol
    except ImportError:  # pragma: no cover - Home Assistant without probatio
        import voluptuous as vol

    try:
        from homeassistant.components.binary_sensor.const import (
            BinarySensorDeviceClass,
        )
    except ImportError:  # pragma: no cover - Home Assistant < 2026.10
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

__all__ = ["BinarySensorDeviceClass", "vol"]
