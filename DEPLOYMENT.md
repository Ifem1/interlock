# Deployment

## Network lock

Interlock is prepared for exactly this target:

- **Network:** StudioNet
- **Chain ID:** `61999`
- **Studio API:** `https://studio.genlayer.com/api`

Do not change the network during finalization unless the project owner explicitly instructs it.

## Before deployment

```bash
python -m pip install -r requirements-test.txt
python scripts/preflight.py
pytest -q tests/direct
```

All direct tests must pass before any deployment evidence is written into the repository. The test count at this revision is 30.

## Deploy order

1. Deploy `contracts/interlock.py` with no constructor arguments.
2. Record the finalized Interlock contract address.
3. Deploy `contracts/protected_resource.py` with the Interlock address as its constructor argument.
4. Record the finalized ProtectedResource address.
5. Execute the lifecycle in `docs/REVIEWER_DEMO.md` only if Studio supports the required method and IC-to-IC calls.
6. Create/update `docs/STUDIONET_EVIDENCE.md` with finalized addresses and transaction hashes. Never treat deployment as proof that cross-contract calls work.
7. Re-run `python scripts/preflight.py` and the direct test suite.

## Studio configuration

`gltest.config.yaml` contains the requested StudioNet API preset. The final agent should verify the wallet/network selector itself also reports chain ID `61999` before signing any deployment.

At this submission's verification time, Studio's UI explicitly reports that contract-to-contract interactions are unsupported. Deployment of the consumer contract is confirmed, but live validation of its typed `is_grant_active` call and the consumer lifecycle is blocked by that Studio limitation. Record the exact current limitation and leave dependent live claims unproven until the UI/runtime supports those calls.

## Evidence policy

The repository currently contains **no fabricated deployment addresses or transaction hashes**. The final agent must insert only evidence obtained from finalized StudioNet transactions.

