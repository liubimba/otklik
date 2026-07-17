from enum import Enum

import psutil
from pydantic import BaseModel

from otklik_backend.setup.constants import MIN_CORES, MIN_RAM_GB

BYTES_PER_GB = 1024**3


class HardwareTier(str, Enum):
    CAPABLE = "capable"
    WEAK = "weak"


class HardwareSpecs(BaseModel):
    ram_gb: float
    cores: int
    tier: HardwareTier


class HardwareProbe:
    def __init__(
        self, min_ram_gb: int = MIN_RAM_GB, min_cores: int = MIN_CORES
    ) -> None:
        self._min_ram_gb = min_ram_gb
        self._min_cores = min_cores

    def probe(self) -> HardwareSpecs:
        ram_gb = psutil.virtual_memory().total / BYTES_PER_GB
        cores = psutil.cpu_count() or 0
        capable = ram_gb >= self._min_ram_gb and cores >= self._min_cores
        return HardwareSpecs(
            ram_gb=round(ram_gb, 1),
            cores=cores,
            tier=HardwareTier.CAPABLE if capable else HardwareTier.WEAK,
        )
