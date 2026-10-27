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


def check_mm7_encapsulation(packet_sizes):
    """Checks the packet_sizes helper (Lab MM7, part A4)."""
    cases = [((50, [20, 20, 18]), [50, 70, 90, 108]),
             ((1000, [2, 2]), [1000, 1002, 1004]),     # Lecture 7: file length + file CRC
             ((64, [0, 4]), [64, 64, 68]),
             ((1, []), [1])]
    ok = True
    for (payload, headers), expected in cases:
        given = list(headers)
        try:
            got = packet_sizes(payload, given)
        except NotImplementedError:
            print("FAIL  packet_sizes is not implemented yet")
            return False
        got_list = list(got) if isinstance(got, (list, tuple)) else got
        if given != headers:
            ok &= _report(f"packet_sizes({payload}, {headers})", False, "changed header_sizes",
                          "build a new list instead of changing the one you were given.")
            continue
        if got_list == expected:
            ok &= _report(f"packet_sizes({payload}, {headers})", True, f"{got_list}", "")
            continue
        if not isinstance(got_list, list) or len(got_list) != len(headers) + 1:
            hint = (f"return a list with one entry more than there are headers "
                    f"({len(headers) + 1} here): the payload first, then one size per layer.")
        elif got_list[0] != payload:
            hint = "the first entry is the payload on its own, before any layer adds a header."
        else:
            hint = ("each layer adds its header to the whole packet it got from the layer above, "
                    "so every entry is the previous entry plus one header.")
        ok &= _report(f"packet_sizes({payload}, {headers})", False, f"returned {got}", hint)
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok


def check_mm7_retry(retry_decision):
    """Checks the retry_decision rule (Lab MM7, part B)."""
    from .twolayer import GIVE_UP, RETRANSMIT, WAIT, normalise_decision, two_layer_link
    groups = [
        ("1 waits for the ACK", [((0, 0, 4, 2), WAIT), ((3, 0, 4, 2), WAIT), ((1, 2, 4, 2), WAIT),
                                 ((1, 0, 2, 0), WAIT)],
         "before `timeout` slots have passed, the ACK may still be on its way: wait."),
        ("2 retransmits after the timeout", [((4, 0, 4, 2), RETRANSMIT), ((5, 1, 4, 2), RETRANSMIT),
                                             ((2, 0, 2, 3), RETRANSMIT), ((9, 0, 4, 2), RETRANSMIT)],
         "once `timeout` slots have passed without an ACK, and the packet has been "
         "retransmitted fewer than max_retransmissions times, send it again."),
        ("3 gives up at the limit", [((4, 2, 4, 2), GIVE_UP), ((2, 0, 2, 0), GIVE_UP),
                                     ((7, 3, 4, 3), GIVE_UP)],
         "when the timeout has passed and the packet has already been retransmitted "
         "max_retransmissions times, stop: return 'give_up'."),
    ]
    ok = True
    for name, cases, hint in groups:
        wrong = []
        for args, expected in cases:
            try:
                raw = retry_decision(*args)
            except NotImplementedError:
                print("FAIL  retry_decision is not implemented yet")
                return False
            if normalise_decision(raw) != expected:
                wrong.append(f"retry_decision{args} returned {raw!r}, expected {expected!r}")
        ok &= _report(name, not wrong, wrong[0] if wrong else f"{len(cases)} cases right", hint)
    if ok:
        r = two_layer_link(retry_decision, reliability="LL", per=0.3, k_ll=2, t_ll=2, n_packets=200,
                           seed=3)
        attempts, last, early = {}, {}, 0
        for e in r.events:
            if e.row == "Zoya LL" and e.kind in ("tx_ok", "tx_lost"):
                attempts[e.label] = attempts.get(e.label, 0) + 1
                if e.label in last and e.slot - last[e.label] < 2:
                    early += 1
                last[e.label] = e.slot
        most = max(attempts.values())
        ok &= _report("4 in the simulator", most <= 3 and early == 0 and r.delivered > 180,
                      f"at most {most} attempts per frame (limit 3), {early} sent before the timeout, "
                      f"{r.delivered}/200 delivered",
                      "run two_layer_link with your rule and look at layer_timeline: are frames "
                      "sent too early, or too often?")
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok


