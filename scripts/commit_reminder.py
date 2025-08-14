"""
GitHub Daily Activity Email Reporter
Sends daily email reports with GitHub activities and motivational quotes.
Enhanced with Nepali timezone and cultural context.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from github import Github
import sys
import pytz
import random

# Nepali timezone
NEPAL_TZ = pytz.timezone('Asia/Kathmandu')

# Nepali holidays
NEPALI_HOLIDAYS = {
    (1, 1): "New Year's Day",
    (1, 15): "Maghe Sankranti",
    (2, 19): "Democracy Day", 
    (3, 8): "International Women's Day",
    (4, 14): "Nepali New Year",
    (5, 1): "Labour Day",
    (5, 29): "Republic Day",
    (8, 20): "Constitution Day",
    (10, 1): "Dashain Start",
    (10, 10): "Dashain End",
    (10, 25): "Tihar Start",
    (11, 2): "Tihar End",
    (12, 25): "Christmas",
}

# Motivational quotes for developers
MOTIVATIONAL_QUOTES = [
    "Code is like humor. When you have to explain it, it's bad. - Cory House",
    "First, solve the problem. Then, write the code. - John Johnson",
    "Experience is the name everyone gives to their mistakes. - Oscar Wilde",
    "In order to be irreplaceable, one must always be different. - Coco Chanel",
    "Java is to JavaScript what car is to Carpet. - Chris Heilmann",
    "Knowledge is power. - Francis Bacon",
    "Sometimes it pays to stay in bed on Monday, rather than spending the rest of the week debugging Monday's code. - Dan Salomon",
    "Perfection is achieved not when there is nothing more to add, but rather when there is nothing more to take away. - Antoine de Saint-Exupery",
    "Ruby is rubbish! PHP is phpantastic! - Nikita Popov",
    "Code never lies, comments sometimes do. - Ron Jeffries",
    "Simplicity is the ultimate sophistication. - Leonardo da Vinci",
    "Make it work, make it right, make it fast. - Kent Beck",
    "Clean code always looks like it was written by someone who cares. - Robert C. Martin",
    "Any fool can write code that a computer can understand. Good programmers write code that humans can understand. - Martin Fowler",
    "Programming isn't about what you know; it's about what you can figure out. - Chris Pine",
    "The best error message is the one that never shows up. - Thomas Fuchs",
    "A ship in harbor is safe, but that is not what ships are built for. - John A. Shedd",
    "Progress, not perfection. - Anonymous",
    "Every expert was once a beginner. - Helen Hayes",
    "The journey of a thousand miles begins with one step. - Lao Tzu"
]

# Automated commit patterns to exclude
AUTOMATED_COMMIT_PATTERNS = [
    'automated', 'auto-commit', 'bot commit', 'github-actions',
    'dependabot', 'renovate', 'merge pull request', 'bump version',
    'update dependencies', 'auto-generated', 'ci:', '[bot]', 'workflow:'
]

def is_automated_commit(commit_message):
    """Check if a commit message indicates an automated commit."""
    message_lower = commit_message.lower().strip()
    return any(pattern.lower() in message_lower for pattern in AUTOMATED_COMMIT_PATTERNS)

def is_nepali_holiday(date):
    """Check if the given date is a Nepali holiday."""
    nepal_date = date.astimezone(NEPAL_TZ)
    holiday_key = (nepal_date.month, nepal_date.day)
    return holiday_key in NEPALI_HOLIDAYS, NEPALI_HOLIDAYS.get(holiday_key)

def is_weekend_in_nepal(date):
    """Check if the given date is a weekend in Nepal (Saturday)."""
    nepal_date = date.astimezone(NEPAL_TZ)
    return nepal_date.weekday() == 5

def get_user_activity_yesterday(github_client, username):
    """Get comprehensive user activity from yesterday."""
    # Calculate yesterday in Nepal time
    now_nepal = datetime.now(NEPAL_TZ)
    yesterday_start = (now_nepal - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start.replace(hour=23, minute=59, second=59)
    
    # Convert to UTC for GitHub API
    yesterday_start_utc = yesterday_start.astimezone(pytz.UTC)
    yesterday_end_utc = yesterday_end.astimezone(pytz.UTC)
    
    print(f"Checking activity for: {yesterday_start.strftime('%Y-%m-%d')} (Nepal time)")
    
    activity_summary = {
        'date': yesterday_start.strftime('%Y-%m-%d'),
        'commits': {},
        'pull_requests': [],
        'issues': [],
        'reviews': [],
        'total_commits': 0,
        'total_prs': 0,
        'total_issues': 0,
        'total_reviews': 0,
        'repositories_touched': set()
    }
    
    try:
        user = github_client.get_user(username)
        
        # Get user's repositories
        repos = user.get_repos(type='all', sort='updated')
        
        for repo in repos:
            try:
                # Skip if user is not owner or collaborator
                if not (repo.owner.login == username or repo.get_collaborator_permission(username) in ['admin', 'write']):
                    continue
                
                repo_commits = []
                
                # Get commits from yesterday
                commits = repo.get_commits(
                    author=username,
                    since=yesterday_start_utc,
                    until=yesterday_end_utc
                )
                
                for commit in commits:
                    commit_message = commit.commit.message.split('\n')[0]  # First line only
                    
                    # Skip automated commits
                    if is_automated_commit(commit_message):
                        continue
                    
                    repo_commits.append({
                        'message': commit_message,
                        'sha': commit.sha[:8],
                        'url': commit.html_url
                    })
                    activity_summary['total_commits'] += 1
                    activity_summary['repositories_touched'].add(repo.name)
                
                if repo_commits:
                    activity_summary['commits'][repo.name] = repo_commits
                
            except Exception as e:
                print(f"Error processing repo {repo.name}: {e}")
                continue
        
        # Get pull requests created yesterday
        search_query = f"author:{username} type:pr created:{yesterday_start.strftime('%Y-%m-%d')}"
        prs = github_client.search_issues(query=search_query)
        
        for pr in prs:
            activity_summary['pull_requests'].append({
                'title': pr.title,
                'repo': pr.repository.name,
                'url': pr.html_url,
                'state': pr.state
            })
            activity_summary['total_prs'] += 1
            activity_summary['repositories_touched'].add(pr.repository.name)
        
        # Get issues created yesterday
        search_query = f"author:{username} type:issue created:{yesterday_start.strftime('%Y-%m-%d')}"
        issues = github_client.search_issues(query=search_query)
        
        for issue in issues:
            activity_summary['issues'].append({
                'title': issue.title,
                'repo': issue.repository.name,
                'url': issue.html_url,
                'state': issue.state
            })
            activity_summary['total_issues'] += 1
            activity_summary['repositories_touched'].add(issue.repository.name)
        
    except Exception as e:
        print(f"Error getting user activity: {e}")
    
    activity_summary['repositories_touched'] = len(activity_summary['repositories_touched'])
    return activity_summary

def generate_html_email(activity_summary, user_email):
    """Generate HTML email content based on activity."""
    now_nepal = datetime.now(NEPAL_TZ)
    nepal_time = now_nepal.strftime('%Y-%m-%d %H:%M %Z')
    
    has_activity = (activity_summary['total_commits'] > 0 or 
                   activity_summary['total_prs'] > 0 or 
                   activity_summary['total_issues'] > 0)
    
    if has_activity:
        subject = f"🎉 Your GitHub Activity Summary - {activity_summary['date']}"
        
        # Build commits section
        commits_html = ""
        for repo_name, commits in activity_summary['commits'].items():
            commits_html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 8px;">
                <h3 style="color: #0366d6; margin: 0 0 10px 0;">📂 {repo_name}</h3>
                <ul style="margin: 0; padding-left: 20px;">
            """
            for commit in commits:
                commits_html += f"""
                    <li style="margin-bottom: 8px;">
                        <strong>{commit['sha']}</strong>: {commit['message']}
                        <br><a href="{commit['url']}" style="color: #0366d6; font-size: 12px;">View commit</a>
                    </li>
                """
            commits_html += "</ul></div>"
        
        # Build PRs section
        prs_html = ""
        if activity_summary['pull_requests']:
            prs_html = """<h2 style="color: #28a745;">📋 Pull Requests</h2>"""
            for pr in activity_summary['pull_requests']:
                prs_html += f"""
                <div style="margin-bottom: 10px; padding: 10px; background-color: #f0f8e8; border-radius: 5px;">
                    <strong>{pr['repo']}</strong>: {pr['title']} 
                    <span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{pr['state']}</span>
                    <br><a href="{pr['url']}" style="color: #28a745;">View PR</a>
                </div>
                """
        
        # Build issues section
        issues_html = ""
        if activity_summary['issues']:
            issues_html = """<h2 style="color: #d73a49;">🐛 Issues</h2>"""
            for issue in activity_summary['issues']:
                issues_html += f"""
                <div style="margin-bottom: 10px; padding: 10px; background-color: #ffeef0; border-radius: 5px;">
                    <strong>{issue['repo']}</strong>: {issue['title']}
                    <span style="background-color: #d73a49; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{issue['state']}</span>
                    <br><a href="{issue['url']}" style="color: #d73a49;">View Issue</a>
                </div>
                """
        
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px;">
                    <h1 style="margin: 0;">🚀 Daily GitHub Report</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Namaste! Here's your activity from {activity_summary['date']}</p>
                </div>
                
                <div style="background-color: #e8f5e8; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    <h2 style="color: #28a745; margin-top: 0;">📊 Quick Stats</h2>
                    <div style="display: flex; justify-content: space-around; text-align: center;">
                        <div>
                            <div style="font-size: 24px; font-weight: bold; color: #0366d6;">{activity_summary['total_commits']}</div>
                            <div style="font-size: 14px;">Commits</div>
                        </div>
                        <div>
                            <div style="font-size: 24px; font-weight: bold; color: #28a745;">{activity_summary['total_prs']}</div>
                            <div style="font-size: 14px;">Pull Requests</div>
                        </div>
                        <div>
                            <div style="font-size: 24px; font-weight: bold; color: #d73a49;">{activity_summary['total_issues']}</div>
                            <div style="font-size: 14px;">Issues</div>
                        </div>
                        <div>
                            <div style="font-size: 24px; font-weight: bold; color: #6f42c1;">{activity_summary['repositories_touched']}</div>
                            <div style="font-size: 14px;">Repositories</div>
                        </div>
                    </div>
                </div>
                
                {f'<h2 style="color: #0366d6;">💻 Commits</h2>{commits_html}' if activity_summary['commits'] else ''}
                {prs_html}
                {issues_html}
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin-top: 20px;">
                    <p style="margin: 0; color: #856404;"><strong>🇳🇵 Nepal Time:</strong> {nepal_time}</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666;">
                    <p>Keep up the great work! 🎉</p>
                    <small>Generated by your Daily GitHub Activity Reporter</small>
                </div>
            </div>
        </body>
        </html>
        """
    else:
        # No activity - send motivational email
        quote = random.choice(MOTIVATIONAL_QUOTES)
        subject = f"💪 Daily Motivation - {activity_summary['date']}"
        
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; background: linear-gradient(135deg, #ff7b7b 0%, #667eea 100%); color: white; padding: 40px; border-radius: 15px; margin-bottom: 30px;">
                    <h1 style="margin: 0; font-size: 28px;">🌟 Daily Inspiration</h1>
                    <p style="margin: 15px 0 0 0; opacity: 0.9;">Namaste! Let's make today count 🙏</p>
                </div>
                
                <div style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 30px;">
                    <h2 style="color: #d63384; margin: 0 0 20px 0;">💡 Quote of the Day</h2>
                    <blockquote style="font-size: 18px; font-style: italic; color: #6c5ce7; margin: 0; padding: 0; border: none; line-height: 1.8;">
                        "{quote}"
                    </blockquote>
                </div>
                
                <div style="background-color: #e8f4fd; padding: 25px; border-radius: 10px; margin-bottom: 20px;">
                    <h2 style="color: #0984e3; margin-top: 0;">🚀 No Activity Yesterday?</h2>
                    <p>That's okay! Every developer has quiet days. Here are some ideas to get your creative juices flowing:</p>
                    
                    <div style="display: grid; gap: 15px;">
                        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #00b894;">
                            <strong>🐛 Quick Wins:</strong> Fix a small bug, update documentation, or clean up some code
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #fdcb6e;">
                            <strong>🧪 Experiment:</strong> Try a new library, write a small script, or refactor an old function
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #e17055;">
                            <strong>📚 Learn:</strong> Read about best practices, watch a tutorial, or explore new technologies
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #a29bfe;">
                            <strong>🤝 Contribute:</strong> Help with open source, review someone's code, or start a new project
                        </div>
                    </div>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <p style="margin: 0; color: #856404;"><strong>🇳🇵 Nepal Time:</strong> {nepal_time}</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="color: #00b894; font-weight: bold; font-size: 18px;">You've got this! 💪</p>
                    <p style="color: #666; margin: 0;">Remember: Progress over perfection, consistency over intensity!</p>
                    <small style="color: #999;">Generated with love by your Daily GitHub Activity Reporter</small>
                </div>
            </div>
        </body>
        </html>
        """
    
    return subject, html_content

