import pytest

from fuzzy_tariff.advisor import (
    Device,
    DeviceAdvisor,
    DeviceRequest,
    plan_slots,
    urgency,
)
from fuzzy_tariff.labels import Action


def test_urgency_is_required_time_over_available_time():
    req = DeviceRequest(Device.EV, energy_kwh=22.2, deadline_hours=12, power_kw=7.4)  # 3 h of 12
    assert urgency(req) == pytest.approx(0.25)
    assert urgency(DeviceRequest(Device.EV, 80, 1)) == 1.0
    assert urgency(DeviceRequest(Device.EV, 10, 0)) == 1.0


def test_advisor_waits_on_poor_price_with_slack_and_starts_at_deadline(stage2):
    advisor = DeviceAdvisor(stage2)
    relaxed = DeviceRequest(Device.EV, energy_kwh=14.8, deadline_hours=12)  # 2 h of 12
    tight = DeviceRequest(Device.EV, energy_kwh=70, deadline_hours=8)
    assert advisor.advise(15, relaxed).action is Action.WAIT
    assert advisor.advise(15, tight).action is Action.MUST_START
    assert advisor.advise(90, relaxed).action is Action.START_NOW


def test_plan_picks_best_slots_chronologically():
    scores = [10, 90, 20, 95, 30, 85]
    assert plan_slots(scores, 3, contiguous=False) == [1, 3, 5]


def test_plan_contiguous_block_for_appliances():
    scores = [10, 90, 20, 60, 70, 65, 5]
    assert plan_slots(scores, 3, contiguous=True) == [3, 4, 5]


def test_plan_rounds_partial_hours_up_and_rejects_impossible():
    assert len(plan_slots([1, 2, 3, 4], 1.2)) == 2
    with pytest.raises(ValueError):
        plan_slots([1, 2], 5)
