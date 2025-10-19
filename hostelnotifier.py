#!/usr/bin/env python3
"""
hostel_notifier_email_debug.py
Checks a webpage for changes or a keyword.
Sends an email through Gmail when a change or keyword is detected.
Includes debug output for troubleshooting.
"""

import time
import hashlib
import json
import os
import sys
import smtplib
from email.mime.text import MIMEText
from typing import Optional

try:
    import requests
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except Exception:
    print("Install dependencies: pip install requests selenium")
    print("Also install ChromeDriver: https://chromedriver.chromium.org/")
    sys.exit(1)

CONFIG_PATH = "config.json"

def load_config(path: str) -> dict:
    print(f"[DEBUG] Loading configuration from {path} ...")
    if not os.path.exists(path):
        print(f"[ERROR] Config file {path} not found!")
        sys.exit(1)
    with open(path, "r") as f:
        cfg = json.load(f)
    print(f"[DEBUG] Config loaded successfully: {cfg}")
    return cfg

def fetch_url_with_js(url: str, timeout: int) -> str:
    """Fetch URL content with JavaScript rendering using Selenium"""
    print(f"[DEBUG] Fetching URL with JavaScript rendering: {url}")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(timeout)
        
        print(f"[DEBUG] Loading page...")
        driver.get(url)
        
        # Wait for content to load (wait for body to have some content)
        print(f"[DEBUG] Waiting for JavaScript content to load...")
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_element(By.TAG_NAME, "body").text.strip()) > 100
        )
        
        # Get the full rendered page text
        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"[DEBUG] Rendered page content length: {len(page_text)} characters")
        
        driver.quit()
        return page_text
        
    except Exception as e:
        print(f"[DEBUG] Selenium error: {e}")
        if 'driver' in locals():
            driver.quit()
        raise

def fetch_url(url: str, timeout: int, ua: str) -> Optional[bytes]:
    print(f"[DEBUG] Fetching URL: {url}")
    headers = {"User-Agent": ua}
    resp = requests.get(url, headers=headers, timeout=timeout)
    print(f"[DEBUG] HTTP status: {resp.status_code}")
    resp.raise_for_status()
    return resp.content



def compute_hash(content: bytes) -> str:
    h = hashlib.sha256(content).hexdigest()
    print(f"[DEBUG] Computed hash: {h}")
    return h

def load_state(path: str) -> dict:
    print(f"[DEBUG] Loading state from {path} ...")
    if not os.path.exists(path):
        print("[DEBUG] No previous state found.")
        return {}
    with open(path, "r") as f:
        state = json.load(f)
    print(f"[DEBUG] Loaded state: {state}")
    return state

def save_state(path: str, state: dict):
    print(f"[DEBUG] Saving state: {state}")
    with open(path, "w") as f:
        json.dump(state, f, indent=2)

def send_email(cfg: dict, subject: str, body: str) -> bool:
    print("[DEBUG] Preparing to send email...")
    try:
        smtp_cfg = cfg["smtp"]
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_cfg["from_addr"]
        msg["To"] = smtp_cfg["to_addr"]

        print(f"[DEBUG] Connecting to SMTP server {smtp_cfg['smtp_host']}:{smtp_cfg['smtp_port']}")
        try:
            # Try TLS first
            server = smtplib.SMTP(smtp_cfg["smtp_host"], smtp_cfg["smtp_port"], timeout=20)
            server.set_debuglevel(1)
            server.starttls()
        except Exception as e:
            print("[DEBUG] TLS failed, retrying with SSL...", e)
            # Try SSL fallback
            server = smtplib.SMTP_SSL(smtp_cfg["smtp_host"], 465, timeout=20)
            server.set_debuglevel(1)

        print("[DEBUG] Logging in...")
        server.login(smtp_cfg["username"], smtp_cfg["password"])
        print("[DEBUG] Sending email message...")
        server.send_message(msg)
        server.quit()
        print("[DEBUG] Email sent successfully.")
        return True
    except Exception as e:
        print("[DEBUG] Email send error:", e)
        return False

def build_message(url: str, reason: str, sample: str = "") -> str:
    lines = [f"Hostel site update", f"URL: {url}", f"Reason: {reason}"]
    if sample:
        lines.append(f"Sample: {sample}")
    return "\n".join(lines)

