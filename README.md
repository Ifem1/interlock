# Interlock

**Semantic concurrency control for autonomous agents on GenLayer.**

Interlock is a standalone reusable Intelligent Contract primitive. It answers one narrow but foundational question:

> When two already-authorized operations target the same shared resource, may they safely be in flight at the same time?

Traditional locks require developers to know the conflict matrix in advance. Autonomous agents often express operations in natural language or structured descriptions whose interaction is semantic: `cancel order` and `dispatch order` may touch different fields yet still conflict; `update internal note` and `update printable label` may safely commute.

Interlock combines deterministic lock mechanics with GenLayer consensus for only the part ordinary smart contracts cannot reliably decide: semantic commutativity.

**This repository intentionally has no frontend.** It is an Intelligent Contract primitive, not a product UI.

## Target network

- **StudioNet**
- **Chain ID: `61999`**
- Studio API used by the included config: `https://studio.genlayer.com/api`

The repository is deliberately configured only for the requested stable StudioNet target.

## Why Interlock is not another "AI decides X" contract

The model does not schedule operations, create permissions, mutate payloads, invent compromises, or choose execution order.

Interlock separates the problem into two layers:

1. **Deterministic protocol mechanics**
   - resource ownership and versioning
   - exact action-hash uniqueness
   - FIFO fairness
   - queue bounds
   - read/read fast-path
   - exclusive-operation fast-path
   - grant leases, emergency resource pause, and permissionless expiry
   - immutable pair-decision caching
   - actor/action/resource binding
   - terminal lifecycle accounting

2. **Consensus-only semantic question**
   - `COMMUTES`
   - `CONFLICTS`
   - `AMBIGUOUS`

Validators independently re-derive the bounded relation and conflict-mask. `AMBIGUOUS` fails closed and serializes. This is a bounded semantic judgment over frozen definitions and admitted descriptions; it is not evidence that an off-chain payload is true or that a consumer performed an external side effect.

## Core lifecycle

```text
resource owner / owner-controlled gateway
    │
    ├── create_resource(...)
    │
    └── admit actor-bound intents
            │
            ▼
       Resource v1
            │
     ┌──────┴──────┐
     ▼             ▼
 Intent A       Intent B
 PENDING        PENDING
     │             │
     └──── pair classification ────┐
                                   ▼
                       COMMUTES / CONFLICTS /
                            AMBIGUOUS
                                   │
                    deterministic scheduler
                     ┌─────────────┴────────────┐
                     ▼                          ▼
                 GRANTED                    BLOCKED
                     │                          │
          complete / lease expiry      blocker completes/expires
                     │                          │
                     ▼                          └── resolve again
                  TERMINAL
```

## Admission boundary

Interlock deliberately does **not** let arbitrary callers enqueue locks. Only the resource owner (or a gateway contract that owns the resource) may call `submit_intent`. This prevents a third party from griefing a public resource with conflicting long-lived intents.

Admission is not the same as semantic scheduling: the owner chooses *which actor/action is eligible to enter the queue*, while GenLayer consensus decides only whether that admitted operation commutes with another admitted operation. The `actor` may differ from the owner and is pinned into the grant.

Production integrations should compute `action_hash` from a canonical, domain-separated executable action representation. Interlock cannot prove that arbitrary free-form descriptions match off-chain execution.

## Modes

Each intent declares one bounded access mode:

| Mode | Meaning | Deterministic treatment |
|---|---|---|
| `READ` | no resource mutation | two READs commute automatically |
| `WRITE` | mutates resource state | semantic comparison where needed |
| `EXCLUSIVE` | requires sole in-flight control | conflicts with every other open operation |

Modes are deliberately coarse. A caller cannot escape semantic conflict by declaring a narrower custom mode.

## Semantic relation

For non-trivial pairs, validators independently classify the same frozen resource definition and the same two intent descriptions.

| Relation | Meaning | Scheduler consequence |
|---|---|---|
| `COMMUTES` | either completion order preserves both operations' meaning/correctness | may be granted concurrently |
| `CONFLICTS` | safe operation requires serialization | later/open candidate is blocked |
| `AMBIGUOUS` | insufficient information to prove commutativity | fails closed and blocks |

The conflict mask is bounded to:

- `WRITE_OVERLAP`
- `PRECONDITION_INVALIDATION`
- `EXCLUSIVE_LIFECYCLE`
- `ORDER_SENSITIVITY`
- `CAPACITY_CONTENTION`
- `IDENTITY_OR_OWNERSHIP`
- `UNKNOWN_SEMANTIC`

Consensus equivalence is based only on the bounded relation and bit mask. The leader's free-form rationale is not persisted as trusted protocol state; the stored pair summary is derived deterministically from those bounded fields.

## Fairness model

Interlock uses a **commuting FIFO queue**.

A candidate intent must commute with:

- every currently granted intent; and
- every earlier still-open intent.

This prevents a later conflicting operation from jumping an older waiter, while allowing a later operation to bypass earlier work only when the relationship is consensus-established as commuting.

The queue is bounded (`24` open intents, `64` historical slots in the live scan window) to make worst-case work explicit.

## Liveness

Locks cannot be held forever:

