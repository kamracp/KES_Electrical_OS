from decimal import Decimal

import pytest

from app.domain.electrical.sources.ups_engine import (
    calculate_ups_sizing,
)
from app.domain.electrical.sources.ups_models import (
    UPSRedundancyMode,
    UPSSizingInput,
)
from app.domain.electrical.sources.ups_results import (
    UPSSizingStatus,
)


def _build_input(
    **overrides: object,
) -> UPSSizingInput:
    values: dict[str, object] = {
        "code": "UPS-01",
        "name": "Critical Process UPS",
        "critical_load_kw": Decimal("120"),
        "load_power_factor": Decimal("0.90"),
        "ups_efficiency": Decimal("0.94"),
        "inverter_overload_factor": Decimal("1"),
        "future_growth_factor": Decimal("1.10"),
        "design_margin_factor": Decimal("1.20"),
        "ambient_derating_factor": Decimal("0.95"),
        "altitude_derating_factor": Decimal("1"),
        "required_runtime_minutes": Decimal("30"),
        "available_unit_ratings_kva": (
            Decimal("80"),
            Decimal("100"),
            Decimal("120"),
            Decimal("160"),
            Decimal("200"),
        ),
        "duty_modules": 2,
        "redundant_modules": 1,
        "redundancy_mode": UPSRedundancyMode.N_PLUS_1,
    }

    values.update(overrides)

    return UPSSizingInput(**values)


def test_calculate_ups_sizing_selects_standard_rating() -> None:
    result = calculate_ups_sizing(
        _build_input()
    )

    assert result.status is UPSSizingStatus.SELECTED
    assert result.base_load_kva == Decimal("133.33")
    assert result.design_load_kva == Decimal("176.00")
    assert (
        result.derated_required_capacity_kva
        == Decimal("185.26")
    )
    assert (
        result.required_capacity_per_duty_module_kva
        == Decimal("92.63")
    )
    assert result.selected_unit_rating_kva == Decimal("100.00")
    assert result.duty_capacity_kva == Decimal("200.00")
    assert (
        result.total_installed_capacity_kva
        == Decimal("300.00")
    )
    assert result.spare_capacity_kva == Decimal("14.74")
    assert result.loading_percent == Decimal("92.63")
    assert result.total_installed_modules == 3


def test_calculate_ups_sizing_calculates_battery_energy() -> None:
    result = calculate_ups_sizing(
        _build_input()
    )

    assert (
        result.estimated_output_energy_kwh
        == Decimal("60.00")
    )
    assert (
        result.estimated_dc_energy_kwh
        == Decimal("63.83")
    )


def test_calculate_ups_sizing_returns_no_rating_status() -> None:
    result = calculate_ups_sizing(
        _build_input(
            available_unit_ratings_kva=(
                Decimal("40"),
                Decimal("60"),
                Decimal("80"),
            ),
        )
    )

    assert (
        result.status
        is UPSSizingStatus.NO_STANDARD_RATING_AVAILABLE
    )
    assert result.selected_unit_rating_kva is None
    assert result.duty_capacity_kva is None
    assert result.total_installed_capacity_kva is None
    assert result.spare_capacity_kva is None
    assert result.loading_percent is None


def test_calculate_ups_sizing_rejects_invalid_input_type() -> None:
    with pytest.raises(
        TypeError,
        match="sizing_input must be a UPSSizingInput instance",
    ):
        calculate_ups_sizing("invalid")  # type: ignore[arg-type]


def test_ups_input_requires_n_plus_one_module() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one redundant module",
    ):
        _build_input(
            redundant_modules=0,
            redundancy_mode=UPSRedundancyMode.N_PLUS_1,
        )


def test_ups_input_requires_ascending_ratings() -> None:
    with pytest.raises(
        ValueError,
        match="ascending order",
    ):
        _build_input(
            available_unit_ratings_kva=(
                Decimal("100"),
                Decimal("80"),
            ),
        )


def test_ups_input_rejects_float_values() -> None:
    with pytest.raises(
        TypeError,
        match="critical_load_kw must be a Decimal",
    ):
        _build_input(
            critical_load_kw=120.0,
        )