def main():
    print("[DEBUG] Starting hostel notifier...")
    cfg = load_config(CONFIG_PATH)
    url = cfg.get("url")
    interval = int(cfg.get("check_interval_seconds", 300))
    use_keyword = bool(cfg.get("use_keyword", False))
    keyword = cfg.get("keyword", "").lower()
    timeout = int(cfg.get("timeout_seconds", 15))
    ua = cfg.get("user_agent", "hostel-notifier/1.0")
    state_file = cfg.get("state_file", "last_state.json")

    state = load_state(state_file)
    last_hash = state.get("last_hash")
    last_keyword_found = state.get("last_keyword_found", False)

    # Check if this is a single run (for GitHub Actions) or continuous monitoring
    single_run = cfg.get("single_run", False)
    
    print("Monitoring:", url)
    if single_run:
        print("Running single check (GitHub Actions mode)")
    else:
        print("Interval:", interval, "seconds")

    run_once = True
    while run_once or not single_run:
        print("[DEBUG] Starting new check cycle...")
        try:
            # Try to get JavaScript-rendered content first
            try:
                text_content = fetch_url_with_js(url, timeout)
                text_lower = text_content.lower()
                content = text_content.encode('utf-8')
                page_hash = compute_hash(content)
                print(f"[DEBUG] Using JavaScript-rendered content")
            except Exception as js_error:
                print(f"[DEBUG] JavaScript rendering failed: {js_error}")
                print(f"[DEBUG] Falling back to regular HTTP request")
                content = fetch_url(url, timeout, ua)
                page_hash = compute_hash(content)
                text_lower = content.decode("utf-8", "ignore").lower()

            # Check for content changes first
            content_changed = False
            keyword_found = False
            reasons = []
            samples = []
            
            print(f"[DEBUG] Page content length: {len(text_lower)} characters")
            print(f"[DEBUG] Current page hash: {page_hash}")
            
            # 1. Check for content changes (always check this)
            if last_hash is None:
                print("[DEBUG] No previous hash. Saving initial snapshot.")
                last_hash = page_hash
                state["last_hash"] = last_hash
                save_state(state_file, state)
                print("Initial snapshot saved. No notifications sent on first run.")
            elif page_hash != last_hash:
                print("[DEBUG] *** CONTENT CHANGE DETECTED ***")
                content_changed = True
                reasons.append("Page content changed")
                samples.append(f"Content preview: {text_lower[:200].strip()}")
                last_hash = page_hash
            else:
                print("[DEBUG] No content changes detected.")
            
            # 2. Check for keyword (if enabled)
            if use_keyword:
                print(f"[DEBUG] Searching entire page content for keyword: {keyword}")
                
                # Try multiple search variations
                found = False
                keyword_used = ""
                search_variations = [
                    keyword,
                    keyword.upper(),
                    keyword.capitalize(),
                    f" {keyword} ",
                    f">{keyword}<",
                    f'"{keyword}"',
                    f"'{keyword}'"
                ]
                
                for variation in search_variations:
                    if variation.lower() in text_lower:
                        found = True
                        keyword_used = variation
                        print(f"[DEBUG] *** KEYWORD FOUND *** - variation: '{variation}'")
                        break
                
                if found:
                    keyword_found = True
                    current_keyword_state = True
                    reasons.append(f"Keyword '{keyword}' found on page")
                    idx = text_lower.find(keyword_used.lower())
                    start = max(0, idx - 60)
                    keyword_sample = text_lower[start:start + 200].strip()
                    samples.append(f"Keyword context: {keyword_sample}")
                    print("[DEBUG] *** KEYWORD FOUND - WILL NOTIFY ***")
                else:
                    current_keyword_state = False
                    print(f"[DEBUG] Keyword '{keyword}' not found on page - no notification")
                    # Don't trigger notification when keyword is not found
                
                last_keyword_found = current_keyword_state
            
            # Determine if we should send notification
            changed = content_changed or keyword_found
            
            if changed:
                reason = " | ".join(reasons)
                sample = "\n\n".join(samples)
                print(f"[DEBUG] *** NOTIFICATION TRIGGERED *** Reasons: {reason}")
            else:
                print("[DEBUG] No changes detected - no notification needed.")

            if changed:
                print(f"[DEBUG] Change detected. Reason: {reason}")
                body = build_message(url, reason, sample)
                subject = "Hostel site update detected"
                sent = send_email(cfg, subject, body)
                if sent:
                    print("Email notification sent.")
                else:
                    print("Change detected. Email failed.")
                state["last_hash"] = last_hash
                state["last_keyword_found"] = last_keyword_found
                save_state(state_file, state)

        except requests.RequestException as e:
            print("[DEBUG] Network error:", e)
        except Exception as e:
            print("[DEBUG] General error:", e)

        if single_run:
            print("[DEBUG] Single run completed. Exiting.")
            break
        else:
            print(f"[DEBUG] Sleeping for {interval} seconds...\n")
            time.sleep(interval)
        
        run_once = False

if __name__ == "__main__":
    main()