- pending/blocked intents have a bounded queue TTL;
- grants have a bounded lease;
- **any caller** may crystallize expiry after the deadline;
- `resolve_intent` also expires stale blockers it encounters.

The resource owner cannot rewrite the semantic definition while intents are open. Pausing a resource blocks new admission/resolution and makes existing grants non-consumable through `is_grant_active` until the resource is unpaused or the grant expires.

## Resource version pinning

A resource has a canonical `definition_hash` derived from:

- name
- resource URI
- semantic description
- generation

Every intent pins that hash. Resource semantics can change only with zero open intents, and each update increments the generation.

This prevents policy substitution after the owner/gateway admitted an operation.

## Immutable pair memory

Once two exact intents are classified, their `PairDecision` is permanent and cached by intent IDs.

A later model cannot rewrite the relation because a blocked intent is retried. New intent IDs are required for new actions, and new resource generations produce new pinned definitions.

## Consumer contract

`contracts/protected_resource.py` is a deliberately tiny consumer example for the intended reuse boundary. Its local test uses a controlled interface stub because StudioNet Studio currently reports that it does not support contract-to-contract interactions. The contract deploys with the Interlock address, and the typed interface spelling passes GenVM lint, but the live `is_grant_active` call and full consumer lifecycle remain unproven on chain 61999.

Before recording a protected action it calls:

```python
interlock.view().is_grant_active(
    intent_id,
    expected_resource_hash,
    action_hash,
    actor,
)
```

The consumer also rejects an already-consumed `action_hash`, so a valid lease cannot be replayed to create the same side effect twice in that consumer.

Interlock itself does **not** claim the consumer executed the requested external effect. It only certifies that the exact actor/action/resource combination currently has a concurrency grant. Consumers must independently derive or verify `action_hash` from a canonical executable action.

## Main API

### Resource administration

```text
create_resource(name, resource_uri, semantics) -> resource_id
update_resource(resource_id, resource_uri, semantics)
set_resource_paused(resource_id, paused)
```

### Intent lifecycle

Only the resource owner (or an owner-controlled gateway contract) may admit an intent. `actor` is the address that may consume/complete the resulting grant.

```text
submit_intent(
    resource_id,
    actor,
    operation,
    mode,
    description,
    action_hash,
    queue_ttl_seconds,
    lease_seconds,
) -> intent_id

resolve_intent(intent_id) -> bool
complete_intent(intent_id)
cancel_intent(intent_id)
expire_intent(intent_id) -> bool
```

### Reuse views

```text
get_resource(resource_id)
get_intent(intent_id)
get_pair_decision(left_intent_id, right_intent_id)
is_grant_active(intent_id, expected_resource_hash, expected_action_hash, actor)
queue_snapshot(resource_id, limit)
constants()
```

## Reviewer demo scenario

Use one order-like resource and four operations:

1. `READ status` — READ
2. `READ shipping metadata` — READ
3. `DISPATCH order` — WRITE
4. `CANCEL order` — WRITE

Demonstrate:

1. both reads are granted without any LLM call;
2. dispatch is granted;
3. cancel is independently classified `CONFLICTS` with dispatch and becomes `BLOCKED`;
4. the validator re-runs the classification and rejects a forged `COMMUTES` leader result;
5. after dispatch completes/expires, cancel resolves and is granted;
6. `ProtectedResource` rejects cancel before the grant and accepts the exact pinned action after the grant;
7. replaying that action hash is rejected.

That demo shows deterministic fast paths, semantic consensus, shared scheduling state, liveness, and actual composability in one lifecycle.

## Tests

Install the StudioNet-compatible direct-mode test dependency:

```bash
python -m pip install -r requirements-test.txt
pytest -q tests/direct
python scripts/preflight.py
```

The pinned direct suite currently has 30 passing tests covering owner-only admission, distinct actor binding, resource pinning, pause/update restrictions, exact-action deduplication, deterministic read/exclusive cases, semantic commute/conflict/ambiguity, independent validator re-derivation, immutable pair decisions, lease expiry, queue liveness, actor/owner lifecycle authorization, bounded queues, FIFO fairness, and the consumer rejection/acceptance/replay boundary through a test interface stub.

## What Interlock does not prove

Interlock intentionally does **not** claim:

- that an operation is authorized;
- that an operation is economically desirable;
- that the action payload is truthful;
- that the consumer actually completed an off-chain side effect;
- that two operations on different registered resources are independent;
- that ambiguous operations are safe.

It provides one primitive only: **bounded semantic concurrency control for a shared resource**.

## Repository map

```text
contracts/interlock.py             core reusable primitive
contracts/protected_resource.py    minimal consuming IC
tests/direct/                       Direct Mode behavioural/adversarial tests
docs/ARCHITECTURE.md               protocol architecture
docs/INVARIANTS.md                 safety/liveness invariants
docs/THREAT_MODEL.md               adversarial analysis
docs/REVIEWER_DEMO.md              live reviewer walkthrough
DEPLOYMENT.md                       StudioNet 61999 deployment checklist
SUBMISSION.md                       submission-ready explanation
scripts/preflight.py                static repository/network checks
```

## License

MIT.

