import pytest

from protocol import (
    PARAM_LEN,
    TRACE_STEPS,
    Cmd,
    FrameError,
    FrameParser,
    checksum,
    decode,
    encode,
    pack_int8,
    pack_params,
    pack_q88,
    pack_read_block,
    pack_read_record,
    pack_read_trace,
    pack_run,
    pack_set_input,
    pack_write_weights,
    unpack_counts,
    unpack_int8,
    unpack_q88,
    unpack_records,
    unpack_status,
    unpack_trace,
)


def test_known_vector():
    # cmd 0x01, len 2, data 01 02 -> checksum = 0x01 + 0x02 + (0x01 + 0x02) = 0x06
    assert encode(0x01, b"\x01\x02") == bytes([0xA5, 0x01, 0x02, 0x01, 0x02, 0x06])


def test_empty_payload():
    assert encode(Cmd.RUN) == bytes([0xA5, 0x04, 0x00, 0x04])
    assert decode(encode(Cmd.RUN)) == (Cmd.RUN, b"")


def test_round_trip_all_lengths():
    for n in range(0, 256, 17):
        data = bytes((i * 37) & 0xFF for i in range(n))
        cmd, out = decode(encode(Cmd.WRITE_WEIGHTS, data))
        assert cmd == Cmd.WRITE_WEIGHTS and out == data


def test_encode_rejects_too_long():
    with pytest.raises(ValueError):
        encode(0x02, bytes(256))


def test_decode_rejects_bad_checksum():
    frame = bytearray(encode(0x01, b"\x10\x20"))
    frame[-1] ^= 0x01
    with pytest.raises(FrameError, match="checksum"):
        decode(bytes(frame))


def test_decode_rejects_length_mismatch():
    frame = encode(0x01, b"\x10\x20")
    with pytest.raises(FrameError, match="length"):
        decode(frame[:-1])
    with pytest.raises(FrameError, match="length"):
        decode(frame + b"\x00")


def test_decode_rejects_bad_sync():
    frame = bytearray(encode(0x01, b"\x10"))
    frame[0] = 0x5A
    with pytest.raises(FrameError, match="sync"):
        decode(bytes(frame))


def test_checksum_wraps_mod_256():
    assert checksum(0xFF, b"\xFF\xFF") == (0xFF + 2 + 0xFF + 0xFF) & 0xFF


def test_parser_handles_byte_by_byte_feed():
    f1 = encode(0x05, b"\x01\x02\x03")
    f2 = encode(0x06)
    p = FrameParser()
    got = []
    for b in f1 + f2:
        got += p.feed(bytes([b]))
    assert got == [(0x05, b"\x01\x02\x03"), (0x06, b"")]


def test_parser_skips_junk_before_sync():
    p = FrameParser()
    assert p.feed(b"\x00\x11junk" + encode(0x06)) == [(0x06, b"")]


def test_parser_sync_byte_inside_data_is_not_a_frame_start():
    data = b"\xA5\xA5\x00"
    p = FrameParser()
    assert p.feed(encode(0x02, data)) == [(0x02, data)]


def test_parser_resyncs_after_corrupt_frame():
    bad = bytearray(encode(0x01, b"\x10\x20"))
    bad[-1] ^= 0xFF
    good = encode(0x06, b"\x07")
    p = FrameParser()
    assert p.feed(bytes(bad) + good) == [(0x06, b"\x07")]


def test_parser_waits_for_partial_frame():
    frame = encode(0x04, b"\x01\x02\x03\x04")
    p = FrameParser()
    assert p.feed(frame[:4]) == []
    assert p.feed(frame[4:]) == [(0x04, b"\x01\x02\x03\x04")]


def test_q88_round_trip_and_endianness():
    values = [0, 1, -1, 256, -256, 32767, -32768]
    packed = pack_q88(values)
    assert packed[:4] == bytes([0x00, 0x00, 0x01, 0x00])  # 0 then 1, little-endian
    assert unpack_q88(packed) == values


def test_q88_rejects_out_of_range():
    with pytest.raises(ValueError):
        pack_q88([32768])
    with pytest.raises(ValueError):
        pack_q88([-32769])


def test_q88_unpack_rejects_odd_length():
    with pytest.raises(ValueError):
        unpack_q88(b"\x00")


def test_pack_params_layout():
    payload = pack_params(theta=0x0100, v_reset=-256, v_rest=0, k_m=4, k_s=3, refrac=5)
    assert len(payload) == PARAM_LEN
    assert payload == bytes([0x00, 0x01, 0x00, 0xFF, 0x00, 0x00, 4, 3, 5])


def test_pack_params_rejects_out_of_range():
    with pytest.raises(ValueError):
        pack_params(0, 0, 0, k_m=16, k_s=0, refrac=0)
    with pytest.raises(ValueError):
        pack_params(0, 0, 0, k_m=0, k_s=0, refrac=8)


