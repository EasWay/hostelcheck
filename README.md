# 🏠 Hostel Availability Notifier

Automated monitoring for hostel availability using GitHub Actions. Runs 3 times daily and sends email notifications when the keyword "available" is found or when content changes.

## 🚀 Setup Instructions

### 1. Create GitHub Repository
1. Create a new repository on GitHub
2. Upload these files:
   - `hostelnotifier.py`
   - `config.json` 
   - `.github/workflows/check_site.yml`
   - `README.md`

### 2. Configure Email Secrets
Go to your repository → Settings → Secrets and variables → Actions

Add these secrets:
- `EMAIL_USERNAME`: Your Gmail address (e.g., `your-email@gmail.com`)
- `EMAIL_PASSWORD`: Your Gmail App Password (not regular password!)

### 3. Generate Gmail App Password
1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Security → 2-Step Verification (must be enabled)
3. App passwords → Generate new password
4. Use this password as `EMAIL_PASSWORD` secret

### 4. Enable GitHub Actions
1. Go to repository → Actions tab
2. Enable workflows if prompted
3. The workflow will run automatically 3x daily

## 📅 Schedule
- **6:00 AM UTC** (Morning check)
- **12:00 PM UTC** (Afternoon check)  
- **6:00 PM UTC** (Evening check)

## 🔧 Manual Testing
- Go to Actions tab → "Hostel Availability Checker" → "Run workflow"

## 📧 Notifications
You'll receive email notifications when:
- ✅ Keyword "available" is found on the page
- ✅ Any content changes are detected
- ❌ No notifications when keyword is absent

## 🛠️ Features
- **JavaScript Rendering**: Uses Selenium to see actual content
- **Smart Detection**: Multiple keyword variations
- **Content Monitoring**: Detects any page changes
- **Free Hosting**: Runs on GitHub's servers
- **No Maintenance**: Fully automated

## 📁 Files
- `hostelnotifier.py` - Main monitoring script
- `config.json` - Configuration settings
- `.github/workflows/check_site.yml` - GitHub Actions workflow
- `last_state.json` - State tracking (auto-generated)

## 🔍 Monitoring URL
Currently monitoring: `https://accommodationhub.uenr.edu.gh/`

## 💡 Cost
**Completely FREE** - Uses GitHub Actions free tier (2000 minutes/month)