"""Shared direct-mode test configuration for Interlock."""

import pytest
import os
import sys


@pytest.fixture(autouse=True)
def _reset_contract_registry(monkeypatch):
    # genlayer-test 0.29.2 swaps a temporary message file onto stdin and then
    # unlinks it immediately. POSIX allows unlinking an open file, but Windows
    # does not. Defer only that Windows cleanup until after the VM fixture has
    # restored stdin; this changes no Direct Mode execution behaviour.
    deferred_temp_files = []
    original_unlink = os.unlink
    from gltest.direct.vm import VMContext
    original_warp = VMContext.warp

    def warp_and_refresh_message(vm, timestamp):
        original_warp(vm, timestamp)
        gl = sys.modules.get("genlayer.gl")
        if gl is not None and isinstance(getattr(gl, "message_raw", None), dict):
            gl.message_raw["datetime"] = timestamp

    monkeypatch.setattr(VMContext, "warp", warp_and_refresh_message)
    if os.name == "nt":
        def windows_safe_unlink(path, *args, **kwargs):
            try:
                return original_unlink(path, *args, **kwargs)
            except PermissionError:
                deferred_temp_files.append(path)

        os.unlink = windows_safe_unlink
    yield
    if os.name == "nt":
        os.unlink = original_unlink
        for path in deferred_temp_files:
            try:
                original_unlink(path)
            except FileNotFoundError:
                pass
            except PermissionError:
                # The test-suite may still hold the descriptor until process
                # shutdown; Windows will remove this temporary file then.
                pass
    try:
        import genlayer.gl.genvm_contracts as contracts
    except ImportError:
        return
    contracts.__known_contract__ = None