def test_pack_run_layout():
    assert pack_run(0x0100, 1000) == bytes([0x00, 0x01, 0xE8, 0x03])
    assert pack_run(-256, 1024) == bytes([0x00, 0xFF, 0x00, 0x04])


def test_pack_run_rejects_bad_steps():
    for steps in (0, 1025):
        with pytest.raises(ValueError):
            pack_run(0, steps)


def test_pack_read_record_layout():
    assert pack_read_record(300, 64) == bytes([0x2C, 0x01, 64])


def test_pack_read_record_rejects_bad_values():
    with pytest.raises(ValueError):
        pack_read_record(1024, 1)
    with pytest.raises(ValueError):
        pack_read_record(0, 0)
    with pytest.raises(ValueError):
        pack_read_record(0, 65)


def test_unpack_records_round_trip():
    data = bytes([0x00, 0x01, 0, 0xFF, 0xFF, 1])  # V=256 spike 0; V=-1 spike 1
    assert unpack_records(data) == [(256, 0), (-1, 1)]


def test_unpack_records_rejects_bad_input():
    with pytest.raises(ValueError):
        unpack_records(b"\x00\x01")
    with pytest.raises(ValueError):
        unpack_records(bytes([0, 0, 2]))


def test_int8_round_trip():
    values = [-128, -1, 0, 1, 127]
    assert pack_int8(values) == bytes([0x80, 0xFF, 0x00, 0x01, 0x7F])
    assert unpack_int8(pack_int8(values)) == values


def test_int8_rejects_out_of_range():
    with pytest.raises(ValueError):
        pack_int8([128])


def test_pack_write_weights_layout():
    assert pack_write_weights(0x0102, [-1, 5]) == bytes([0x02, 0x01, 0xFF, 0x05])


def test_pack_write_weights_limits():
    pack_write_weights(0, [0] * 253)          # largest block that fits a frame
    with pytest.raises(ValueError):
        pack_write_weights(0, [0] * 254)
    with pytest.raises(ValueError):
        pack_write_weights(0, [])
    with pytest.raises(ValueError):
        pack_write_weights(0x10000, [0])


def test_pack_set_input_layout_and_limits():
    assert pack_set_input(3, [0x0100, -256]) == bytes([0x03, 0x00, 0x00, 0x01, 0x00, 0xFF])
    pack_set_input(0, [0] * 126)              # largest block that fits a frame
    with pytest.raises(ValueError):
        pack_set_input(0, [0] * 127)


def test_pack_read_block_layout_and_limits():
    assert pack_read_block(256, 64) == bytes([0x00, 0x01, 64])
    with pytest.raises(ValueError):
        pack_read_block(0, 65)
    with pytest.raises(ValueError):
        pack_read_block(0, 0)


def test_pack_read_trace_layout_and_limits():
    assert pack_read_trace(509, 3) == bytes([0xFD, 0x01, 3])
    assert pack_read_trace(0, 7)[-1] == 7
    with pytest.raises(ValueError):
        pack_read_trace(0, 8)
    with pytest.raises(ValueError):
        pack_read_trace(0, 0)
    with pytest.raises(ValueError):
        pack_read_trace(0x10000, 1)


def test_pack_read_trace_stays_inside_kept_steps():
    pack_read_trace(TRACE_STEPS - 7, 7)       # ends exactly at the last kept step
    with pytest.raises(ValueError):
        pack_read_trace(TRACE_STEPS - 6, 7)   # one step past the kept steps
    with pytest.raises(ValueError):
        pack_read_trace(TRACE_STEPS, 1)


def test_unpack_trace_rejects_zero_neurons():
    with pytest.raises(ValueError):
        unpack_trace(b"", 0)                  # would divide by zero without the check


def test_unpack_trace_bit_order():
    # N = 16: byte 0 holds neurons 0..7 (bit j = neuron j), byte 1 holds neurons 8..15
    steps = unpack_trace(bytes([0b0000_0101, 0b1000_0000, 0x00, 0x03]), 16)
    assert steps[0][:8] == [1, 0, 1, 0, 0, 0, 0, 0]
    assert steps[0][8:] == [0, 0, 0, 0, 0, 0, 0, 1]
    assert steps[1][:8] == [0, 0, 0, 0, 0, 0, 0, 0]
    assert steps[1][8:] == [1, 1, 0, 0, 0, 0, 0, 0]
    with pytest.raises(ValueError):
        unpack_trace(b"\x00\x00\x00", 16)     # not a whole number of steps
    with pytest.raises(ValueError):
        unpack_trace(b"\x00\x00", 12)         # N is not a multiple of 8


def test_unpack_counts_and_status():
    assert unpack_counts(bytes([0x34, 0x12, 0x01, 0x00])) == [0x1234, 1]
    with pytest.raises(ValueError):
        unpack_counts(b"\x00")
    assert unpack_status(bytes([3, 0, 0x00, 0x04])) == (3, 0, 1024)
    with pytest.raises(ValueError):
        unpack_status(b"\x00\x00")
