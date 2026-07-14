from unittest.mock import patch

from otklik_backend.setup.hardware import HardwareProbe, HardwareSpecs, HardwareTier


def _probe_with(ram_bytes: int, cores: int) -> HardwareSpecs:
    with (
        patch("otklik_backend.setup.hardware.psutil.virtual_memory") as memory,
        patch("otklik_backend.setup.hardware.psutil.cpu_count", return_value=cores),
    ):
        memory.return_value.total = ram_bytes
        return HardwareProbe().probe()


GB = 1024**3


def test_capable_machine() -> None:
    specs = _probe_with(ram_bytes=32 * GB, cores=16)
    assert specs.tier == HardwareTier.CAPABLE
    assert specs.cores == 16
    assert specs.ram_gb == 32.0


def test_weak_on_low_ram() -> None:
    assert _probe_with(ram_bytes=8 * GB, cores=16).tier == HardwareTier.WEAK


def test_weak_on_few_cores() -> None:
    assert _probe_with(ram_bytes=32 * GB, cores=4).tier == HardwareTier.WEAK


def test_threshold_is_inclusive() -> None:
    # Ровно порог — проходит: 16 ГБ и 8 ядер это «сильная машина».
    assert _probe_with(ram_bytes=16 * GB, cores=8).tier == HardwareTier.CAPABLE


def test_just_below_threshold_is_weak() -> None:
    assert _probe_with(ram_bytes=15 * GB, cores=8).tier == HardwareTier.WEAK


def test_unknown_core_count_is_weak() -> None:
    # psutil.cpu_count() возвращает None на экзотических платформах — не
    # выдаём такой машине кредит доверия.
    assert _probe_with(ram_bytes=32 * GB, cores=None).tier == HardwareTier.WEAK
