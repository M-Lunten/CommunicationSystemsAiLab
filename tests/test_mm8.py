"""The MM8 engines must agree with Lecture 8 and Problem Set 4."""
import pytest

from commsim import chain_routing, distance_vector, flow_control_link
from commsim import reference as sol


def test_receiver_capacity_problem_3():
    # PS4, Problem 3 (official solution): 4 copies x 10 instructions at 1000 MIPS = 40 ns per
    # 64-bit packet -> 1.6 Gbit/s, so a 1 Gbit/s link loses nothing.
    r = flow_control_link(copies=4, n_packets=20_000)
    assert r.receiver_capacity_gbps == pytest.approx(1.6)
    assert r.dropped == 0


def test_overload_drops_the_excess():
    r = flow_control_link(copies=8)
    assert r.receiver_capacity_gbps == pytest.approx(0.8)
    assert r.drop_fraction == pytest.approx(1 - 0.8 / 1.0, abs=0.002)
    assert r.goodput_gbps == pytest.approx(0.8, rel=1e-3)


def test_bellman_ford_chain_converges():
    r = chain_routing(sol.dv_update, fail=None)
    assert r.rounds_to_start == 4                      # diameter of the 5-node chain
    assert r.distances("Zoya") == [4]


def test_count_to_infinity_and_poisoned_reverse():
    assert chain_routing(sol.dv_update).rounds_after_failure == 15
    assert chain_routing(sol.dv_update, poisoned_reverse=True).rounds_after_failure == 4


def test_link_failure_with_alternative_route():
    # A square: when A-B fails, A reaches B via C-D at cost 3, no counting to infinity.
    links = {("A", "B"): 1, ("B", "D"): 1, ("D", "C"): 1, ("C", "A"): 1}
    r = distance_vector(sol.dv_update, links, fail=("A", "B"))
    assert r.distances("A")[-1] == 3


def test_window_limits_goodput_to_window_per_rtt():
    # Each packet holds a window slot for transmission + RTT + processing = 10.104 us.
    fc = (sol.advertised_window, sol.may_send)
    for w in (32, 64, 128):
        r = flow_control_link(copies=4, rtt_us=10, buffer_packets=w, flow_control=fc, n_packets=50_000)
        assert r.dropped == 0
        assert r.goodput_gbps == pytest.approx(w * 64 / 10_104, rel=0.01)
