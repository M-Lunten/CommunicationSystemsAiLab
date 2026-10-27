"""Diffie-Hellman and the man in the middle (MM9, Question 2).

Zoya and Yoshi agree on a key with Diffie-Hellman (Problem Set 5, Problems 3 and 6) over a
router, and then chat, encrypted with that key. If the router is Mallory, she can replace
both public values with her own, agree on one key with Zoya and another with Yoshi, and
read and re-encrypt every message while forwarding it unchanged.

Authentication (Problem 4): Zoya and Yoshi share a pre-shared key K. Each sends a random
challenge with its public value, and each answers the other's challenge with
respond(K, challenge, own_public_value). The other side checks the answer with verify(...),
using the public value it actually received. Mallory does not know K.

Chat messages are encrypted with a simple SHA-256 keystream, keyed with a hash of the
Diffie-Hellman key: enough for this lab, not a real protocol.
"""
import hashlib
import random
from dataclasses import dataclass, field

# Problem Set 5, Problem 6 (a 1536-bit prime, generator 2, and Alice's and Bob's secrets)
PS5_PROBLEM6 = dict(
    p=int("24103124269210325885520760221975660748569505485024599426541169419581088316826122288900"
          "93858261341614673227141477904012196503648957050582631942730706805009223062734745341073"
          "40669624601458936165977404102716924945320037872943417032584377865919814376319377685986"
          "95240889401955773461198435453015470437472077499697637500843089263392955599688824578724"
          "12993810129130294592999947926365264059284647209730384947211681434464714438488520940127"
          "459844288859336526896320919633919"),
    g=2,
    a=int("97210744383703379624586431620045824684690459848898160585676589047885308824689734548732"
          "84910377102192220389309433658486261941098303091793930182167633275721201247601400180386"
          "73999837643377590434413866611132403979547150659053897355593394492586978400044375465657"
          "29602759294834958921641536372266836132868958899654137009755909033513767641159594933585"
          "73417971489261516942995759702928098053144314470434694474859576699499890902023202343378"
          "90323293401862304986599884732815"),
    b=int("12019233252903990344598522535774963020395770409445296724034378433497976840167805970589"
          "96096222194829095187338772810211599683145448229924322683949099971376344041217796586150"
          "87734205322664846191267105664149142275601037153366961932103798505750477303883783482661"
          "80934946139100479831339835896583443691529372703954589071507717917136906770122077739814"
          "26229848866213808560873610341860175086169841734026421386775383467935919142709819588711"
          "2064503104510489610448294420720"),
)

CHAT = ["Hi Yoshi, are we still on for Friday?", "Yes! 18:00 at the station?",
        "Perfect. Can you bring the projector?", "Sure. Do you have the access code?",
        "It is 4711. Don't tell anyone.", "Got it. See you then.",
        "Wait, the bank details for the deposit:", "Send them, I'll pay tonight.",
        "DK50 0040 0440 1162 43", "Paid. Thanks!"]


def dh_public(g, secret, p):
    """Public value g^secret mod p."""
    return pow(g, secret, p)


def dh_shared(other_public, secret, p):
    """Shared key: (the other side's public value)^secret mod p."""
    return pow(other_public, secret, p)


def _sym_key(dh_key):
    return hashlib.sha256(str(dh_key).encode()).digest()


