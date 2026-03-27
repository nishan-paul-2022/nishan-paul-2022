import os
import subprocess
import json
from datetime import datetime, timedelta
import collections

# CONFIGURATION
DOCUMENTS_DIR = "/home/nishan/Documents" # Root where repos live
PROJECT_DIR = "/home/nishan/Documents/nishan-paul-2022"
GITHUB_USER_BASE_URL = "https://github.com/nishanpaul"

def run_cmd(cmd, cwd=None):
    try:
        return subprocess.check_output(cmd, shell=True, cwd=cwd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
    except:
        return ""

def collect_stats():
    # Identify all repos in Documents
    base_path = DOCUMENTS_DIR
    repos = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
    
    # Global Aggregators
    total_commits = 0
    total_loc = 0
    all_commit_dates = []
    
    lang_loc_map = collections.Counter()
    weekday_commits = collections.Counter()
    repo_list = []

    # Extension to Language mapping
    ext_map = {
        ".cpp": "C++", ".c": "C", ".js": "JavaScript", ".ts": "TypeScript", 
        ".py": "Python", ".html": "HTML", ".css": "CSS", ".md": "Markdown",
        ".php": "PHP", ".java": "Java", ".dart": "Dart", ".json": "JSON"
    }

    print(f"Analyzing {len(repos)} repositories...")

    for repo in repos:
        repo_path = os.path.join(base_path, repo)
        if not os.path.exists(os.path.join(repo_path, ".git")):
            continue
        
        # 1. Commit Count
        commit_count = run_cmd("git rev-list --count HEAD", cwd=repo_path)
        if not commit_count: continue
        total_commits += int(commit_count)
        
        # 2. Commit Dates & Weekly Activity
        dates_raw = run_cmd('git log --pretty=format:"%as"', cwd=repo_path)
        if dates_raw:
            dates = dates_raw.split('\n')
            all_commit_dates.extend(dates)
            for d in dates:
                if d:
                    weekday = datetime.strptime(d, "%Y-%m-%d").weekday()
                    weekday_commits[weekday] += 1
        
        # 3. LOC per Language
        files = run_cmd("git ls-files", cwd=repo_path).split('\n')
        repo_loc = 0
        for f in files:
            if not f or os.path.islink(os.path.join(repo_path, f)): continue
            ext = os.path.splitext(f)[1].lower()
            if ext in ext_map:
                try:
                    f_path = os.path.join(repo_path, f)
                    if os.path.isfile(f_path):
                        count = int(run_cmd(f"wc -l < {f_path}"))
                        lang_loc_map[ext_map[ext]] += count
                        repo_loc += count
                except: pass
        
        total_loc += repo_loc
        
        # Build live Repository Object
        repo_list.append({
            "name": repo,
            "url": f"{GITHUB_USER_BASE_URL}/{repo}",
            "commits": int(commit_count),
            "loc": repo_loc
        })

    # Calculations
    sorted_unique_dates = sorted(list(set(all_commit_dates)))
    first_date = datetime.strptime(sorted_unique_dates[0], "%Y-%m-%d") if sorted_unique_dates else datetime.now()
    tenure_days = (datetime.now() - first_date).days
    tenure_years = tenure_days / 365.25
    velocity = total_commits / max(tenure_days / 30.44, 1)

    # Weekly Averages
    total_weeks = max(tenure_days / 7, 1)
    weekly_avg = {i: weekday_commits[i] / total_weeks for i in range(7)}
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    formatted_weekly = {weekday_names[i]: round(weekly_avg[i], 2) for i in range(7)}

    # Language Percentages
    lang_percentages = {lang: round((count/total_loc)*100, 2) for lang, count in lang_loc_map.items() if total_loc > 0}
    
    # Streak
    streak = 0
    if sorted_unique_dates:
        rev_dates = sorted_unique_dates[::-1]
        today = datetime.now().date()
        latest = datetime.strptime(rev_dates[0], "%Y-%m-%d").date()
        if latest in [today, today - timedelta(days=1)]:
            streak, curr = 1, latest
            for i in range(1, len(rev_dates)):
                nxt = datetime.strptime(rev_dates[i], "%Y-%m-%d").date()
                if (curr - nxt).days == 1: streak, curr = streak + 1, nxt
                elif (curr - nxt).days == 0: continue
                else: break

    data = {
        "global": {
            "total_repos": len(repo_list),
            "total_commits": total_commits,
            "total_loc": total_loc,
            "tenure_years": round(tenure_years, 1),
            "avg_commits_month": round(velocity, 1),
            "streak_days": streak,
            "avg_loc_per_project": int(total_loc / len(repo_list)) if repo_list else 0
        },
        "languages": dict(sorted(lang_percentages.items(), key=lambda x: x[1], reverse=True)),
        "weekly_activity": formatted_weekly,
        # ALPHABETICAL SORT BY NAME
        "repositories": sorted(repo_list, key=lambda x: x['name'], reverse=False)
    }

    # Save JSON
    json_path = os.path.join(PROJECT_DIR, "repo-stats.json")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=4)
    
    return data

if __name__ == "__main__":
    stats_data = collect_stats()
    print("REPO_STATS_JSON_UPDATED_LINKED_SORTED")
