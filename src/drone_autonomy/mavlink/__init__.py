"""MAVLink module initialization."""

from .telemetry import MAVLinkTelemetry
from .proximity import ProximityMonitor, ProximityReading, SensorDirection

__all__ = [
    'MAVLinkTelemetry',
    'ProximityMonitor',
    'ProximityReading',
    'SensorDirection'
]