def _seal(key, nonce, data):
    stream = b""
    counter = 0
    while len(stream) < len(data):
        stream += hashlib.sha256(key + nonce.to_bytes(8, "big") + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(x ^ y for x, y in zip(data, stream))


def _fingerprint(dh_key):
    return hashlib.sha256(str(dh_key).encode()).hexdigest()[:12]


@dataclass
class ChatResults:
    scenario: str
    mallory: bool
    authentication: bool
    zoya_key: int
    yoshi_key: int
    handshake_ok: object          # True / False, or None without authentication
    rejected_by: list             # who refused the handshake
    messages_sent: int
    delivered_unchanged: int
    mallory_read: int
    mallory_read_texts: list = field(default_factory=list)
    transcript: list = field(default_factory=list, repr=False)   # (time, from, to, label, kind)

    @property
    def same_key(self):
        return self.zoya_key == self.yoshi_key

    def summary(self):
        hs = ("not used" if self.handshake_ok is None else "succeeded" if self.handshake_ok
              else f"FAILED (rejected by {', '.join(self.rejected_by)})")
        lines = [self.scenario,
                 f"  Zoya's key           {_fingerprint(self.zoya_key)}...   (fingerprint)",
                 f"  Yoshi's key          {_fingerprint(self.yoshi_key)}...",
                 f"  same key             {'yes' if self.same_key else 'no'}",
                 f"  authentication       {hs}",
                 f"  messages sent        {self.messages_sent}",
                 f"  arrived unchanged    {self.delivered_unchanged}",
                 f"  Mallory read         {self.mallory_read}"]
        for text in self.mallory_read_texts[:3]:
            lines.append(f"      e.g. \"{text}\"")
        return "\n".join(lines)

    def __str__(self):
        return self.summary()

    def _repr_pretty_(self, p, cycle):
        p.text(self.summary())


def dh_chat(*, mallory=False, authentication=None, psk=b"Zoya+Yoshi pre-shared key", n_messages=10,
            seed=9, p=PS5_PROBLEM6["p"], g=PS5_PROBLEM6["g"]):
    """Zoya and Yoshi agree on a key with Diffie-Hellman and send `n_messages` chat messages.

    mallory          True: the router in the middle is Mallory (she replaces public values,
                     then reads and re-encrypts every message, forwarding it unchanged)
    authentication   None, or (respond, verify): your two functions, used with the
                     pre-shared key `psk` that Zoya and Yoshi (but not Mallory) know
    seed             fixes all secrets and challenges
    """
    rng = random.Random(seed)
    secret = lambda: rng.randrange(2, p - 2)
    a, b, m1, m2 = secret(), secret(), secret(), secret()
    A, B = dh_public(g, a, p), dh_public(g, b, p)
    M1, M2 = dh_public(g, m1, p), dh_public(g, m2, p)
    mid = "Mallory" if mallory else "Router"
    t = 0
    transcript = []

    def hop(frm, to, label, kind="data"):
        nonlocal t
        transcript.append((t, frm, to, label, kind))
        t += 1

    # Diffie-Hellman, with a challenge each if authentication is on
    c_zoya = rng.randbytes(16)
    c_yoshi = rng.randbytes(16)
    hop("Zoya", mid, "A" + (", challenge cZ" if authentication else ""), "key")
    A_at_yoshi = M2 if mallory else A
    hop(mid, "Yoshi", ("M2" if mallory else "A") + (", cZ" if authentication else ""), "key")
    hop("Yoshi", mid, "B" + (", cY, respond(K, cZ, B)" if authentication else ""), "key")
    B_at_zoya = M1 if mallory else B
    hop(mid, "Zoya", ("M1" if mallory else "B") + (", cY, response" if authentication else ""), "key")
    zoya_key, yoshi_key = dh_shared(B_at_zoya, a, p), dh_shared(A_at_yoshi, b, p)

    handshake_ok, rejected = None, []
    if authentication is not None:
        respond, verify = authentication
        r_yoshi = respond(psk, c_zoya, B)                 # Yoshi answers with his own value
        if not verify(psk, c_zoya, B_at_zoya, r_yoshi):   # Mallory forwards it; she cannot make a new one
            rejected.append("Zoya")
        r_zoya = respond(psk, c_yoshi, A)
        hop("Zoya", mid, "respond(K, cY, A)", "key")
        hop(mid, "Yoshi", "response", "key")
        if not verify(psk, c_yoshi, A_at_yoshi, r_zoya):
            rejected.append("Yoshi")
        handshake_ok = not rejected

    sent = unchanged = read = 0
    read_texts = []
    if handshake_ok is not False:
        k_zoya, k_yoshi = _sym_key(zoya_key), _sym_key(yoshi_key)
        k_mz, k_my = _sym_key(dh_shared(A, m1, p)), _sym_key(dh_shared(B, m2, p))
        for i, text in enumerate(CHAT[:n_messages]):
            frm, to = ("Zoya", "Yoshi") if i % 2 == 0 else ("Yoshi", "Zoya")
            k_from, k_to = (k_zoya, k_yoshi) if frm == "Zoya" else (k_yoshi, k_zoya)
            box = _seal(k_from, i, text.encode())
            sent += 1
            hop(frm, mid, f"msg {i + 1}")
            if mallory:
                k_in, k_out = (k_mz, k_my) if frm == "Zoya" else (k_my, k_mz)
                plain = _seal(k_in, i, box)
                try:
                    read_texts.append(plain.decode())
                    read += 1
                except UnicodeDecodeError:
                    pass
                box = _seal(k_out, i, plain)
            hop(mid, to, f"msg {i + 1}")
            if _seal(k_to, i, box) == text.encode():
                unchanged += 1
    label = (f"dh_chat: {'Mallory in the middle' if mallory else 'honest router'}, "
             f"{'with' if authentication else 'without'} authentication, seed {seed}")
    return ChatResults(label, mallory, authentication is not None, zoya_key, yoshi_key, handshake_ok,
                       rejected, sent, unchanged, read, read_texts, transcript)
