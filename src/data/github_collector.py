import os
import json
import time
import requests
from tqdm import tqdm
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from app.config import settings

def load_repos(filepath: str) -> List[str]:
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def fetch_issues_page(repo: str, page: int, pat: str) -> requests.Response:
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {pat}" if pat else "",
        "User-Agent": "SupportPulse-Data-Collector"
    }
    params = {
        "state": "all",
        "per_page": 100,
        "page": page
    }
    
    # Retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            return response
        except requests.exceptions.RequestException as e:
            print(f"\n[Error] Network error fetching {repo} page {page}: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise

def handle_rate_limits(response: requests.Response):
    remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
    if remaining < 100:
        reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
        sleep_duration = max(reset_time - time.time(), 0) + 10
        print(f"\n[Rate Limit] Approaching rate limit. Sleeping for {sleep_duration:.0f} seconds...")
        time.sleep(sleep_duration)

def process_issue(issue: Dict[str, Any], repo: str) -> Dict[str, Any]:
    # Extract only what we need
    return {
        "title": issue.get("title", ""),
        "body": issue.get("body", ""),
        "labels": [label["name"] for label in issue.get("labels", []) if isinstance(label, dict)],
        "state": issue.get("state", ""),
        "created_at": issue.get("created_at", ""),
        "closed_at": issue.get("closed_at", ""),
        "comments_url": issue.get("comments_url", ""),
        "repo": repo,
        "issue_number": issue.get("number", ""),
        "is_pull_request": "pull_request" in issue
    }

def main():
    start_time = time.time()
    repos = load_repos("configs/github_repos.txt")
    pat = settings.GITHUB_PAT
    
    output_dir = Path("data/bronze/github")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_issues_collected = 0
    errors = 0
    
    print(f"Starting collection for {len(repos)} repositories...")
    
    for repo in repos:
        repo_safe_name = repo.replace("/", "_")
        page = 1
        
        print(f"\nCollecting issues from {repo}...")
        
        while True:
            response = fetch_issues_page(repo, page, pat)
            
            if response.status_code != 200:
                print(f"\n[Error] Failed to fetch {repo} page {page}. Status: {response.status_code}")
                print(response.text)
                errors += 1
                break
                
            issues = response.json()
            if not issues:
                break # No more issues
                
            handle_rate_limits(response)
            
            # Filter out PRs and process
            processed_issues = [process_issue(iss, repo) for iss in issues if "pull_request" not in iss]
            
            if processed_issues:
                output_file = output_dir / f"repo_{repo_safe_name}_page_{page}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed_issues, f, ensure_ascii=False, indent=2)
                
                total_issues_collected += len(processed_issues)
                print(f"  -> Saved {len(processed_issues)} issues from page {page}")
            
            # Check pagination link to see if we reached the end
            if "next" not in response.links:
                break
                
            page += 1

    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "="*50)
    print("COLLECTION COMPLETE")
    print(f"Total Repositories: {len(repos)}")
    print(f"Total Issues Collected: {total_issues_collected}")
    print(f"Time Taken: {duration/60:.2f} minutes")
    print(f"Errors Encountered: {errors}")
    print("="*50)

if __name__ == "__main__":
    main()
