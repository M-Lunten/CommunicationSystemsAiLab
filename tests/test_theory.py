"""The fixed engine must agree with the formulas from the lectures.

Run with:  python -m pytest tests
"""
import math

import pytest

from commsim import FrameFormat, point_to_point, shared_uplink
from commsim.reference import (GroupedAloha, RoundRobinTDMA, SlottedAloha, StopAndWaitReceiver,
                               StopAndWaitSender)
from student.mm5_link import UtopiaReceiver, UtopiaSender


def test_problem_set_1_frame_time():
    # PS1, Problem 1: 79 frames of 64 bytes at 1 kbit/s, no errors, no ARQ.
    # Our frame has one extra 'type' bit compared with Figure 1 (537 instead of 536 bits).
    fmt = FrameFormat(max_payload_bytes=64, check="crc8")
    assert fmt.data_bits(64) == 537
    r = point_to_point(UtopiaSender, UtopiaReceiver, ber=0.0)
    assert r.delivered == 79
    assert r.duration == pytest.approx(79 * 537 / 1000 + 0.010)  # + propagation of the last frame


def test_per_matches_formula():
    # Lecture 5: PER = 1 - (1 - BER)^n
    ber, n_packets = 2e-3, 3000
    r = point_to_point(UtopiaSender, UtopiaReceiver, n_packets=n_packets, payload_bytes=16,
                       ber=ber, rate_bps=1e6, seed=4)
    n_bits = FrameFormat(64, "crc8").data_bits(16)
    per = 1 - (1 - ber) ** n_bits
    assert r.detected_errors / n_packets == pytest.approx(per, abs=0.02)


def test_stop_and_wait_time_matches_formula():
    # Lecture 5: expected attempts = 1 / (1 - p); a failed attempt costs one timeout,
    # the successful one costs a round trip.
    ber, n_packets, payload = 1e-3, 3000, 32
    r = point_to_point(StopAndWaitSender, StopAndWaitReceiver, n_packets=n_packets,
                       payload_bytes=payload, ber=ber, rate_bps=1e5, prop_delay=1e-3,
                       check="crc16", seed=5)
    fmt = FrameFormat(64, "crc16")
    p_fail = 1 - (1 - ber) ** (fmt.data_bits(payload) + fmt.ack_bits)
    t_d, t_a, d = fmt.data_bits(payload) / 1e5, fmt.ack_bits / 1e5, 1e-3
    rtt = t_d + t_a + 2 * d
    timeout = 1.25 * rtt
    expected = n_packets * (rtt + p_fail / (1 - p_fail) * timeout)
    assert r.delivered == n_packets and r.duplicates == 0
    assert r.duration == pytest.approx(expected, rel=0.03)


@pytest.mark.parametrize("n,p", [(3, 1 / 3), (10, 0.1), (20, 0.05)])
def test_slotted_aloha_throughput(n, p):
    # Lecture 6: N p (1 - p)^(N - 1)
    r = shared_uplink(SlottedAloha, mac_params={"p": p}, n_users=n, n_slots=6000, seed=6)
    assert r.throughput == pytest.approx(n * p * (1 - p) ** (n - 1), abs=0.02)


def test_problem_set_2_grouped_aloha():
    # PS2, Problem 2(c): 1/2 [ (3/4)^3 + (15/16)^15 ] ~ 0.401
    r = shared_uplink(GroupedAloha, mac_params={"group_a": 4}, n_users=20, n_slots=20000, seed=8)
    theory = 0.5 * ((3 / 4) ** 3 + (15 / 16) ** 15)
    assert r.throughput == pytest.approx(theory, abs=0.015)


def test_tdma_is_collision_free_and_fair():
    r = shared_uplink(RoundRobinTDMA, n_users=4, n_slots=4000)
    assert r.slots["collision"] == 0
    assert r.throughput == pytest.approx(1.0, abs=0.01)
    assert r.fairness == pytest.approx(1.0, abs=0.01)
