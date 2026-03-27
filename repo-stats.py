import os
import subprocess
import json
from datetime import datetime, timedelta
import collections

DOCUMENTS_DIR = "/home/nishan" # Root where repos live
PROJECT_DIR = "/home/nishan/Documents/nishan-paul-2022"

def run_cmd(cmd, cwd=None):
    try:
        return subprocess.check_output(cmd, shell=True, cwd=cwd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
    except:
        return ""

def collect_stats():
    # Identify all repos in Documents
    base_path = "/home/nishan/Documents"
    repos = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
    
    # Global Aggregators
    total_commits = 0
    total_loc = 0
    all_commit_dates = []
    
    lang_loc_map = collections.Counter()
    framework_repo_counts = collections.Counter()
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
        
        # 3. LOC per Language (Handwritten)
        files = run_cmd("git ls-files", cwd=repo_path).split('\n')
        repo_loc = 0
        for f in files:
            if not f or os.path.islink(os.path.join(repo_path, f)): continue
            ext = os.path.splitext(f)[1].lower()
            if ext in ext_map:
                try:
                    f_path = os.path.join(repo_path, f)
                    if os.path.isfile(f_path):
                        # Fast line count for specific extension
                        count = int(run_cmd(f"wc -l < {f_path}"))
                        lang_loc_map[ext_map[ext]] += count
                        repo_loc += count
                except: pass
        
        total_loc += repo_loc
        
        # 4. Framework Detection
        if os.path.exists(os.path.join(repo_path, "package.json")): framework_repo_counts["Next.js/Node.js"] += 1
        if os.path.exists(os.path.join(repo_path, "requirements.txt")): framework_repo_counts["FastAPI/Python"] += 1
        if os.path.exists(os.path.join(repo_path, "tailwind.config.js")): framework_repo_counts["Tailwind CSS"] += 1
        if os.path.exists(os.path.join(repo_path, "CMakeLists.txt")): framework_repo_counts["C++/Systems"] += 1

        repo_list.append({
            "name": repo,
            "commits": int(commit_count),
            "loc": repo_loc
        })

    # Calculations
    sorted_unique_dates = sorted(list(set(all_commit_dates)))
    first_date = datetime.strptime(sorted_unique_dates[0], "%Y-%m-%d") if sorted_unique_dates else datetime.now()
    tenure_days = (datetime.now() - first_date).days
    tenure_years = tenure_days / 365.25
    velocity = total_commits / max(tenure_days / 30.44, 1)

    # Weekly Averages (Total commits on Mon / Total weeks in history)
    total_weeks = max(tenure_days / 7, 1)
    weekly_avg = {i: weekday_commits[i] / total_weeks for i in range(7)}
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    formatted_weekly = {weekday_names[i]: round(weekly_avg[i], 2) for i in range(7)}

    # Language Percentages
    lang_percentages = {lang: round((count/total_loc)*100, 2) for lang, count in lang_loc_map.items() if total_loc > 0}
    
    # Framework Percentages (based on repo adoption)
    framework_percentages = {fm: round((count/len(repo_list))*100, 2) for fm, count in framework_repo_counts.items()}

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
        "frameworks": dict(sorted(framework_percentages.items(), key=lambda x: x[1], reverse=True)),
        "weekly_activity": formatted_weekly,
        "repositories": sorted(repo_list, key=lambda x: x['commits'], reverse=True)
    }

    # Save JSON
    json_path = os.path.join(PROJECT_DIR, "repo-stats.json")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=4)
    
    return data

