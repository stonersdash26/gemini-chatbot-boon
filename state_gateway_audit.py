#!/usr/bin/env python3
import argparse
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path

def canonical_json_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def merkle_root(items):
    if not items:
        return sha256_hex(b"empty-state")

    level = [sha256_hex(canonical_json_bytes(item)) for item in items]

    if len(level) == 1:
        return level[0]

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])

        new_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1]
            combined = (left + right).encode("utf-8")
            new_level.append(sha256_hex(combined))
        level = new_level

    return level[0]

def load_state(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("State file must contain a JSON array of records.")
    return data

def read_ledger(path):
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries

def sign_payload(payload, secret):
    return hmac.new(secret.encode("utf-8"), canonical_json_bytes(payload), hashlib.sha256).hexdigest()

def make_snapshot_entry(state, actor, notes, previous_hash, secret, ledger_path=None):
    timestamp = datetime.now(timezone.utc).isoformat()
    state_root = merkle_root(state)

    payload = {
        "timestamp": timestamp,
        "actor": actor,
        "notes": notes,
        "previous_hash": previous_hash,
        "state_root": state_root,
        "state_count": len(state),
    }

    signature = sign_payload(payload, secret)
    entry = {
        **payload,
        "signature": signature,
    }

    if ledger_path is not None:
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")

    return entry

def verify_entry(entry, secret):
    if "signature" not in entry:
        return False

    payload = {
        "timestamp": entry["timestamp"],
        "actor": entry["actor"],
        "notes": entry["notes"],
        "previous_hash": entry.get("previous_hash"),
        "state_root": entry["state_root"],
        "state_count": entry["state_count"],
    }

    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, entry["signature"])

def verify_ledger(ledger_path, secret):
    ledger = read_ledger(Path(ledger_path))
    if not ledger:
        return {"valid": False, "reason": "ledger is empty"}

    prev_hash = None
    for idx, entry in enumerate(ledger):
        if not verify_entry(entry, secret):
            return {"valid": False, "entry_index": idx, "reason": "invalid signature"}

        if prev_hash is not None and entry["previous_hash"] != prev_hash:
            return {
                "valid": False,
                "entry_index": idx,
                "reason": "previous_hash mismatch",
                "expected_previous_hash": prev_hash,
                "actual_previous_hash": entry["previous_hash"],
            }

        prev_hash = sha256_hex(canonical_json_bytes(entry))
        # Note: this is a hash-chain identity for the ledger itself.
        # The actual state snapshot hash is entry["state_root"].

    return {"valid": True, "entries_verified": len(ledger), "last_hash": prev_hash}

def verify_current_state_against_snapshot(state_path, expected_state_root):
    state = load_state(state_path)
    actual_root = merkle_root(state)
    return actual_root == expected_state_root

def main():
    parser = argparse.ArgumentParser(description="State gateway audit: Merkle hash + ledger accountability + integrity validation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="Record a new state snapshot to the ledger")
    record.add_argument("--state", required=True, help="JSON state file (array of records)")
    record.add_argument("--actor", required=True, help="Who/what produced this state")
    record.add_argument("--notes", default="", help="Optional note")
    record.add_argument("--ledger", required=True, help="Ledger path (.jsonl)")
    record.add_argument("--secret", required=True, help="Shared secret for HMAC accountability")

    verify = subparsers.add_parser("verify", help="Verify the ledger and current state")
    verify.add_argument("--ledger", required=True, help="Ledger path (.jsonl)")
    verify.add_argument("--secret", required=True, help="Shared secret for HMAC accountability")
    verify.add_argument("--state", required=False, help="Optional current state file to verify against latest snapshot")

    args = parser.parse_args()

    if args.command == "record":
        if Path(args.ledger).exists():
            ledger = read_ledger(Path(args.ledger))
            previous_hash = sha256_hex(canonical_json_bytes(ledger[-1])) if ledger else None
        else:
            previous_hash = None

        state = load_state(args.state)
        entry = make_snapshot_entry(
            state=state,
            actor=args.actor,
            notes=args.notes,
            previous_hash=previous_hash,
            secret=args.secret,
            ledger_path=Path(args.ledger),
        )

        print(json.dumps({
            "status": "recorded",
            "state_count": len(state),
            "state_root": merkle_root(state),
            "entry": entry
        }, sort_keys=True, indent=2))

    elif args.command == "verify":
        result = verify_ledger(Path(args.ledger), args.secret)
        print(json.dumps(result, sort_keys=True, indent=2))

        if args.state:
            ledger = read_ledger(Path(args.ledger))
            if not ledger:
                print("No ledger entries found; cannot match current state.")
            else:
                latest = ledger[-1]
                ok = verify_current_state_against_snapshot(args.state, latest["state_root"])
                print(json.dumps({
                    "current_state_matches_latest_snapshot": ok,
                    "latest_state_root": latest["state_root"]
                }, sort_keys=True, indent=2))