# v0.1.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

from dataclasses import dataclass


@gl.contract_interface
class IInterlock:
    class View:
        def is_grant_active(
            self,
            intent_id: u256,
            expected_resource_hash: str,
            expected_action_hash: str,
            actor: Address,
        ) -> bool: ...

    class Write:
        pass


@allow_storage
@dataclass
class ExecutionReceipt:
    actor: Address
    intent_id: u256
    action_hash: str
    resource_hash: str
    payload_hash: str


class ProtectedResource(gl.Contract):
    """Minimal consumer example for Interlock's pinned-grant interface.

    The consumer deliberately does not trust a free-form Interlock verdict. It
    pins the exact resource-definition hash, action hash, actor, and one-time
    execution key before recording the protected state transition. Local tests
    exercise this boundary with a controlled interface stub; StudioNet's
    current UI does not support live contract-to-contract interactions.
    """

    interlock_address: Address
    executions: TreeMap[str, ExecutionReceipt]
    execution_count: u256
    last_payload_hash: str

    def __init__(self, interlock_address: Address):
        # Studio's stable transaction form encodes Address constructor values
        # as an unsigned 160-bit integer. Normalize that ABI representation
        # back to the SDK Address wrapper before storing it; the typed
        # IC-to-IC interface requires an Address value at runtime.
        if isinstance(interlock_address, int) and not isinstance(interlock_address, bool):
            if interlock_address < 0 or interlock_address >= 1 << 160:
                raise gl.vm.UserError("EXPECTED: invalid Interlock address")
            interlock_address = Address(f"0x{interlock_address:040x}")
        if not isinstance(interlock_address, Address):
            raise gl.vm.UserError("EXPECTED: Interlock address must be an Address")
        self.interlock_address = interlock_address
        self.execution_count = u256(0)
        self.last_payload_hash = ""

    @gl.public.write
    def execute(
        self,
        intent_id: u256,
        expected_resource_hash: str,
        action_hash: str,
        payload_hash: str,
    ) -> None:
        expected_resource_hash = str(expected_resource_hash).strip().lower()
        action_hash = str(action_hash).strip().lower()
        payload_hash = str(payload_hash).strip().lower()
        for field, value in (
            ("expected_resource_hash", expected_resource_hash),
            ("action_hash", action_hash),
            ("payload_hash", payload_hash),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise gl.vm.UserError(f"EXPECTED: {field} must be a 32-byte lowercase hex digest")

        if action_hash in self.executions:
            raise gl.vm.UserError("EXPECTED: protected action was already executed")

        interlock = IInterlock(self.interlock_address)
        actor = gl.message.sender_address
        if not interlock.view().is_grant_active(
            intent_id,
            expected_resource_hash,
            action_hash,
            actor,
        ):
            raise gl.vm.UserError("EXPECTED: no active Interlock grant for this actor/action/resource")

        self.executions[action_hash] = ExecutionReceipt(
            actor=actor,
            intent_id=intent_id,
            action_hash=action_hash,
            resource_hash=expected_resource_hash,
            payload_hash=payload_hash,
        )
        self.execution_count = u256(int(self.execution_count) + 1)
        self.last_payload_hash = payload_hash

    @gl.public.view
    def was_executed(self, action_hash: str) -> bool:
        return str(action_hash).strip().lower() in self.executions

    @gl.public.view
    def get_execution(self, action_hash: str) -> dict:
        key = str(action_hash).strip().lower()
        if key not in self.executions:
            raise gl.vm.UserError("EXPECTED: unknown execution")
        item = self.executions[key]
        return {
            "actor": str(item.actor),
            "intent_id": int(item.intent_id),
            "action_hash": str(item.action_hash),
            "resource_hash": str(item.resource_hash),
            "payload_hash": str(item.payload_hash),
        }