def generate_markdown(data):
    md = f"""# 📊 Global Development Ecosystem Board

---

## 📈 High-Level Insights
*Aggregated performance metrics from your production workspace*

<div align="center">
  <table width="100%" style="border-collapse: collapse; border: 1px solid #30363d; border-radius: 12px;">
    <tr>
      <td width="25%" align="center" style="padding: 25px;">
        <img src="https://img.shields.io/badge/DEVELOPER_TENURE-{data['global']['tenure_years']}_Years-brightgreen?style=for-the-badge&logo=opsgenie&logoColor=white" height="35" />
      </td>
      <td width="25%" align="center" style="padding: 25px;">
        <img src="https://img.shields.io/badge/COMMIT_VELOCITY-{data['global']['avg_commits_month']}_MO-blue?style=for-the-badge&logo=speedtest&logoColor=white" height="35" />
      </td>
      <td width="25%" align="center" style="padding: 25px;">
        <img src="https://img.shields.io/badge/TOTAL_COMMITS-{data['global']['total_commits']}-purple?style=for-the-badge&logo=git&logoColor=white" height="35" />
      </td>
      <td width="25%" align="center" style="padding: 25px;">
        <img src="https://img.shields.io/badge/ACTIVE_STREAK-{data['global']['streak_days']}_DAYS-orange?style=for-the-badge&logo=hotjar&logoColor=white" height="35" />
      </td>
    </tr>
  </table>
</div>

---

## 🛠️ Technology & Framework Distribution
*A breakdown of architectural choices across all projects*

<div align="center">

| Language Proficiency | Weight (%) | Framework Adoption | Usage (%) |
| :--- | :---: | :--- | :---: |
"""
    # Merge Languages and Frameworks for the table
    langs = list(data['languages'].items())
    fms = list(data['frameworks'].items())
    max_len = max(len(langs), len(fms))
    
    for i in range(max_len):
        l_name, l_val = langs[i] if i < len(langs) else ("", "")
        f_name, f_val = fms[i] if i < len(fms) else ("", "")
        
        l_bar = f"![](https://img.shields.io/badge/--{l_val}%25-blue?style=flat-square)" if l_val else ""
        f_bar = f"![](https://img.shields.io/badge/--{f_val}%25-purple?style=flat-square)" if f_val else ""
        
        md += f"| **{l_name}** | {l_bar} | **{f_name}** | {f_bar} |\n"

    md += """
</div>

---

## 📅 Weekly Commit Frequency (Average)
*Consistency analysis per day of the week*

<div align="center">
"""
    for day, avg in data['weekly_activity'].items():
        md += f"  <img src='https://img.shields.io/badge/{day}-{avg}_avg-333?style=for-the-badge' /> \n"

    md += f"""
</div>

---

## 📁 Repository Deep-Dive
*Project-by-project activity and complexity (Sorted by Commits)*

<div align="center">

| Repository Name | Commits | Handwritten LOC | Complexity |
| :--- | :---: | :---: | :---: |
"""
    for repo in data['repositories']:
        complexity = "High" if repo['loc'] > 50000 else ("Medium" if repo['loc'] > 10000 else "Stable")
        badge_color = "red" if complexity == "High" else ("yellow" if complexity == "Medium" else "success")
        md += f"| `{repo['name']}` | **{repo['commits']}** | {repo['loc']:,} | ![{complexity}](https://img.shields.io/badge/-{complexity}-{badge_color}?style=flat-square) |\n"

    md += f"""
</div>

---

## ⚡ Productivity Constants
- **System Density:** Average handwritten code per project is **{data['global']['avg_loc_per_project']:,}** lines.
- **Global Footprint:** Total audited codebase represents **{data['global']['total_loc']:,}** lines of original logic.
- **Maintainability:** All metrics exclude external libraries, frameworks (node_modules, vendor), and assets.

---

<div align="center">
  <i>"This dossier is automatically synced from local Git history to ensure real-time accuracy."</i>
</div>
"""
    # Write Markdown
    md_path = os.path.join(PROJECT_DIR, "repo-stats.md")
    with open(md_path, "w") as f:
        f.write(md)

if __name__ == "__main__":
    stats_data = collect_stats()
    generate_markdown(stats_data)
    print("ALL_STATS_COMPLETE")
