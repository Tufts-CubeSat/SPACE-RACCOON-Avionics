import numpy as np
import pytest

import tests.cp_mock  # noqa: F401
from flight.apps.adcs.acs import bdot_controller, spin_stabilizing_controller, sun_pointing_controller
from flight.apps.adcs.consts import ControllerConst


@pytest.fixture
def tolerance() -> float:
    return 1.0e-5  # controller throttle output is quantized to 1/255


@pytest.fixture
def zero_spin_error_omega() -> np.ndarray:
    return np.linalg.inv(ControllerConst.INERTIA_MAT) @ ControllerConst.MOMENTUM_TARGET


@pytest.fixture
def larger_spin_error_omega(zero_spin_error_omega: np.ndarray) -> np.ndarray:
    return 2 * zero_spin_error_omega


@pytest.mark.parametrize(
    "omega, mag_field, expected",
    [
        (  # zero error test case
            "zero_spin_error_omega",
            np.ones(3),
            np.zeros(3),
        ),
        (  # parallel magnetic field and spin error test case
            "larger_spin_error_omega",
            "zero_spin_error_omega",
            ControllerConst.FALLBACK_CONTROL,
        ),
        (  # zero magnetic field test case
            "larger_spin_error_omega",
            np.zeros(3),
            ControllerConst.FALLBACK_CONTROL,
        ),
    ],
)
def test_nominal_spin_stabilization(
    omega: np.ndarray, mag_field: np.ndarray, expected: np.ndarray, tolerance: float, request: pytest.FixtureRequest
) -> None:
    # Get fixture values
    if isinstance(omega, str):
        omega = request.getfixturevalue(omega)
    if isinstance(mag_field, str):
        mag_field = request.getfixturevalue(mag_field)

    # Assert control input value
    result = spin_stabilizing_controller(omega, mag_field)
    assert result.shape == (3,)
    assert result == pytest.approx(expected, abs=tolerance)


@pytest.fixture
def nominal_sun_vector() -> np.ndarray:
    return np.array([0.0, 0.0, 1.0])


@pytest.fixture
def zero_pointing_error_omega(
    nominal_sun_vector: np.ndarray,
) -> np.ndarray:
    return np.linalg.norm(ControllerConst.MOMENTUM_TARGET) * np.linalg.inv(ControllerConst.INERTIA_MAT) @ nominal_sun_vector


@pytest.fixture
def larger_pointing_error_omega(
    zero_pointing_error_omega: np.ndarray,
) -> np.ndarray:
    return 2 * zero_pointing_error_omega


@pytest.mark.parametrize(
    "sun_vector, omega, mag_field, expected",
    [
        (  # zero error test case
            "nominal_sun_vector",
            "zero_pointing_error_omega",
            np.ones(3),
            ControllerConst.FALLBACK_CONTROL,
        ),
        (  # parallel magnetic field and pointing error test case
            "nominal_sun_vector",
            "larger_pointing_error_omega",
            "nominal_sun_vector",
            ControllerConst.FALLBACK_CONTROL,
        ),
        (  # zero sun vector test case
            np.zeros(3),
            "larger_pointing_error_omega",
            np.ones(3),
            ControllerConst.FALLBACK_CONTROL,
        ),
        (  # zero magnetic field test case
            "nominal_sun_vector",
            "larger_pointing_error_omega",
            np.zeros(3),
            ControllerConst.FALLBACK_CONTROL,
        ),
        (  # zero sun vector and magnetic field tEst case
            np.zeros(3),
            "larger_pointing_error_omega",
            np.zeros(3),
            ControllerConst.FALLBACK_CONTROL,
        ),
    ],
)
def test_nominal_sun_pointing(
    sun_vector: np.ndarray,
    omega: np.ndarray,
    mag_field: np.ndarray,
    expected: np.ndarray,
    tolerance: float,
    request: pytest.FixtureRequest,
) -> None:
    # Get fixture values
    if isinstance(sun_vector, str):
        sun_vector = request.getfixturevalue(sun_vector)
    if isinstance(omega, str):
        omega = request.getfixturevalue(omega)
    if isinstance(mag_field, str):
        mag_field = request.getfixturevalue(mag_field)

    # Assert control input value
    result = sun_pointing_controller(sun_vector, omega, mag_field)
    assert result.shape == (3,)
    assert result == pytest.approx(expected, abs=tolerance)


