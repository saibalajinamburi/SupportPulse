import json
import uuid
import os
from pathlib import Path

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

def main():
    print("Combining Bronze Data...")
    
    bronze_dir = Path("data/bronze")
    github_dir = bronze_dir / "github"
    zendesk_dir = bronze_dir / "zendesk"
    synthetic_dir = bronze_dir / "synthetic"
    
    all_tickets = []
    counts = {"github": 0, "hf_customer_support": 0, "synthetic": 0}
    
    # 1. Load GitHub Data
    if github_dir.exists():
        for file in github_dir.glob("*.json"):
            data = load_json(file)
            for item in data:
                # Map to schema roughly
                mapped = {
                    "ticket_id": f"GH-{item.get('repo', 'unknown')}-{item.get('issue_number', uuid.uuid4().hex[:6])}",
                    "source": "github",
                    "created_at": item.get("created_at"),
                    "subject": item.get("title", ""),
                    "body": item.get("body", ""),
                    "labels_raw": item.get("labels", [])
                }
                if not mapped["subject"] or not mapped["body"] or len(str(mapped["body"])) < 20:
                    continue
                all_tickets.append(mapped)
                counts["github"] += 1
                
    # 2. Load Zendesk / Hugging Face Data
    if zendesk_dir.exists():
        # Tobi Bueck
        tobi_file = zendesk_dir / "tobi_bueck_raw.json"
        if tobi_file.exists():
            data = load_json(tobi_file)
            for item in data:
                mapped = {
                    "ticket_id": f"HF-TOBI-{uuid.uuid4().hex[:8]}",
                    "source": "hf_customer_support",
                    "created_at": None,  # Has no date
                    "subject": item.get("subject", ""),
                    "body": item.get("body", ""),
                    "labels_raw": [item.get("queue", ""), item.get("type", "")]
                }
                if not mapped["subject"] or not mapped["body"] or len(str(mapped["body"])) < 20:
                    continue
                all_tickets.append(mapped)
                counts["hf_customer_support"] += 1
                
        # Gorkemsevinc
        gorkem_file = zendesk_dir / "gorkemsevinc_raw.json"
        if gorkem_file.exists():
            data = load_json(gorkem_file)
            for item in data:
                mapped = {
                    "ticket_id": f"HF-GORKEM-{uuid.uuid4().hex[:8]}",
                    "source": "hf_customer_support",
                    "created_at": None,
                    "subject": item.get("Ticket Subject", ""),
                    "body": item.get("Combined Text", ""),
                    "labels_raw": [item.get("Ticket Type", "")]
                }
                if not mapped["subject"] or not mapped["body"] or len(str(mapped["body"])) < 20:
                    continue
                all_tickets.append(mapped)
                counts["hf_customer_support"] += 1

    # 3. Load Synthetic Data
    if synthetic_dir.exists():
        synth_file = synthetic_dir / "synthetic_tickets.json"
        if synth_file.exists():
            data = load_json(synth_file)
            for item in data:
                # Already in schema format mostly
                if not item.get("subject") or not item.get("body") or len(str(item.get("body"))) < 20:
                    continue
                all_tickets.append(item)
                counts["synthetic"] += 1

    # Save combined
    output_file = bronze_dir / "all_bronze_combined.json"
    print(f"\nWriting {len(all_tickets)} combined tickets to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_tickets, f, indent=2)
        
    print("\nCombine Summary:")
    print("-" * 20)
    for source, count in counts.items():
        print(f"{source.upper()}: {count} tickets")
    print("-" * 20)
    print(f"TOTAL: {len(all_tickets)} tickets")

if __name__ == "__main__":
    main()
