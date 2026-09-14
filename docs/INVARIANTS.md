# Protocol invariants

## Admission and safety invariants

1. **No permissionless lock injection.** Only the resource owner (or owner-controlled gateway) may admit an intent.
2. **Actor is explicit.** Every admitted intent binds one actor; downstream grant checks must match it exactly.
3. **No duplicate action identity within a resource.** One `resource_id + action_hash` maps to only one intent.
4. **No semantic-policy substitution.** A resource definition cannot change while any intent is open.
5. **No silent ambiguity.** `AMBIGUOUS` is treated as non-commuting.
6. **No LLM scheduling authority.** Consensus only classifies a pair relation; deterministic code grants/blocks.
7. **No mutable pair history.** Once stored, a pair relation for exact intent IDs is reused.
8. **No bypass of older conflicting work.** A candidate must commute with all earlier open intents.
9. **No overlap with an active conflicting grant.** A candidate must commute with every active grant regardless of queue position.
10. **No unbounded queue.** Open intent count and live scan span are bounded.
11. **No grant replay by the example consumer.** `ProtectedResource` consumes each action hash once locally.
12. **No actor substitution.** `is_grant_active` binds the stored actor to the supplied actor.
13. **No action substitution.** `is_grant_active` requires the exact stored action hash.
14. **No resource-version substitution.** `is_grant_active` requires the exact pinned resource hash.
15. **No unverified leader prose in protocol state.** Stored pair summaries are deterministically derived from consensus fields.
16. **Pause fails closed.** A paused resource cannot admit/resolve new intents and existing grants are not consumable through `is_grant_active`.

## Liveness invariants

1. Pending and blocked intents can expire permissionlessly.
2. Granted intents have finite leases.
3. Expired blockers are cleared during resolution.
4. The bound actor or resource owner can cancel pending/blocked work.
5. The bound actor or resource owner can complete a live grant.
6. Completion/expiry decrements open/active counters exactly once.

## Consensus invariants

1. Validators do not accept JSON merely because it is well formed.
2. Validators independently re-run the bounded semantic decision.
3. Leader and validator must agree exactly on relation and conflict mask.
4. Free-form rationale wording is not part of equivalence and is not trusted protocol state.
5. Malformed model output fails closed to ambiguity.
6. Deterministic READ/READ and EXCLUSIVE cases do not invoke LLM consensus.