def check_mm8_dv(dv_update):
    """Checks a distance-vector update (Lab MM8, question 1). Not on Problem 2: that is 1a."""
    import copy
    cases = [
        ("1 picks the cheapest neighbour",
         ("X", {"Y": 1, "Z": 4}, {"Y": {"X": 1, "Y": 0, "Z": 2, "W": 7},
                                  "Z": {"X": 4, "Y": 2, "Z": 0, "W": 1}}),
         ({"X": 0, "Y": 1, "Z": 3, "W": 5}, {"X": None, "Y": "Y", "Z": "Y", "W": "Z"}),
         "for each destination, add the link cost to each neighbour's distance and keep the "
         "smallest sum; the next hop is the neighbour that gave it."),
        ("2 itself: distance 0, no next hop",
         ("M", {"N": 3}, {"N": {"M": 3, "N": 0, "P": 2}}),
         ({"M": 0, "N": 3, "P": 5}, {"M": None, "N": "N", "P": "N"}),
         "a router reaches itself at distance 0 with next hop None, whatever its neighbours say."),
        ("3 ties and unknown destinations",
         ("X", {"P": 2, "Q": 1}, {"P": {"T": 1}, "Q": {"T": 2, "U": 4}}),
         ({"X": 0, "T": 3, "U": 5}, {"X": None, "T": "P", "U": "Q"}),
         "on a tie keep the neighbour that comes first in link_costs (use < , not <=), and "
         "only use neighbours whose vector contains the destination."),
        ("4 no neighbours",
         ("Solo", {}, {}),
         ({"Solo": 0}, {"Solo": None}),
         "with no neighbours, the table only contains the router itself."),
    ]
    ok = True
    for name, args, (want_d, want_h), hint in cases:
        given = copy.deepcopy(args)
        try:
            out = dv_update(*given)
        except NotImplementedError:
            print("FAIL  dv_update is not implemented yet")
            return False
        if given != args:
            ok &= _report(name, False, "changed its inputs", "build new dicts instead of changing "
                          "link_costs or neighbour_vectors.")
            continue
        if not (isinstance(out, tuple) and len(out) == 2):
            ok &= _report(name, False, f"returned {out!r}", "return a tuple (distances, next_hops).")
            continue
        dist, hops = out
        good = dict(dist) == want_d and dict(hops) == want_h
        ok &= _report(name, good, "right" if good else f"returned distances {dist}, next hops {hops}",
                      hint)
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok


def check_mm8_flow(advertised_window, may_send):
    """Checks the two flow-control rules (Lab MM8, question 2)."""
    from .flow import flow_control_link
    ok = True
    try:
        aw = [(args, advertised_window(*args), want) for args, want in
              (((64, 0), 64), ((64, 10), 54), ((64, 64), 0), ((8, 3), 5))]
        ms = [(args, may_send(*args), want) for args, want in
              (((0, 64), True), ((63, 64), True), ((64, 64), False), ((5, 0), False), ((70, 64), False))]
    except NotImplementedError:
        print("FAIL  advertised_window or may_send is not implemented yet")
        return False
    wrong = [f"advertised_window{a} returned {g!r}, expected {w!r}" for a, g, w in aw if g != w]
    ok &= _report("1 advertised_window", not wrong, wrong[0] if wrong else "4 cases right",
                  "the window is the free space in the receiver's buffer.")
    wrong = [f"may_send{a} returned {g!r}, expected {w!r}" for a, g, w in ms if bool(g) != w]
    ok &= _report("2 may_send", not wrong, wrong[0] if wrong else "5 cases right",
                  "the sender may send while fewer than `window` packets are in flight.")
    if ok:
        r = flow_control_link(flow_control=(advertised_window, may_send), copies=8, n_packets=20_000)
        good = r.dropped == 0 and r.processed == 20_000
        ok &= _report("3 in the simulator", good,
                      f"{r.dropped} dropped, {r.processed}/20000 processed",
                      "with flow control, no packet should ever arrive at a full buffer.")
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok


