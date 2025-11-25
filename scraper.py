#RUN THIS SHIT BY USING python scraper.py

import requests
import time
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
import re

# GitHub repositories to monitor
REPOSITORIES = [
    "speedyapply/2026-SWE-College-Jobs",
    "SimplifyJobs/Summer2026-Internships",
]

# File to store seen links
SEEN_LINKS_FILE = "seen_links.json"

# Check interval (in seconds) - 5 minutes
CHECK_INTERVAL = 180

# IMPORTANT!!!!!!!!!!!!!!!!!!!!! discord webhook. if this get deprecated this app doesnt work
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

class InternshipMonitor:
    def __init__(self):
        self.seen_links = self.load_seen_links()
        
    def load_seen_links(self):
        """Load previously seen links from file"""
        if os.path.exists(SEEN_LINKS_FILE):
            with open(SEEN_LINKS_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_seen_links(self):
        """Save seen links to file"""
        with open(SEEN_LINKS_FILE, 'w') as f:
            json.dump(list(self.seen_links), f, indent=2)
    
    def send_notification(self, title, message, url=None):
        if DISCORD_WEBHOOK_URL == "YOUR_WEBHOOK_URL_HERE":
            print(f"\n🔔 NOTIFICATION: {title}")
            print(f"   {message}")
            if url:
                print(f"   URL: {url}")
            return
        
        # Create Discord embed for a prettier notification
        embed = {
            "title": title,
            "description": f"{message}\n\n{url}",
            "color": 5814783,  # Blue color
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Internship Monitor"
            }
        }
        
        data = {
            "username": "Internship Monitor 🎓",
            "embeds": [embed]
        }
        
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=data)
            if response.status_code in [200, 204]:
                print(f"✅ Discord notification sent: {title}")
            else:
                print(f"❌ Failed to send Discord notification: {response.text}")
        except Exception as e:
            print(f"❌ Error sending Discord notification: {e}")
    
    def extract_links_SpeedyApply(self, content):
        """Extract application links from SpeedyApply FAANG+ and Quant tables only"""
        links = set()
        
        # Find the FAANG+ section
        faang_start = content.find('<!-- TABLE_FAANG_START -->')
        faang_end = content.find('<!-- TABLE_FAANG_END -->')
        
        # Find the Quant section
        quant_start = content.find('<!-- TABLE_QUANT_START -->')
        quant_end = content.find('<!-- TABLE_QUANT_END -->')
        
        # Extract content from both sections
        sections_to_parse = []
        
        if faang_start != -1 and faang_end != -1:
            faang_section = content[faang_start:faang_end]
            sections_to_parse.append(faang_section)
            print("  ✓ Found FAANG+ section")
        
        if quant_start != -1 and quant_end != -1:
            quant_section = content[quant_start:quant_end]
            sections_to_parse.append(quant_section)
            print("  ✓ Found Quant section")
        
        # Parse each section for links
        for section in sections_to_parse:
            # SpeedyApply uses HTML format, not markdown!
            # Look for <a href="url"> instead of [text](url)
            html_links = re.findall(r'<a href="([^"]+)"', section)
            
            for url in html_links:
                # Only include actual application URLs
                # Exclude images and company homepage links
                if (url.startswith('http') and 
                    not any(x in url.lower() for x in 
                        ['imgur.com', '.png', '.jpg', '.gif', 'i.imgur.com'])):
                
                        links.add(url)
                        print(f"  ✓ Added: {url}")
        
        return links

    def extract_links_SimplifyJobs(self, content):
        links = set()
        
        # Split content into lines
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Check if this line contains the fire emoji
            if '🔥' in line:
                # Look for the next few lines that might contain the application link
                # Usually the link appears within 1-3 lines after the fire emoji
                for j in range(i, min(i + 5, len(lines))):
                    search_line = lines[j]
                    
                    # SimplifyJobs uses HTML format, not markdown!
                    # Look for <a href="url"> instead of [text](url)
                    html_links = re.findall(r'<a href="([^"]+)"', search_line)
                    
                    for url in html_links:
                        # Clean the URL by removing Simplify tracking parameters
                        if '?utm_source=Simplify' in url:
                            clean_url = url.split('?utm_source=Simplify')[0]
                        elif '&utm_source=Simplify' in url:
                            clean_url = url.split('&utm_source=Simplify')[0]
                        else:
                            clean_url = url
                        
                        # Only include actual application URLs (not GitHub, images, or Simplify internal links)
                        if (clean_url.startswith('http') and 
                            not any(x in clean_url.lower() for x in 
                                ['github.com', 'imgur.com', '.png', '.jpg', '.gif', 
                                'simplify.jobs/c/', 'simplify.jobs/p/', 'i.imgur.com'])):
                            links.add(clean_url)
                            print(f"  ✓ Added: {clean_url}")
        
        return links


    def extract_links_from_markdown(self, content):
        """Extract application links from markdown table"""
        links = set()
        
        # Match markdown links [text](url)
        markdown_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
        
        for text, url in markdown_links:
            # Filter for actual application links (exclude GitHub, images, etc.)
            if url.startswith('http') and not any(x in url.lower() for x in 
                ['github.com', 'imgur.com', '.png', '.jpg', '.gif', 'discord']):
                links.add(url)
        
        return links
    
    def fetch_repository_links(self, repo):
        """Fetch README content from a GitHub repository"""
        try:
            # Use GitHub API to get README
            api_url = f"https://api.github.com/repos/{repo}/readme"
            headers = {"Accept": "application/vnd.github.v3.raw"}
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                links = set()
                if("SimplifyJobs" in repo): links = self.extract_links_SimplifyJobs(content)
                elif("speedyapply" in repo): links = self.extract_links_SpeedyApply(content)
                else: links = self.extract_links_from_markdown(content)

                print(f"  ✓ Found {len(links)} links in {repo}")
                return links
            else:
                print(f"  ⚠ Failed to fetch {repo}: Status {response.status_code}")
                return set()
                
        except Exception as e:
            print(f"  ❌ Error fetching {repo}: {e}")
            return set()
    
    def check_for_new_postings(self):
        """Check all repositories for new internship postings"""
        print(f"\n{'='*60}")
        print(f"🔍 Checking repositories at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        all_current_links = set()
        new_links = []
        
        for repo in REPOSITORIES:
            print(f"\n📂 Checking {repo}...")
            links = self.fetch_repository_links(repo)
            all_current_links.update(links)
            
            # Find new links
            repo_new_links = links - self.seen_links
            if repo_new_links:
                for link in repo_new_links:
                    new_links.append((repo, link))
        
        # Send notifications for new links
        if new_links:
            print(f"\n🎉 Found {len(new_links)} new internship posting(s)!")
            for repo, link in new_links:
                repo_name = repo.split('/')[-1]
                self.send_notification(
                    title=f"New Internship: {repo_name}",
                    message=f"New posting found in {repo}",
                    url=link
                )
                self.seen_links.add(link)
            
            # Save updated seen links
            self.save_seen_links()
        else:
            print(f"\n✅ No new postings found. Monitoring {len(all_current_links)} total links.")
        
        return len(new_links)
    
    def run(self):
        """Main loop - runs forever"""
        print("🚀 Internship Monitor Started!")
        print(f"📱 Notifications: {'Discord' if DISCORD_WEBHOOK_URL != 'YOUR_WEBHOOK_URL_HERE' else 'Console only (set up Discord webhook for notifications)'}")
        print(f"⏰ Check interval: {CHECK_INTERVAL // 60} minutes")
        print(f"📊 Currently tracking {len(self.seen_links)} seen links")
        
        iteration = 0

        new_count = self.check_for_new_postings()
        
        """
        while True:
            try:
                iteration += 1
                new_count = self.check_for_new_postings()
                
                next_check = datetime.now().timestamp() + CHECK_INTERVAL
                next_check_time = datetime.fromtimestamp(next_check).strftime('%H:%M:%S')
                
                print(f"\n💤 Sleeping until {next_check_time} (Iteration #{iteration} complete)")
                print(f"{'='*60}\n")
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n\n⏹️  Monitor stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                print("⏳ Waiting 60 seconds before retry...")
                time.sleep(60)

        """

if __name__ == "__main__":
    
    time.sleep(3)
    
    monitor = InternshipMonitor()
    monitor.run()
