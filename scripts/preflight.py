"""Repository preflight for the Interlock standalone IC submission."""

from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET_CHAIN = "61999"
REQUIRED = [
    "README.md",
    "SUBMISSION.md",
    "DEPLOYMENT.md",
    "contracts/interlock.py",
    "contracts/protected_resource.py",
    "tests/direct/test_interlock.py",
    "docs/ARCHITECTURE.md",
    "docs/INVARIANTS.md",
    "docs/THREAT_MODEL.md",
    "docs/REVIEWER_DEMO.md",
    "gltest.config.yaml",
]
FORBIDDEN_DIRS = {"node_modules", ".next", "dist", "build", ".venv", "venv"}
FRONTEND_MARKERS = {"package.json", "next.config.js", "next.config.mjs", "vite.config.js", "vite.config.ts"}
SECRET_PATTERNS = [
    re.compile(r"(?i)(private[_ -]?key|seed phrase|mnemonic)\s*[:=]\s*[A-Za-z0-9+/=_-]{16,}"),
    re.compile(r"0x[a-fA-F0-9]{64}"),
]
PUBLIC_RECEIPT_HASHES = {
    "0x50d7acf99e4401e53e412198ae5ec8bcabe534e8139e0ed396f4b208885ebdbd",
    "0xe560813006d8d17029589e10698ae867c4597c50f7c7340010ca768452f92b91",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


for rel in REQUIRED:
    if not (ROOT / rel).exists():
        fail(f"missing required file: {rel}")

for path in ROOT.rglob("*"):
    if path.relative_to(ROOT).parts[0] in {".venv", "venv"}:
        continue
    if path.is_dir() and path.name in FORBIDDEN_DIRS:
        fail(f"forbidden generated directory present: {path.relative_to(ROOT)}")
    if path.is_file() and path.name in FRONTEND_MARKERS:
        fail(f"frontend marker present in contract-only repository: {path.relative_to(ROOT)}")

for contract in (ROOT / "contracts").glob("*.py"):
    try:
        ast.parse(contract.read_text(encoding="utf-8"), filename=str(contract))
    except SyntaxError as exc:
        fail(f"syntax error in {contract.name}: {exc}")

# Network hygiene: 61999 must be present; common accidental devnet identifier
# is intentionally not named here so it can never leak into project files.
all_text = ""
for path in ROOT.rglob("*"):
    if any(part in {".venv", "venv", "__pycache__", ".pytest_cache", "artifacts"} for part in path.relative_to(ROOT).parts):
        continue
    if path.is_file() and path.suffix.lower() in {".md", ".py", ".yaml", ".yml", ".txt", ".toml", ".example"}:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        all_text += "\n" + text
        if path.name != ".env.example":
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    # 64-char action hashes in tests are obvious repeated chars;
                    # avoid flagging those while still catching plausible secrets.
                    match = pattern.search(text)
                    if (
                        match
                        and match.group(0).lower() not in PUBLIC_RECEIPT_HASHES
                        and len(set(match.group(0).lower())) > 10
                    ):
                        fail(f"possible secret-like material in {path.relative_to(ROOT)}")

if TARGET_CHAIN not in all_text:
    fail("target chain id 61999 is not documented")
if "https://studio.genlayer.com/api" not in (ROOT / "gltest.config.yaml").read_text():
    fail("studionet API is missing from gltest.config.yaml")
if not re.search(r"(?m)^\s*default:\s*studionet\s*$", (ROOT / "gltest.config.yaml").read_text()):
    fail("gltest default network must be studionet")

contract_text = (ROOT / "contracts/interlock.py").read_text()
for needle in (
    "run_nondet_unsafe",
    "RELATION_COMMUTES",
    "RELATION_CONFLICTS",
    "RELATION_AMBIGUOUS",
    "is_grant_active",
    "queue_expires_at",
    "grant_expires_at",
):
    if needle not in contract_text:
        fail(f"core contract invariant marker missing: {needle}")

print("PASS: Interlock preflight")
print("- contract-only repository: yes")
print("- target chain documented: 61999")
print("- contract Python syntax: parseable")
print("- consensus/liveness markers: present")
