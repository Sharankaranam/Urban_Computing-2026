import numpy as np
import pytest

from fuzzy_tariff.fuzzy.membership import MembershipFunction, trapmf, trimf

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


def test_triangle_known_values():
    assert trimf(25, 10, 25, 45) == pytest.approx(1.0)
    assert trimf(10, 10, 25, 45) == pytest.approx(0.0)
    assert trimf(35, 10, 25, 45) == pytest.approx(0.5)
    assert trimf(50, 10, 25, 45) == pytest.approx(0.0)


def test_trapezoid_shoulders_are_one_at_the_edge():
    assert trapmf(0, 0, 0, 10, 25) == pytest.approx(1.0)
    assert trapmf(100, 75, 90, 100, 100) == pytest.approx(1.0)
    assert trapmf(17.5, 0, 0, 10, 25) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("shape", "params"),
    [("tri", (1, 2)), ("trap", (1, 2, 3)), ("tri", (3, 2, 1)), ("tri", (1, 1, 1)), ("hex", (1,))],
)
def test_invalid_definitions_are_rejected(shape, params):
    with pytest.raises(ValueError):
        MembershipFunction(shape, params)  # type: ignore[arg-type]


@given(
    x=st.floats(-1e3, 1e3, allow_nan=False),
    a=st.floats(0, 10),
    w1=st.floats(0.1, 10),
    w2=st.floats(0.1, 10),
)
def test_triangle_always_in_unit_interval(x, a, w1, w2):
    value = float(trimf(x, a, a + w1, a + w1 + w2))
    assert 0.0 <= value <= 1.0


def test_vectorised_matches_scalar():
    xs = np.linspace(-5, 120, 51)
    mf = MembershipFunction("trap", (0, 0, 10, 25))
    assert np.allclose(mf(xs), [float(mf(x)) for x in xs])