def check_mm9_cbc(cbc_encrypt, cbc_decrypt):
    """Checks CBC encryption and decryption (Lab MM9, question 1)."""
    from .crypto import DEMO_IV, DEMO_KEY, ecb_encrypt, sensor_log
    key, iv = b"check-key", bytes(range(8))
    plain = [b"ABCDEFGH", b"ABCDEFGH", b"12345678"]
    vector = [bytes.fromhex(h) for h in ("69d9b3824d290559", "efeef59f1c79370e", "d5cf130fe4668cbc")]
    given = list(plain)
    try:
        cipher = cbc_encrypt(given, key, iv)
        back = cbc_decrypt(list(vector), key, iv)
    except NotImplementedError:
        print("FAIL  cbc_encrypt or cbc_decrypt is not implemented yet")
        return False
    ok = True
    cipher = list(cipher) if isinstance(cipher, (list, tuple)) else cipher
    if given != plain:
        return _report("0 inputs", False, "cbc_encrypt changed its input list",
                       "build a new list of ciphertext blocks.")
    first_ok = isinstance(cipher, list) and len(cipher) == 3 and cipher[0] == vector[0]
    ok &= _report("1 first block", first_ok, "matches the test vector" if first_ok else
                  f"got {cipher[0].hex() if isinstance(cipher, list) and cipher else cipher!r}",
                  "C[0] = toy_encrypt_block(xor_bytes(P[0], iv), key).")
    chain_ok = first_ok and cipher == vector
    ok &= _report("2 chaining", chain_ok, "matches the test vector" if chain_ok else
                  "later blocks differ from the test vector",
                  "each next block is XORed with the previous CIPHERTEXT block before encrypting. "
                  "Note that P[0] and P[1] are equal here, but C[0] and C[1] must differ.")
    dec_ok = list(back) == plain
    ok &= _report("3 decryption", dec_ok, "recovers the test plaintext" if dec_ok else f"got {back}",
                  "P[i] = toy_decrypt_block(C[i], key) XOR C[i-1], with the IV for the first block.")
    if ok:
        log = sensor_log()
        rt = cbc_decrypt(cbc_encrypt(log, DEMO_KEY, DEMO_IV), DEMO_KEY, DEMO_IV) == log
        other_iv = cbc_encrypt(log, DEMO_KEY, bytes(8))[0] != cbc_encrypt(log, DEMO_KEY, DEMO_IV)[0]
        not_ecb = cbc_encrypt(log, DEMO_KEY, DEMO_IV) != ecb_encrypt(log, DEMO_KEY)
        ok &= _report("4 round trip on the sensor log", rt and other_iv and not_ecb,
                      "decrypt(encrypt(log)) == log, and the IV matters",
                      "check that both functions use the same key and IV, and that the IV is used.")
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok


def check_mm9_auth(respond, verify):
    """Checks the challenge-response functions (Lab MM9, question 2)."""
    from .keyexchange import dh_chat
    K, c, pub = b"K-check", b"\x00\x01challenge", 123456789
    known = "95700394c23a19fc2389b6297352476fddd304c874e3062897838b266649079f"
    try:
        r = respond(K, c, pub)
        good = verify(K, c, pub, known)
        bad = [verify(K2, c2, p2, known) for K2, c2, p2 in
               ((b"wrong key", c, pub), (K, b"other challenge", pub), (K, c, pub + 1))]
    except NotImplementedError:
        print("FAIL  respond or verify is not implemented yet")
        return False
    ok = _report("1 respond", r == known, "matches the known value" if r == known else f"returned {r!r}",
                 "hash K + challenge + str(public_value).encode() with hashlib.sha256 and return "
                 ".hexdigest().")
    ok &= _report("2 verify accepts", good is True, f"returned {good!r}",
                  "verify must return True when the response is respond(K, challenge, public_value).")
    ok &= _report("3 verify rejects", not any(bad),
                  "rejects a wrong key, a wrong challenge and a wrong public value" if not any(bad)
                  else "accepted a wrong key, challenge or public value",
                  "recompute the expected response from the arguments and compare.")
    if ok:
        honest = dh_chat(authentication=(respond, verify))
        attacked = dh_chat(mallory=True, authentication=(respond, verify), seed=5)
        ok &= _report("4 in the simulator", honest.handshake_ok is True and attacked.handshake_ok is False,
                      f"honest handshake {'succeeds' if honest.handshake_ok else 'fails'}, "
                      f"attacked one {'fails' if attacked.handshake_ok is False else 'succeeds'}",
                      "both sides must verify the response against the public value they received.")
    print("\nAll checks passed." if ok else "\nFix the failing checks and run again.")
    return ok
