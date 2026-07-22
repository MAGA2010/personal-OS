#!/usr/bin/env python3
"""Merge pipeline real data into frontend universities.json."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
FRONTEND_DATA = ROOT / "frontend" / "src" / "data"
ARTIFACTS = ROOT / "data-pipeline" / "artifacts"

def load_json(p):
    with open(p) as f:
        return json.load(f)

def build_name_to_candidate(pipeline_unis):
    name_to_candidate = {}
    for u in pipeline_unis["universities"]:
        cid = u["candidate_id"]
        name_to_candidate[u["display_name"].lower().replace("-", " ").strip()] = cid
        for alias in u.get("known_aliases", []):
            name_to_candidate[alias.lower().strip()] = cid
        # Also try by candidate_id suffix
        suffix = cid.replace("candidate-v2:", "")
        name_to_candidate[suffix.replace("-", " ").strip()] = cid
    return name_to_candidate

def build_lookup(records, key_field="candidate_id"):
    return {u[key_field]: u for u in records.get("universities", [])}

def extract_pipeline_id(fe_id, fe_name, name_to_candidate):
    cid = f"candidate-v2:{fe_id}"
    if cid in name_to_candidate.values():
        return cid
    fe_name_lower = fe_name.lower().strip()
    fe_key = fe_id.replace("-", " ").strip()
    for k, v in name_to_candidate.items():
        if k == fe_name_lower or k == fe_key:
            return v
        # sub-string match
        words = set(fe_key.split())
        k_words = set(k.split())
        if len(words & k_words) >= max(2, len(words) - 1):
            return v
    return None

def convert_tuition(tuition_record):
    if not tuition_record:
        return None
    highest = tuition_record.get("highest_tuition_program", {}) or {}
    if highest.get("amount"):
        return round(highest["amount"] * 7.3, -3)
    for display in tuition_record.get("program_tuition_display", []):
        if display and display.get("displayed_amount"):
            return round(display["displayed_amount"] * 7.3, -3)
    return None

def extract_programs(pipeline_uni):
    if not pipeline_uni:
        return None
    programs = pipeline_uni.get("top_5_programs_for_demo", [])
    if not programs:
        return None
    names = [p.get("program_name", "").replace(", General", "").replace(", general", "") for p in programs]
    return [n for n in names if n]

def main():
    print("Loading data...")
    frontend = load_json(FRONTEND_DATA / "universities.json")
    pipeline_unis = load_json(ARTIFACTS / "stage3-program-mvp-detail-pack" / "program-mvp-universities.json")
    pipeline_tuition = load_json(ARTIFACTS / "stage3-program-mvp-detail-pack" / "program-mvp-tuition.json")

    history_path = ARTIFACTS / "stage3d-fill-bulk-completion-v2" / "stage3d-fill-bulk-v2-history.json"
    anecdotes_path = ARTIFACTS / "stage3d-fill-bulk-completion-v2" / "stage3d-fill-bulk-v2-anecdotes.json"
    history = load_json(history_path) if history_path.exists() else None
    anecdotes = load_json(anecdotes_path) if anecdotes_path.exists() else None

    name_to_candidate = build_name_to_candidate(pipeline_unis)
    univ_lookup = build_lookup(pipeline_unis)
    tuition_lookup = build_lookup(pipeline_tuition)
    history_lookup = build_lookup(history) if history else {}
    anecdotes_list = []
    if anecdotes:
        for u in anecdotes.get("universities", []):
            cid = u.get("candidate_id", "")
            anecdotes_list.append({"candidate_id": cid, "text": u.get("anecdote_text", ""), "type": u.get("anecdote_type", "general")})

    stats = {"found": 0, "not_found": 0, "tuition": 0, "programs": 0, "history": 0, "anecdotes": 0}

    for uni in frontend["universities"]:
        cid = extract_pipeline_id(uni["id"], uni["name"], name_to_candidate)
        if not cid:
            stats["not_found"] += 1
            continue
        stats["found"] += 1

        # Tuition
        tr = tuition_lookup.get(cid)
        new_cost = convert_tuition(tr)
        if new_cost and uni.get("annualCostRmb") != new_cost:
            uni["annualCostRmb"] = new_cost
            stats["tuition"] += 1

        # Programs
        pu = univ_lookup.get(cid)
        new_progs = extract_programs(pu)
        if new_progs:
            old_progs = uni.get("programs", [])
            if old_progs != new_progs and len(new_progs) >= 3:
                uni["programs"] = new_progs
                stats["programs"] += 1

        # History
        hr = history_lookup.get(cid)
        if hr and hr.get("history_summary"):
            old = uni.get("historySummary", "")
            new = hr["history_summary"]
            if not old or (len(new) > len(old) and old not in new):
                uni["historySummary"] = new
                stats["history"] += 1

        # Anecdotes
        uni_anecdotes = [a for a in anecdotes_list if a["candidate_id"] == cid]
        if uni_anecdotes:
            existing = [{"text": a["text"], "type": a["type"]} for a in uni_anecdotes if a["text"]]
            if existing:
                old_anecdotes = uni.get("anecdotes", [])
                if not old_anecdotes or len(existing) > len(old_anecdotes):
                    uni["anecdotes"] = existing
                    stats["anecdotes"] += 1

    frontend["_lastUpdated"] = "2026-07-22"
    frontend["_mergedFrom"] = "data-pipeline/artifacts (Program MVP + Stage 3D)"

    output_path = FRONTEND_DATA / "universities.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(frontend, f, ensure_ascii=False, indent=2)

    print(f"=== Merge Summary ===")
    print(f"  Found: {stats['found']} / Not found: {stats['not_found']}")
    print(f"  Tuition updated: {stats['tuition']}")
    print(f"  Programs replaced: {stats['programs']}")
    print(f"  History added: {stats['history']}")
    print(f"  Anecdotes added: {stats['anecdotes']}")
    print(f"  Output: {output_path}")

if __name__ == "__main__":
    main()
