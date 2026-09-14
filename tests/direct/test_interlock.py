"""Direct-mode tests for the Interlock reusable Intelligent Contract.

These tests focus on the primitive's invariants rather than happy-path volume:
resource definitions are version-pinned, duplicate side effects are rejected,
ambiguous semantic conflicts fail closed, validators independently re-derive
relations, FIFO fairness is preserved, and abandoned locks expire permissionlessly.
"""

import json
import sys
from pathlib import Path

CONTRACT = "contracts/interlock.py"
CLASSIFIER = r"INTERLOCK / SEMANTIC CONCURRENCY CLASSIFICATION"
BASE = "2026-09-13T20:00:00+00:00"
LATER = "2026-09-13T20:02:00+00:00"
EXPIRED = "2026-09-13T22:00:00+00:00"

RESOURCE_NAME = "Order 812 coordination surface"
RESOURCE_URI = "urn:orders:812"
RESOURCE_SEMANTICS = (
    "This resource represents the lifecycle of order 812. Dispatch, cancellation, "
    "refund, address mutation, and fulfilment may invalidate one another. Read-only "
    "status inspection does not mutate lifecycle state."
)



def alice_address():
    from gltest.direct import create_address
    return create_address("alice")


def bob_address():
    from gltest.direct import create_address
    return create_address("bob")


def charlie_address():
    from gltest.direct import create_address
    return create_address("charlie")


def h(char):
    return char * 64


def relation(name="COMMUTES", mask=0, reason="operations are independent"):
    return json.dumps({"relation": name, "conflict_mask": mask, "reason": reason})


def create_resource(vm, deploy):
    vm.warp(BASE)
    contract = deploy(CONTRACT)
    vm.sender = alice_address()
    resource_id = contract.create_resource(RESOURCE_NAME, RESOURCE_URI, RESOURCE_SEMANTICS)
    return contract, resource_id


def submit(contract, resource_id, operation, mode, description, action_hash, ttl=600, lease=300, actor=None):
    return contract.submit_intent(
        resource_id,
        actor or alice_address(),
        operation,
        mode,
        description,
        action_hash,
        ttl,
        lease,
    )


