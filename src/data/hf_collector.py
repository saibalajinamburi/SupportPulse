import os
import json
from pathlib import Path
from datasets import load_dataset

def collect_hf_dataset(dataset_name: str, output_path: str):
    print(f"\nDownloading dataset: {dataset_name}...")
    try:
        # Some datasets have configs or splits. We try to grab the 'train' split by default.
        dataset = load_dataset(dataset_name, split='train')
    except Exception as e:
        print(f"Error loading {dataset_name}: {e}")
        return
        
    print(f"Columns available: {dataset.column_names}")
    print(f"Number of rows: {len(dataset)}")
    
    # Convert to list of dicts
    data = dataset.to_dict()
    
    # Convert columnar dict to row dicts
    rows = []
    for i in range(len(dataset)):
        row = {col: data[col][i] for col in dataset.column_names}
        rows.append(row)
        
    # Save as JSON
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to {output_path}")

def main():
    print("Starting Hugging Face Data Collection...")
    output_dir = "data/bronze/zendesk"
    
    collect_hf_dataset(
        "Tobi-Bueck/customer-support-tickets",
        f"{output_dir}/tobi_bueck_raw.json"
    )
    
    collect_hf_dataset(
        "gorkemsevinc/customer_support_tickets",
        f"{output_dir}/gorkemsevinc_raw.json"
    )
    
    print("\nCollection Complete.")

if __name__ == "__main__":
    main()
