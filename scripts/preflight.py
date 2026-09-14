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
    # Public 32-byte hashes may appear in live evidence (deployment and
    # lifecycle receipts, canonical actions, resource definitions, decisions).
    "0xacfa75c76d7926e658abbf501dd83120fdd247d482f096ed59cf355b69349b9a",
    "0x511aadaee9c914dc650cc606d44508ec4365c31d83dea42152e2dd43f19cf0b7",
    "0x034ea2e3d9e0faf3b05d2483d3c248fbf8425c9e302347bc01dbb7e57d9634a6",
    "0x228cfae053473c51732d06c11d84271b2f38d169f88a5680ba88c6e456850a52",
    "0xe88dcc843d4188709720d039c2cd9eb8f469fa206e80d3210ef949870d1d6782",
    "0x0ab62edcad35e1886b481324582520455fc085a0f54d83fe2459b09024a02601",
    "0xbb6edb40ba45a916299590f09134d8df7e81ccc7b313c5f81c9fa09067707508",
    "0x0a41470c9f19ecb4d9a244b078308bb2eecf62c2777939703c8dc8ffd5d9d513",
    "0xd2cccaac729de07d0281db1c312865558d910c62c0454faccc6eb4f0d6dccf8e",
    "0x51dd7d9acf550103057daea4d0f21741c9c5c2c605af7d116ba0cae448629b66",
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