def test_create_resource_pins_definition_hash(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    resource = contract.get_resource(resource_id)
    assert resource["status_name"] == "ACTIVE"
    assert resource["generation"] == 1
    assert len(resource["definition_hash"]) == 64
    assert resource["open_count"] == 0


def test_resource_update_requires_no_open_intents(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    submit(
        contract, resource_id, "cancel", 2,
        "Cancel order 812 before the warehouse dispatches the package.", h("1")
    )
    with direct_vm.expect_revert("while intents are open"):
        contract.update_resource(resource_id, RESOURCE_URI, RESOURCE_SEMANTICS + " Updated.")


def test_resource_update_changes_generation_and_hash(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    before = contract.get_resource(resource_id)
    contract.update_resource(resource_id, RESOURCE_URI, RESOURCE_SEMANTICS + " Updated semantics.")
    after = contract.get_resource(resource_id)
    assert after["generation"] == 2
    assert after["definition_hash"] != before["definition_hash"]


def test_paused_resource_rejects_new_intents(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    contract.set_resource_paused(resource_id, True)
    with direct_vm.expect_revert("paused"):
        submit(
            contract, resource_id, "cancel", 2,
            "Cancel order 812 before the warehouse dispatches the package.", h("2")
        )




def test_only_resource_owner_may_admit_intents(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    with direct_vm.prank(bob_address()):
        with direct_vm.expect_revert("only resource owner may admit intents"):
            contract.submit_intent(
                resource_id,
                bob_address(),
                "dispatch",
                2,
                "Dispatch order 812 from the warehouse and mark it as fulfilled.",
                h("d"),
                600,
                300,
            )


def test_owner_can_admit_distinct_actor_and_grant_binds_actor(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    action = h("e")
    intent = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.",
        action, actor=bob_address(),
    )
    assert contract.resolve_intent(intent) is True
    resource_hash = contract.get_resource(resource_id)["definition_hash"]
    assert contract.is_grant_active(intent, resource_hash, action, bob_address()) is True
    assert contract.is_grant_active(intent, resource_hash, action, alice_address()) is False
    with direct_vm.prank(bob_address()):
        contract.complete_intent(intent)
    assert contract.get_intent(intent)["status_name"] == "COMPLETED"

def test_duplicate_action_hash_is_rejected(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    action = h("3")
    submit(
        contract, resource_id, "cancel", 2,
        "Cancel order 812 before the warehouse dispatches the package.", action
    )
    with direct_vm.expect_revert("already registered"):
        submit(
            contract, resource_id, "retry cancel", 2,
            "Retry cancellation of the same economic side effect for order 812.", action
        )


def test_first_intent_grants_without_llm(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    intent = submit(
        contract, resource_id, "cancel", 2,
        "Cancel order 812 before the warehouse dispatches the package.", h("4")
    )
    assert contract.resolve_intent(intent) is True
    data = contract.get_intent(intent)
    assert data["status_name"] == "GRANTED"
    assert data["grant_expires_at"] > data["granted_at"]


def test_read_read_commutes_deterministically(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    first = submit(
        contract, resource_id, "inspect status", 1,
        "Read the current order status without modifying any order state.", h("5")
    )
    second = submit(
        contract, resource_id, "inspect shipping", 1,
        "Read the current shipping metadata without modifying any order state.", h("6")
    )
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is True
    decision = contract.get_pair_decision(first, second)
    assert decision["relation_name"] == "COMMUTES"
    assert decision["conflict_mask"] == 0


def test_exclusive_intent_blocks_later_operation_without_llm(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    first = submit(
        contract, resource_id, "close order", 3,
        "Take exclusive ownership of the lifecycle while permanently closing order 812.", h("7")
    )
    second = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.", h("8")
    )
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is False
    assert contract.get_intent(second)["last_blocker_id"] == first
    assert contract.get_pair_decision(first, second)["relation_name"] == "CONFLICTS"


def test_semantic_commute_allows_parallel_write_grants(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    direct_vm.mock_llm(CLASSIFIER, relation("COMMUTES", 0, "fields are independent"))
    first = submit(
        contract, resource_id, "set note", 2,
        "Update the internal warehouse note only; do not alter fulfilment or payment state.", h("9")
    )
    second = submit(
        contract, resource_id, "set label", 2,
        "Update the printable package label metadata only; do not alter warehouse notes.", h("a")
    )
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is True
    assert contract.get_pair_decision(first, second)["relation_name"] == "COMMUTES"
    assert direct_vm.run_validator() is True


def test_semantic_conflict_blocks_parallel_grant(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    direct_vm.mock_llm(
        CLASSIFIER,
        relation("CONFLICTS", 11, "dispatch and cancellation alter the same lifecycle and order matters"),
    )
    first = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.", h("b")
    )
    second = submit(
        contract, resource_id, "cancel", 2,
        "Cancel order 812 and prevent warehouse fulfilment from proceeding.", h("c")
    )
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is False
    decision = contract.get_pair_decision(first, second)
    assert decision["relation_name"] == "CONFLICTS"
    assert "WRITE_OVERLAP" in decision["conflict_names"]
    assert "ORDER_SENSITIVITY" in decision["conflict_names"]
    assert decision["reason"] == "CONFLICTS:WRITE_OVERLAP,PRECONDITION_INVALIDATION,ORDER_SENSITIVITY"


def test_malformed_model_output_fails_closed(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    direct_vm.mock_llm(CLASSIFIER, "not valid json")
    first = submit(
        contract, resource_id, "update field one", 2,
        "Update one state field under the shared order lifecycle resource.", h("a")
    )
    second = submit(
        contract, resource_id, "update field two", 2,
        "Update another field whose interaction is not mechanically established.", h("b")
    )
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is False
    decision = contract.get_pair_decision(first, second)
    assert decision["relation_name"] == "AMBIGUOUS"
    assert decision["conflict_names"] == ["UNKNOWN_SEMANTIC"]
    assert decision["reason"] == "AMBIGUOUS:UNKNOWN_SEMANTIC"


def test_well_formed_but_inconsistent_model_output_fails_closed(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    direct_vm.mock_llm(
        CLASSIFIER,
        '{"relation":"COMMUTES","conflict_mask":64,"reason":"contradictory result"}',
    )
    first = submit(contract, resource_id, "write one", 2,
                   "Update one field under the shared order lifecycle resource.", h("a"))
    second = submit(contract, resource_id, "write two", 2,
                    "Update another field under the shared order lifecycle resource.", h("b"))
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is False
    decision = contract.get_pair_decision(first, second)
    assert decision["relation_name"] == "AMBIGUOUS"
    assert decision["conflict_mask"] == 64


def test_ambiguous_relation_fails_closed(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    direct_vm.mock_llm(
        CLASSIFIER,
        relation("AMBIGUOUS", 64, "resource definition does not establish whether the effects overlap"),
    )
    first = submit(
        contract, resource_id, "agent action one", 2,
        "Perform a write whose exact interaction with other writes is not fully specified.", h("d")
    )
    second = submit(
        contract, resource_id, "agent action two", 2,
        "Perform another write whose cross-effect cannot be established from current semantics.", h("e")
    )
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is False
    assert contract.get_pair_decision(first, second)["relation_name"] == "AMBIGUOUS"


def test_validator_rederives_relation_not_just_json_shape(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    direct_vm.mock_llm(CLASSIFIER, relation("COMMUTES", 0, "leader sees independence"))
    first = submit(
        contract, resource_id, "set note", 2,
        "Update the warehouse note field while preserving every lifecycle field.", h("f")
    )
    second = submit(
        contract, resource_id, "set label", 2,
        "Update printable label metadata while preserving every warehouse-note field.", h("0")
    )
    contract.resolve_intent(first)
    contract.resolve_intent(second)
    assert direct_vm.run_validator() is True

    # A format-only validator would still accept the leader's valid JSON.
    # Interlock must reject when the validator independently reaches CONFLICTS.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(CLASSIFIER, relation("CONFLICTS", 1, "validator detects write overlap"))
    assert direct_vm.run_validator() is False


def test_cancel_releases_open_slot(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    intent = submit(
        contract, resource_id, "cancel", 2,
        "Cancel order 812 before the warehouse dispatches the package.", h("1")
    )
    assert contract.get_resource(resource_id)["open_count"] == 1
    contract.cancel_intent(intent)
    assert contract.get_intent(intent)["status_name"] == "CANCELLED"
    assert contract.get_resource(resource_id)["open_count"] == 0


def test_only_actor_or_owner_may_cancel(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    intent = submit(
        contract, resource_id, "cancel", 2,
        "Cancel order 812 before the warehouse dispatches the package.", h("2"),
        actor=bob_address(),
    )
    with direct_vm.prank(charlie_address()):
        with direct_vm.expect_revert("only actor or resource owner"):
            contract.cancel_intent(intent)
    with direct_vm.prank(bob_address()):
        contract.cancel_intent(intent)
    assert contract.get_intent(intent)["status_name"] == "CANCELLED"


def test_pause_makes_existing_grant_non_consumable_until_unpaused(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    action = h("f")
    intent = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.", action
    )
    assert contract.resolve_intent(intent) is True
    resource_hash = contract.get_resource(resource_id)["definition_hash"]
    assert contract.is_grant_active(intent, resource_hash, action, alice_address()) is True
    contract.set_resource_paused(resource_id, True)
    assert contract.is_grant_active(intent, resource_hash, action, alice_address()) is False
    contract.set_resource_paused(resource_id, False)
    assert contract.is_grant_active(intent, resource_hash, action, alice_address()) is True


def test_grant_expiration_is_permissionless_and_releases_active_count(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    intent = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.", h("3"), ttl=60, lease=60
    )
    assert contract.resolve_intent(intent) is True
    assert contract.get_resource(resource_id)["active_count"] == 1
    direct_vm.warp(EXPIRED)
    assert contract.expire_intent(intent) is True
    assert contract.get_intent(intent)["status_name"] == "EXPIRED"
    assert contract.get_resource(resource_id)["active_count"] == 0


def test_expired_blocker_cannot_hold_queue(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    first = submit(
        contract, resource_id, "close", 3,
        "Hold the order lifecycle exclusively while permanently closing order 812.", h("4"), ttl=60, lease=60
    )
    second = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.", h("5"), ttl=7200, lease=300
    )
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is False
    direct_vm.warp(LATER)
    assert contract.resolve_intent(second) is True
    assert contract.get_intent(first)["status_name"] == "EXPIRED"


def test_completed_intent_no_longer_blocks_queue(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    first = submit(
        contract, resource_id, "close", 3,
        "Hold the order lifecycle exclusively while permanently closing order 812.", h("6")
    )
    second = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.", h("7")
    )
    assert contract.resolve_intent(first) is True
    assert contract.resolve_intent(second) is False
    contract.complete_intent(first)
    assert contract.resolve_intent(second) is True


def test_conflicting_later_intent_cannot_jump_older_waiter(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    direct_vm.mock_llm(CLASSIFIER, relation("CONFLICTS", 1, "same lifecycle field"))
    exclusive = submit(contract, resource_id, "close", 3,
                       "Hold the lifecycle exclusively while order 812 is closed.", h("c"))
    older = submit(contract, resource_id, "dispatch", 2,
                   "Dispatch order 812 from the warehouse and mark it fulfilled.", h("d"))
    later = submit(contract, resource_id, "cancel", 2,
                   "Cancel order 812 and prevent warehouse fulfilment from proceeding.", h("e"))
    assert contract.resolve_intent(exclusive) is True
    assert contract.resolve_intent(older) is False
    contract.complete_intent(exclusive)
    assert contract.resolve_intent(later) is False
    assert contract.get_intent(later)["last_blocker_id"] == older
    assert contract.resolve_intent(older) is True
    contract.complete_intent(older)
    assert contract.resolve_intent(later) is True


def test_queue_open_intent_limit_is_enforced(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    for index in range(24):
        submit(contract, resource_id, f"read {index}", 1,
               "Read order metadata without modifying resource state.", f"{index + 1:064x}")
    with direct_vm.expect_revert("resource queue is full"):
        submit(contract, resource_id, "one too many", 1,
               "Read order metadata without modifying resource state.", f"{25:064x}")


def test_protected_resource_rejects_accepts_and_prevents_replay(
    direct_vm, direct_deploy, monkeypatch
):
    action = h("9")
    intent = 41
    resource_hash = h("8")
    # Direct Mode has no cross-contract runtime. Replace only the typed view
    # boundary with a controllable response and assert exact pinning arguments.
    from gltest.direct.sdk_loader import setup_sdk_paths
    import gltest.direct.loader as direct_loader
    setup_sdk_paths(Path("contracts/protected_resource.py").resolve())
    from genlayer.py.types import Address
    monkeypatch.setattr(direct_loader, "_calldata_roundtrip_args", lambda args, kwargs: (args, kwargs))
    interlock_address = Address(str(alice_address()))
    protected = direct_deploy(
        "contracts/protected_resource.py", int(str(interlock_address), 16)
    )
    assert protected._instance.interlock_address == interlock_address
    direct_vm.sender = alice_address()
    grant = {"active": False}
    calls = []

    class FakeInterlock:
        def __init__(self, _address):
            pass

        def view(self):
            return self

        def is_grant_active(self, iid, rh, ah, actor):
            calls.append((iid, rh, ah, str(actor)))
            return grant["active"]

    monkeypatch.setitem(protected._instance.execute.__globals__, "IInterlock", FakeInterlock)

    with direct_vm.expect_revert("no active Interlock grant"):
        protected.execute(intent, resource_hash, action, h("a"))

    assert calls[-1] == (intent, resource_hash, action, str(direct_vm.sender))
    grant["active"] = True
    protected.execute(intent, resource_hash, action, h("a"))
    assert protected.was_executed(action) is True
    assert protected.get_execution(action)["intent_id"] == intent
    with direct_vm.expect_revert("already executed"):
        protected.execute(intent, resource_hash, action, h("a"))


def test_active_grant_is_pinned_to_actor_action_and_resource_hash(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    action = h("8")
    intent = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.", action
    )
    contract.resolve_intent(intent)
    resource_hash = contract.get_resource(resource_id)["definition_hash"]
    assert contract.is_grant_active(intent, resource_hash, action, alice_address()) is True
    assert contract.is_grant_active(intent, resource_hash, action, bob_address()) is False
    assert contract.is_grant_active(intent, resource_hash, h("9"), alice_address()) is False
    assert contract.is_grant_active(intent, h("a"), action, alice_address()) is False


def test_pair_decision_is_cached(direct_vm, direct_deploy):
    contract, resource_id = create_resource(direct_vm, direct_deploy)
    direct_vm.mock_llm(CLASSIFIER, relation("CONFLICTS", 1, "same lifecycle field"))
    first = submit(
        contract, resource_id, "dispatch", 2,
        "Dispatch order 812 from the warehouse and mark it as fulfilled.", h("b")
    )
    second = submit(
        contract, resource_id, "cancel", 2,
        "Cancel order 812 and prevent warehouse fulfilment from proceeding.", h("c")
    )
    contract.resolve_intent(first)
    contract.resolve_intent(second)
    before = contract.get_pair_decision(first, second)
    # Re-resolution must reuse the immutable pair decision rather than ask a
    # newly configured model to rewrite history.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(CLASSIFIER, relation("COMMUTES", 0, "changed model opinion"))
    assert contract.resolve_intent(second) is False
    after = contract.get_pair_decision(first, second)
    assert after["decision_hash"] == before["decision_hash"]
    assert after["relation_name"] == "CONFLICTS"
