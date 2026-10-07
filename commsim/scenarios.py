"""Ready-made experiments. Each function builds a network, runs it and returns Results.

point_to_point()   MM5: Alice sends a file to Bob over one link.
shared_uplink()    MM6: several users share one channel to a base station (Basil).
"""
import math

from .apps import Bernoulli, FileTransfer, Saturated, Sink, Source
from .frames import FrameFormat
from .node import MAC, Network
from .phy import BinarySymmetricChannel
from .results import collect


def point_to_point(sender, receiver, *, n_packets=79, payload_bytes=64, rate_bps=1000,
                   prop_delay=0.010, ber=0.0, check="crc8", ack_loss=0.0, timeout=None,
                   seed=1, max_time=None, **params):
    """Alice sends `n_packets` payloads of `payload_bytes` to Bob.

    sender, receiver  LinkProtocol classes (e.g. StopAndWaitSender, StopAndWaitReceiver)
    rate_bps          channel bit rate
    prop_delay        one-way propagation delay in seconds
    ber               bit error rate of the Binary Symmetric Channel
    check             error detection: "none", "parity", "crc8", "crc16", "crc32"
    ack_loss          extra probability that an ACK frame vanishes (e.g. a deep fade)
    timeout           retransmission timeout in seconds, available as ctx.params["timeout"].
                      Default: 1.25 x (time to send a DATA frame and get its ACK back).
    Any extra keyword arguments are added to ctx.params.
    """
    fmt = FrameFormat(max_payload_bytes=max(64, payload_bytes), check=check)
    t_data = fmt.data_bits(payload_bytes) / rate_bps
    t_ack = fmt.ack_bits / rate_bps
    if timeout is None:
        timeout = 1.25 * (t_data + t_ack + 2 * prop_delay)
    params = dict(params, timeout=timeout, t_data=t_data, t_ack=t_ack, prop_delay=prop_delay)
    net = Network(fmt, BinarySymmetricChannel(ber), rate_bps, prop_delay, seed, params, ack_loss)
    alice = net.add_node(1, "Alice", sender)
    bob = net.add_node(2, "Bob", receiver)
    source = FileTransfer(n_packets)
    source.attach(net, alice, bob.addr, payload_bytes)
    net.sources[(alice.addr, bob.addr)] = source
    sink = Sink(source, net)
    net.sinks[(bob.addr, alice.addr)] = sink
    source.start()
    net.sim.schedule(0.0, alice.context, bob.addr)
    if max_time is None:
        max_time = 200 * n_packets * (timeout + t_data) + 1.0
    net.sim.run(until=max_time, stop_when=lambda: sink.done)
    duration = sink.last_delivery if sink.done else net.sim.now
    label = (f"point_to_point: {n_packets} x {payload_bytes} B, {rate_bps:g} bit/s, "
             f"delay {prop_delay:g} s, BER {ber:g}, {check}")
    return collect(net, label, payload_bytes, duration)


def shared_uplink(mac, *, mac_params=None, n_users=3, traffic="saturated", n_slots=5000,
                  payload_bytes=16, rate_bps=1e6, prop_delay=1e-6, ber=0.0, check="crc16",
                  link=None, user_names=None, seed=1, **params):
    """`n_users` share one slotted channel to the base station Basil.

    mac         a MAC subclass, e.g. SlottedAloha; mac_params are passed to its constructor
    traffic     "saturated" (always data waiting), a number (Bernoulli arrivals per user
                per slot), or a list with one Source per user (Saturated(), Bernoulli(0.1),
                Bursty(0.002, 20), ...)
    link        (SenderClass, ReceiverClass) for the link layer. Default: the reference
                stop-and-wait ARQ released after MM5.
    """
    if link is None:
        from .reference import StopAndWaitReceiver, StopAndWaitSender
        link = (StopAndWaitSender, StopAndWaitReceiver)
    sender_cls, receiver_cls = link
    addr_bits = max(1, math.ceil(math.log2(n_users + 1)))
    fmt = FrameFormat(max_payload_bytes=max(16, payload_bytes), check=check, addr_bits=addr_bits)
    t_data = fmt.data_bits(payload_bytes) / rate_bps
    t_ack = fmt.ack_bits / rate_bps
    slot_time = 1.02 * (t_data + t_ack + 2 * prop_delay)
    params = dict(params, timeout=0.99 * slot_time, slot_time=slot_time)
    net = Network(fmt, BinarySymmetricChannel(ber), rate_bps, prop_delay, seed, params)
    basil = net.add_node(0, "Basil", receiver_cls)
    names = user_names or ["Zoya", "Yoshi", "Xia", "Walt", "Vera", "Ugo", "Tess", "Sam",
                           "Rami", "Quinn"]
    if isinstance(traffic, str):
        sources = [Saturated() for _ in range(n_users)]
    elif isinstance(traffic, (int, float)):
        sources = [Bernoulli(traffic) for _ in range(n_users)]
    else:
        sources = list(traffic)
        if len(sources) != n_users:
            raise ValueError("traffic list needs one Source per user")
    mac_params = mac_params or {}
    net.start_slots(slot_time, n_slots)
    for i in range(n_users):
        name = names[i] if i < len(names) else f"User{i + 1}"
        mac_obj = mac(i, n_users, net.rng, **mac_params)
        if not isinstance(mac_obj, MAC):
            raise TypeError("mac must be a subclass of commsim.MAC")
        user = net.add_node(i + 1, name, sender_cls, mac=mac_obj)
        src = sources[i]
        src.attach(net, user, basil.addr, payload_bytes)
        net.sources[(user.addr, basil.addr)] = src
        net.sinks[(basil.addr, user.addr)] = Sink(src, net)
        src.start()
        net.sim.schedule(0.0, user.context, basil.addr)
    net.sim.run(until=n_slots * slot_time)
    label = (f"shared_uplink: {n_users} users, {mac.__name__}"
             + (f"({', '.join(f'{k}={v}' for k, v in mac_params.items())})" if mac_params else "")
             + f", {n_slots} slots")
    return collect(net, label, payload_bytes, n_slots * slot_time)
