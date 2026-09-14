# Architecture

## Design objective

Interlock is a lock manager whose conflict relation is not limited to syntactic keys. It treats semantic commutativity as a consensus question while keeping admission, scheduling, fairness, expiry, replay resistance, and state transitions deterministic.

## Trust boundary

The **resource owner (or an owner-controlled gateway contract)** admits intents. This is intentional: allowing arbitrary callers to enqueue locks would make permissionless lock-DoS trivial. Each admitted intent names the `actor` that may consume the resulting grant; the actor may differ from the resource owner.

Interlock is **not an authorization system**. The owner/gateway is responsible for deciding whether an actor is allowed to request the underlying action and for ensuring `action_hash` commits to the canonical executable action. Interlock only controls concurrency after admission.

The resource owner controls the resource definition and admitted intent descriptions, but it does not control the consensus result for a non-trivial pair.

The LLM is allowed to classify only one bounded relationship between two already-frozen operations:

```text
COMMUTES | CONFLICTS | AMBIGUOUS
```

It cannot grant an operation directly, choose queue priority, alter a resource, change an action hash, authorize an actor, or execute a consumer.

## State objects

### `ResourceProfile`

A shared concurrency domain. Resource semantics describe what state/lifecycle the resource represents and what kinds of effects can interact. The definition is versioned and cannot change while open intents exist.

### `Intent`

An owner-admitted request for one `actor`/action to acquire a bounded concurrency grant. The exact action is pinned by `action_hash`; the concurrency meaning is provided by `operation`, `mode`, and `description`.

### `PairDecision`

An immutable cached classification for two exact intent IDs under their pinned resource hash.

The contract does **not** persist the leader's free-form rationale. Validators agree on only `relation` and `conflict_mask`; the stored `reason` field is derived deterministically from those consensus fields. This prevents unverified leader-authored prose from becoming protocol state.

## Deterministic fast paths

Two relations never need semantic consensus:

```text
READ + READ       => COMMUTES
EXCLUSIVE + any   => CONFLICTS
```

Everything else may require consensus.

## Consensus path

For non-trivial pairs:

1. the leader receives the frozen resource and both frozen intents;
2. the leader proposes `relation + conflict_mask`;
3. a validator independently performs the same semantic classification;
4. the validator accepts only if both bounded fields match exactly;
5. free-form model rationale is ignored for equivalence and never persisted as trusted state;
6. malformed/incomplete output canonicalizes to `AMBIGUOUS + UNKNOWN_SEMANTIC`.

`AMBIGUOUS` is first-class and fails closed.

## Scheduler

When `resolve_intent(candidate)` runs, candidate must commute with:

```text
all GRANTED intents
+
all earlier PENDING/BLOCKED intents
```

If not, candidate is `BLOCKED` with `last_blocker_id`. If yes, it becomes `GRANTED` with a deterministic lease deadline.

This is a commuting FIFO: safe independent work may proceed in parallel, while conflicting work cannot jump an older open intent.

## Liveness

Every open state has a deadline:

- `queue_expires_at` for PENDING/BLOCKED;
- `grant_expires_at` for GRANTED.

Expiry is permissionless. Any caller can crystallize an expired state, and `resolve_intent` clears expired blockers it encounters. A resource pause also makes existing grants fail `is_grant_active`, providing a deterministic emergency stop without rewriting intent history.

## Definition mutation

`update_resource` requires `open_count == 0`. Every intent also pins the current resource `definition_hash`, so a pair can never be reinterpreted under a silently changed resource definition.

## Consumer binding

A consuming contract should pin:

```text
intent_id
resource_definition_hash
action_hash
actor
```

It should also implement replay protection and independently ensure the supplied `action_hash` is the canonical digest of the action it is about to perform. `ProtectedResource` implements the concurrency-grant/replay boundary in code and local tests; it is intentionally not a general authorization layer. Studio's current UI reports no support for contract-to-contract interactions, so its live typed call has not been verified on chain 61999. No on-chain consumption claim should be inferred from the finalized consumer deployment alone.

## Why there is no frontend

Interlock is infrastructure. A frontend would imply a particular product workflow and weaken the standalone Intelligent Contract primitive boundary. Builders should integrate the interface into their own contracts or applications.