@pytest.fixture
def invalid_dims() -> list[int]:
    return [0, 1, 2, 4, 5, 6, 7, 8, 9]


@pytest.mark.parametrize(
    "valid_omega, valid_mag_field, expected",
    [
        (
            np.ones(3),
            np.ones(3),
            ControllerConst.FALLBACK_CONTROL,
        )
    ],
)
def test_invalid_dim_spin_stabilization(
    invalid_dims: list[int],
    valid_omega: np.ndarray,
    valid_mag_field: np.ndarray,
    expected: np.ndarray,
    tolerance: float,
) -> None:
    for i in invalid_dims:
        # Test angular velocity with invalid dimensions
        invalid_omega = np.ones(i)
        result = spin_stabilizing_controller(invalid_omega, valid_omega)
        assert result == pytest.approx(expected, abs=tolerance)

        # Test magnetic field with invalid dimensions
        invalid_mag_field = np.ones(i)
        result = spin_stabilizing_controller(valid_mag_field, invalid_mag_field)
        assert result == pytest.approx(expected, abs=tolerance)


@pytest.mark.parametrize(
    "valid_omega, valid_mag_field, expected",
    [
        (
            np.ones(3),
            np.ones(3),
            ControllerConst.FALLBACK_CONTROL,
        )
    ],
)
def test_invalid_dim_sun_pointing(
    invalid_dims: list[int],
    nominal_sun_vector: np.ndarray,
    valid_omega: np.ndarray,
    valid_mag_field: np.ndarray,
    expected: np.ndarray,
    tolerance: float,
) -> None:
    for i in invalid_dims:
        # Test sun vector with invalid dimensions
        invalid_sun_vector = np.ones(i)
        result = sun_pointing_controller(invalid_sun_vector, valid_omega, valid_mag_field)
        assert result == pytest.approx(expected, abs=tolerance)

        # Test angular velocity with invalid dimensions
        invalid_omega = np.ones(i)
        result = sun_pointing_controller(nominal_sun_vector, invalid_omega, valid_mag_field)
        assert result == pytest.approx(expected, abs=tolerance)

        # Test magnetic field with invalid dimensions
        invalid_mag_field = np.ones(i)
        result = sun_pointing_controller(nominal_sun_vector, valid_omega, invalid_mag_field)
        assert result == pytest.approx(expected, abs=tolerance)


# ---------------------------------------------------------------------------------------------------------------------
# B-dot detumbling controller (added for the familiarization exercises)
# ---------------------------------------------------------------------------------------------------------------------


def _linear_mag_buffer(b0: np.ndarray, b_rate: np.ndarray, dt: float) -> np.ndarray:
    """6 magnetometer samples (oldest first) of a field changing at a constant rate b_rate [T/s]."""
    return np.array([b0 + b_rate * dt * k for k in range(6)])


@pytest.mark.parametrize(
    "b_rate",
    [
        np.array([1.0e-6, 0.0, 0.0]),
        np.array([0.0, -2.0e-6, 0.0]),
        np.array([1.0e-6, 2.0e-6, -0.5e-6]),
    ],
)
def test_bdot_opposes_field_change(b_rate: np.ndarray) -> None:
    b0 = np.array([20.0e-6, -10.0e-6, 30.0e-6])  # Earth's field in LEO is a few tens of micro-Tesla
    u = bdot_controller(_linear_mag_buffer(b0, b_rate, dt=0.5), dt=0.5)

    assert u.shape == (3,)
    assert np.linalg.norm(u) < 1.0, "throttle must be soft-clipped below 1"
    # The commanded dipole must point opposite to dB/dt
    assert u / np.linalg.norm(u) == pytest.approx(-b_rate / np.linalg.norm(b_rate), abs=1e-6)


def test_bdot_constant_field_gives_zero_control() -> None:
    b0 = np.array([20.0e-6, -10.0e-6, 30.0e-6])
    u = bdot_controller(_linear_mag_buffer(b0, np.zeros(3), dt=0.5), dt=0.5)
    assert u == pytest.approx(np.zeros(3), abs=1e-12)


@pytest.mark.parametrize("shape, dt", [((5, 3), 0.5), ((6, 2), 0.5), ((6, 3), 0.0), ((6, 3), -1.0)])
def test_bdot_invalid_inputs(shape, dt) -> None:
    result = bdot_controller(np.ones(shape), dt)
    assert result == pytest.approx(ControllerConst.FALLBACK_CONTROL)
