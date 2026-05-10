"""
Create HuggingFace Space and upload the demo app files.
Run once to set up the Space.

Usage: Set HF_TOKEN env var first:
  Windows: $env:HF_TOKEN = "your_hf_token_here"
  Linux:   export HF_TOKEN=your_hf_token_here
"""
import os
from huggingface_hub import HfApi, create_repo, upload_folder

HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    raise ValueError("Set HF_TOKEN environment variable. Get token from https://huggingface.co/settings/tokens")

REPO_ID = "saibalajinamburi/SupportPulse"
REPO_TYPE = "space"

api = HfApi(token=HF_TOKEN)

# Step 1: Create the Space (if it doesn't exist)
print(f"Creating/verifying Space: {REPO_ID}...")
try:
    create_repo(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        token=HF_TOKEN,
        space_sdk="gradio",
        exist_ok=True,
        private=False,
    )
    print("Space created/verified.")
except Exception as e:
    print(f"Note: {e}")

# Step 2: Upload the hf_space folder
print("Uploading hf_space/ folder to HuggingFace Space...")
upload_folder(
    folder_path="hf_space",
    repo_id=REPO_ID,
    repo_type=REPO_TYPE,
    token=HF_TOKEN,
    commit_message="Deploy SupportPulse demo: Gradio triage interface with pre-computed results",
    ignore_patterns=["*.pyc", "__pycache__", ".DS_Store"],
)

print(f"\nDeployed! View at: https://huggingface.co/spaces/{REPO_ID}")
