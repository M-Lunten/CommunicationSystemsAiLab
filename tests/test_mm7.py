"""The MM7 layer engine must agree with the lecture formulas."""
import pytest

from commsim import two_layer_link, zoya_router_yoshi
from commsim.reference import retry_decision


@pytest.fixture(scope="module")
def retry():
    return retry_decision


def test_encapsulation_sizes():
    t = zoya_router_yoshi(payload_bytes=100, transport=8, network=12, data_link=10)
    assert t.packet_bytes == 130 and t.link_bytes("link 2") == 130
    assert t.highest_layer == {"Zoya": 7, "Router": 3, "Yoshi": 7}
    assert [s.size for s in t.steps if s.node == "Yoshi"][-1] == 100


def test_router_reframes_only_link_header():
    t = zoya_router_yoshi(data_link=10, data_link_out=20)
    l1 = {h.layer: h for h in t.links["link 1"]}
    l2 = {h.layer: h for h in t.links["link 2"]}
    assert l1[2].fields != l2[2].fields and l2[2].size == 20
    assert l1[3].fields["dst"] == l2[3].fields["dst"] and l1[4].fields == l2[4].fields


def test_clean_channel(retry):
    for rel in ("LL", "HL", "both"):
        r = two_layer_link(retry, reliability=rel, per=0.0, n_packets=50)
        assert r.delivered == 50 and r.ll_retransmissions == 0 and r.hl_retransmissions == 0
        # 2 slots per packet, plus the slot in which the last ACK arrives (and, with both
        # layers, the LL ACK for the last HL ACK)
        assert r.slots == 2 * 50 + (2 if rel == "both" else 1)


@pytest.mark.parametrize("per,k", [(0.2, 2), (0.3, 1)])
def test_ll_arq_formulas(retry, per, k):
    # Lost for good only if all K+1 DATA copies are lost: per^(K+1).
    # An attempt fails if DATA or ACK is lost, q = 1 - (1-per)^2; expected attempts
    # per packet = (1 - q^(K+1)) / (1 - q).
    n = 20000
    r = two_layer_link(retry, reliability="LL", per=per, k_ll=k, n_packets=n, seed=11)
    q = 1 - (1 - per) ** 2
    assert 1 - r.reliability == pytest.approx(per ** (k + 1), abs=0.004)
    assert r.ll_transmissions / n == pytest.approx((1 - q ** (k + 1)) / (1 - q), rel=0.02)


def test_hl_arq_reliability(retry):
    n, per, k = 20000, 0.2, 2
    r = two_layer_link(retry, reliability="HL", per=per, k_hl=k, t_hl=4, n_packets=n, seed=12)
    assert 1 - r.reliability == pytest.approx(per ** (k + 1), abs=0.004)
    assert r.hl_premature == 0      # an unreliable LL never holds a packet


def test_premature_hl_timeout(retry):
    # LL: 3 attempts of 2 slots = up to 6 slots. T_HL = 4 fires while the LL is still trying.
    short = two_layer_link(retry, reliability="both", per=0.2, k_ll=2, t_ll=2, t_hl=4, seed=7)
    longer = two_layer_link(retry, reliability="both", per=0.2, k_ll=2, t_ll=2, t_hl=7, seed=7)
    assert short.hl_premature > 0
    assert longer.hl_unnecessary < short.hl_unnecessary


def test_same_channel_for_all_settings(retry):
    a = two_layer_link(retry, reliability="none", per=0.3, n_packets=500, seed=5)
    b = two_layer_link(retry, reliability="none", per=0.3, n_packets=500, seed=5)
    assert a.delivered == b.delivered
