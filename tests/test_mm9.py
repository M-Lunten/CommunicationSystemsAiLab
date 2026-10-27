"""The MM9 security engine must agree with Lecture 9 and Problem Set 5.

Tests that need the student's functions use trial/mm9_security_solved.py (instructor-only,
kept out of the public repo until the reference is released) and are skipped without it.
"""
import importlib.util
import os
from pathlib import Path

import pytest

from commsim import (DEMO_IV, DEMO_KEY, PS5_PROBLEM6, damaged_blocks, dh_chat, dh_public, dh_shared,
                     drop_block, ecb_decrypt, ecb_encrypt, eve_change, flip_bit, meter_message, read_meter,
                     sensor_log, toy_decrypt_block, toy_encrypt_block)

SOLVED = Path(__file__).resolve().parents[1] / "trial" / "mm9_security_solved.py"


@pytest.fixture(scope="module")
def sol():
    if not SOLVED.exists():
        pytest.skip("trial/mm9_security_solved.py not present (instructor-only)")
    spec = importlib.util.spec_from_file_location("mm9_solved", SOLVED)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_toy_cipher_is_a_permutation_with_avalanche():
    for _ in range(200):
        block = os.urandom(8)
        assert toy_decrypt_block(toy_encrypt_block(block, DEMO_KEY), DEMO_KEY) == block
    a = toy_encrypt_block(b"AAAAAAAA", DEMO_KEY)
    b = toy_encrypt_block(b"AAAAAAAB", DEMO_KEY)
    assert sum(bin(x ^ y).count("1") for x, y in zip(a, b)) > 16      # about half of 64 bits


def test_ecb_shows_repetitions_and_damages_one_block():
    log = sensor_log()
    c = ecb_encrypt(log, DEMO_KEY)
    assert len(set(log)) == len(set(c)) == 3
    assert damaged_blocks(log, ecb_decrypt(flip_bit(c, 20, 5), DEMO_KEY)) == [20]
    assert damaged_blocks(log, ecb_decrypt(drop_block(c, 20), DEMO_KEY), lost=20) == [20]


def test_cbc_hides_repetitions_and_damages_two_blocks(sol):
    log = sensor_log()
    c = sol.cbc_encrypt(log, DEMO_KEY, DEMO_IV)
    assert len(set(c)) == 64
    assert damaged_blocks(log, sol.cbc_decrypt(flip_bit(c, 20, 5), DEMO_KEY, DEMO_IV)) == [20, 21]
    assert damaged_blocks(log, sol.cbc_decrypt(drop_block(c, 20), DEMO_KEY, DEMO_IV), lost=20) == [20, 21]


def test_iv_bitflip_beats_unkeyed_crc(sol):
    c = sol.cbc_encrypt(meter_message("0100"), DEMO_KEY, DEMO_IV)
    iv, c2 = eve_change(DEMO_IV, c, fix_crc=False)
    assert read_meter(sol.cbc_decrypt(c2, DEMO_KEY, iv)) == ("0900", False)
    iv, c2 = eve_change(DEMO_IV, c, fix_crc=True)
    assert read_meter(sol.cbc_decrypt(c2, DEMO_KEY, iv)) == ("0900", True)


def test_diffie_hellman_small_and_problem_6():
    assert (dh_public(5, 6, 23), dh_public(5, 15, 23)) == (8, 19)
    assert dh_shared(19, 6, 23) == dh_shared(8, 15, 23) == 2
    P = PS5_PROBLEM6
    alpha, beta = dh_public(P["g"], P["a"], P["p"]), dh_public(P["g"], P["b"], P["p"])
    assert str(alpha).startswith("18068576978407265233225867218209113584894")   # official solution
    assert str(beta).startswith("518386956790041579928056815914221837599234")
    assert str(dh_shared(beta, P["a"], P["p"])).startswith("6135240515772232051231812024812")


def test_man_in_the_middle():
    honest, attacked = dh_chat(), dh_chat(mallory=True)
    assert honest.same_key and honest.mallory_read == 0 and honest.delivered_unchanged == 10
    assert not attacked.same_key and attacked.mallory_read == 10 and attacked.delivered_unchanged == 10


def test_authentication_stops_mallory(sol):
    auth = (sol.respond, sol.verify)
    for seed in range(5):
        assert dh_chat(authentication=auth, seed=seed).handshake_ok is True
        r = dh_chat(mallory=True, authentication=auth, seed=seed)
        assert r.handshake_ok is False and r.mallory_read == 0
