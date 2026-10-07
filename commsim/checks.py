"""Self-checks students run after implementing their part of a lab.

They say *what* is wrong and give a hint, never the code.
"""
from .scenarios import point_to_point, shared_uplink


def _report(name, ok, detail, hint):
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        print(f"      hint: {hint}")
    return ok


def check_mm5(sender, receiver):
    """Checks a stop-and-wait ARQ implementation (Lab MM5, part B)."""
    results = []
    r = point_to_point(sender, receiver, n_packets=20, payload_bytes=8, rate_bps=10_000,
                       prop_delay=0.001, ber=0.0, check="crc16")
    results.append(_report(
        "1 perfect channel", r.delivered == 20 and r.duplicates == 0 and r.retransmissions == 0,
        f"{r.delivered}/20 delivered, {r.duplicates} duplicates, {r.retransmissions} retransmissions",
        "with no errors every frame should be sent once and ACKed. Does the sender move on "
        "to the next payload when the ACK arrives?"))
    r = point_to_point(sender, receiver, n_packets=200, payload_bytes=8, rate_bps=10_000,
                       prop_delay=0.001, ber=3e-3, check="crc16", seed=2)
    results.append(_report(
        "2 bit errors", r.delivered == 200 and r.undetected_errors == 0,
        f"{r.delivered}/200 delivered, {r.undetected_errors} corrupted",
        "some DATA frames arrive with check_ok == False. Does the receiver ignore them, and "
        "does the sender retransmit when its timer expires?"))
    r = point_to_point(sender, receiver, n_packets=200, payload_bytes=8, rate_bps=10_000,
                       prop_delay=0.001, ber=0.0, ack_loss=0.3, check="crc16", seed=3)
    results.append(_report(
        "3 lost ACKs", r.delivered == 200 and r.duplicates == 0,
        f"{r.delivered}/200 delivered, {r.duplicates} duplicates",
        "when an ACK is lost, Bob receives the same DATA frame again. How can he tell it "
        "is a copy and not new data (Lecture 5, 'ARQ with sequence number')? And does he "
        "still ACK the copy, so Alice can move on?"))
    print("\nAll checks passed." if all(results) else "\nFix the failing checks and run again.")
    return all(results)


def check_mm6_aloha(mac_class, tolerance=0.03):
    """Compares a slotted ALOHA MAC (parameter p) with N p (1-p)^(N-1) (Lab MM6, part B)."""
    ok = True
    for n, p in ((2, 0.5), (5, 0.2), (10, 0.1), (10, 0.3)):
        r = shared_uplink(mac_class, mac_params={"p": p}, n_users=n, n_slots=4000, seed=7)
        theory = n * p * (1 - p) ** (n - 1)
        ok &= _report(f"N={n:>2}, p={p}", abs(r.throughput - theory) <= tolerance,
                      f"simulated {r.throughput:.3f}, theory {theory:.3f}",
                      "in every slot where it has a frame, each node should transmit with "
                      "probability p, independently of the others and of what happened before.")
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok
