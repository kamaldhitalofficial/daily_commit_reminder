"""
Daily Commit Reminder Script
Checks if there have been commits in the last 24 hours and creates an issue if not.
"""

import os
import subprocess
from datetime import datetime, timedelta
from github import Github
import sys

def get_last_commit_date():
    """Get the date of the last commit in the repository."""
    try:
        # Get the last commit timestamp
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ci'],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the timestamp
        commit_date_str = result.stdout.strip()
        commit_date = datetime.strptime(commit_date_str, '%Y-%m-%d %H:%M:%S %z')
        return commit_date.replace(tzinfo=None)  # Remove timezone for comparison

    except subprocess.CalledProcessError:
        print("Error: Could not get last commit date")
        return None

def should_create_reminder(last_commit_date, hours_threshold=24):
    """Check if we should create a reminder based on last commit date."""
    if last_commit_date is None:
        return True

    now = datetime.utcnow()
    time_since_commit = now - last_commit_date

    print(f"Last commit was {time_since_commit} ago")
    return time_since_commit > timedelta(hours=hours_threshold)

def create_reminder_issue(repo, days_since_commit):
    """Create a reminder issue if one doesn't already exist."""

    # Check if there's already an open reminder issue
    issues = repo.get_issues(state='open', labels=['commit-reminder'])

    if issues.totalCount > 0:
        print("Reminder issue already exists, skipping...")
        return

    # Create the issue
    title = f"🔔 Daily Commit Reminder - {datetime.now().strftime('%Y-%m-%d')}"

    body = f"""## 📅 Daily Coding Reminder

Hey there! 👋

It's been **{days_since_commit} day(s)** since your last commit.

### 💡 Quick ideas to get back on track:
- Fix a small bug
- Add documentation
- Refactor some code
- Write a test
- Update your README
- Start a new small feature

### 🎯 Remember:
- Consistency beats perfection
- Even small commits count
- Progress is progress!

---
*This issue was automatically created by your Daily Commit Reminder action.*
*Close this issue after you make your next commit!*
"""

    issue = repo.create_issue(
        title=title,
        body=body,
        labels=['commit-reminder', 'automation']
    )

    print(f"Created reminder issue: {issue.html_url}")

def main():
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    repo_owner = os.environ.get('REPO_OWNER')
    repo_name = os.environ.get('REPO_NAME')

    if not all([github_token, repo_owner, repo_name]):
        print("Error: Missing required environment variables")
        sys.exit(1)

    # Initialize GitHub client
    g = Github(github_token)
    repo = g.get_repo(f"{repo_owner}/{repo_name}")

    # Get last commit date
    last_commit_date = get_last_commit_date()

    if last_commit_date:
        print(f"Last commit: {last_commit_date}")

    # Check if we should create a reminder
    if should_create_reminder(last_commit_date):
        now = datetime.utcnow()
        days_since = (now - last_commit_date).days if last_commit_date else "many"

        print("Creating reminder issue...")
        create_reminder_issue(repo, days_since)
    else:
        print("Recent commit found, no reminder needed!")

        # Close any existing reminder issues since we have a recent commit
        issues = repo.get_issues(state='open', labels=['commit-reminder'])
        for issue in issues:
            issue.edit(state='closed')
            issue.create_comment("🎉 Great job! You've made a recent commit. Keep up the good work!")
            print(f"Closed reminder issue: {issue.html_url}")

if __name__ == "__main__":
    main()