def send_email(user_email, subject, html_content):
    """Send HTML email using Gmail SMTP."""
    
    # Email configuration from environment variables
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_APP_PASSWORD')  # Gmail App Password
    
    if not all([sender_email, sender_password]):
        print("Error: Missing email configuration (SENDER_EMAIL, SENDER_APP_PASSWORD)")
        return False
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = user_email
        
        # Add HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        print(f"✅ Email sent successfully to {user_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def main():
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    github_username = os.environ.get('GITHUB_USERNAME')
    user_email = os.environ.get('USER_EMAIL')
    
    if not all([github_token, github_username, user_email]):
        print("Error: Missing required environment variables (GITHUB_TOKEN, GITHUB_USERNAME, USER_EMAIL)")
        sys.exit(1)
    
    # Check if today is a holiday or weekend
    now_nepal = datetime.now(NEPAL_TZ)
    is_holiday, holiday_name = is_nepali_holiday(now_nepal)
    is_weekend = is_weekend_in_nepal(now_nepal)
    
    if is_weekend and not os.environ.get('FORCE_SEND'):
        print("Today is Saturday (weekend in Nepal), skipping email...")
        return
    
    if is_holiday and not os.environ.get('FORCE_SEND'):
        print(f"Today is {holiday_name} (Nepali holiday), skipping email...")
        return
    
    # Initialize GitHub client
    github_client = Github(github_token)
    
    print(f"📧 Generating daily report for {github_username}...")
    print(f"🇳🇵 Nepal time: {now_nepal.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Get user activity from yesterday
    activity_summary = get_user_activity_yesterday(github_client, github_username)
    
    # Generate email content
    subject, html_content = generate_html_email(activity_summary, user_email)
    
    # Send email
    success = send_email(user_email, subject, html_content)
    
    if success:
        print("🎉 Daily report sent successfully!")
    else:
        print("❌ Failed to send daily report")
        sys.exit(1)

if __name__ == "__main__":
    main()