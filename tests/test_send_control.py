"""Tests for the send_control module — control character mapping."""

from iterm2_agent.tools.send_control import CONTROL_MAP


class TestControlMap:
    def test_ctrl_c(self):
        assert CONTROL_MAP["C"] == "\x03"

    def test_ctrl_z(self):
        assert CONTROL_MAP["Z"] == "\x1a"

    def test_ctrl_d(self):
        assert CONTROL_MAP["D"] == "\x04"

    def test_ctrl_l(self):
        assert CONTROL_MAP["L"] == "\x0c"

    def test_escape(self):
        assert CONTROL_MAP["ESCAPE"] == "\x1b"

    def test_ctrl_a(self):
        assert CONTROL_MAP["A"] == "\x01"

    def test_ctrl_e(self):
        assert CONTROL_MAP["E"] == "\x05"

    def test_ctrl_u(self):
        assert CONTROL_MAP["U"] == "\x15"

    def test_all_values_are_single_chars(self):
        for key, value in CONTROL_MAP.items():
            assert len(value) == 1, f"CONTROL_MAP[{key!r}] should be a single char"

    def test_all_values_are_control_chars(self):
        for key, value in CONTROL_MAP.items():
            assert ord(value) < 32 or value == "\x1b", (
                f"CONTROL_MAP[{key!r}] = {ord(value)} is not a control character"
            )
