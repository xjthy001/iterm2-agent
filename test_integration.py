"""Integration test — call each MCP tool against a live iTerm2 instance."""

import asyncio
import sys

import iterm2

from iterm2_agent.connection import ITerm2Context, get_screen_lines
from iterm2_agent.security import SecurityGuard, SecurityLevel
from iterm2_agent.tools.send_control import CONTROL_MAP


passed = 0
failed = 0


def report(name: str, ok: bool, detail: str = ""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  -- {detail}")


async def run_tests():
    print("Connecting to iTerm2...")
    connection = await iterm2.Connection.async_create()
    app = await iterm2.async_get_app(connection)
    ctx = ITerm2Context(connection=connection, app=app)
    print(f"Connected. App has {len(app.terminal_windows)} window(s).\n")

    # --- Test 1: resolve_session (active) ---
    print("[1] resolve_session (active)")
    try:
        session = await ctx.resolve_session("")
        report("get active session", True)
        print(f"       session_id = {session.session_id}")
    except Exception as e:
        report("get active session", False, str(e))
        print("Cannot continue without a session.")
        return

    # --- Test 2: read_screen ---
    print("\n[2] read_screen")
    try:
        lines, cx, cy = await get_screen_lines(session)
        report("get_screen_lines returns data", len(lines) > 0, f"got {len(lines)} lines")
        report("cursor position valid", cx >= 0 and cy >= 0, f"cursor=({cx},{cy})")
        # Show last non-empty line
        non_empty = [l for l in lines if l.strip()]
        if non_empty:
            print(f"       last line: {non_empty[-1][:80]}")
    except Exception as e:
        report("read_screen", False, str(e))

    # --- Test 3: send_text (no enter) ---
    print("\n[3] send_text (no enter)")
    try:
        await session.async_send_text("echo integration_test_ok")
        await asyncio.sleep(0.5)
        lines, _, _ = await get_screen_lines(session)
        last = lines[-1] if lines else ""
        report("text appears on screen", "echo integration_test_ok" in last or "integration_test_ok" in "\n".join(lines[-3:]),
               f"last line: {last[:80]}")
    except Exception as e:
        report("send_text", False, str(e))

    # --- Test 4: send_control (Ctrl+U to clear line, then Ctrl+C) ---
    print("\n[4] send_control (Ctrl+U clear line)")
    try:
        await session.async_send_text(CONTROL_MAP["U"])
        await asyncio.sleep(0.3)
        await session.async_send_text(CONTROL_MAP["C"])
        await asyncio.sleep(0.5)
        lines, _, _ = await get_screen_lines(session)
        report("ctrl+U/C sent without error", True)
    except Exception as e:
        report("send_control", False, str(e))

    # --- Test 5: run_command pattern (send + wait + read) ---
    print("\n[5] run_command pattern (echo hello_world)")
    try:
        # Record baseline
        pre = await session.async_get_screen_contents()
        baseline = pre.number_of_lines_above_screen + pre.number_of_lines

        # Send command
        await session.async_send_text("echo hello_world\r")

        # Wait for output via ScreenStreamer
        idle = 0
        async with session.get_screen_streamer() as streamer:
            for _ in range(10):
                try:
                    await asyncio.wait_for(streamer.async_get(), timeout=1.0)
                    idle = 0
                except asyncio.TimeoutError:
                    idle += 1
                    if idle >= 2:
                        break

        # Read result
        lines, _, _ = await get_screen_lines(session)
        output = "\n".join(lines)
        report("hello_world in output", "hello_world" in output, f"output tail: {lines[-3:]}")
    except Exception as e:
        report("run_command pattern", False, str(e))

    # --- Test 6: watch_output pattern (regex match) ---
    print("\n[6] watch_output pattern (send + match regex)")
    try:
        import re
        pattern = re.compile(r"watch_test_\d+")

        await session.async_send_text("echo watch_test_42\r")

        matched = False
        async with session.get_screen_streamer() as streamer:
            for _ in range(10):
                lines, _, _ = await get_screen_lines(session)
                hits = [l for l in lines if pattern.search(l)]
                if hits:
                    matched = True
                    break
                try:
                    await asyncio.wait_for(streamer.async_get(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass

        report("regex pattern matched", matched)
    except Exception as e:
        report("watch_output pattern", False, str(e))

    # --- Test 7: manage_session (list) ---
    print("\n[7] manage_session (list)")
    try:
        session_count = 0
        for window in app.terminal_windows:
            for tab in window.tabs:
                for s in tab.sessions:
                    session_count += 1

        report("found sessions", session_count > 0, f"count={session_count}")
    except Exception as e:
        report("manage_session list", False, str(e))

    # --- Test 8: security module ---
    print("\n[8] security classification")
    report("ls is SAFE", SecurityGuard.check("ls -la") == SecurityLevel.SAFE)
    report("rm is DANGEROUS", SecurityGuard.check("rm -rf /") == SecurityLevel.DANGEROUS)
    report("npm is CAUTION", SecurityGuard.check("npm install") == SecurityLevel.CAUTION)

    # --- Summary ---
    total = passed + failed
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("All tests passed!")
    else:
        print("Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_tests())
