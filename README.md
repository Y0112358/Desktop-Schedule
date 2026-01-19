# AI Smart Desktop Assistant (Python Edition)

A minimalist Windows system tray application for managing tasks with AI-powered summaries and categorization.

## Features
- **Minimalist GUI**: Built with PyQt6, featuring a clean white interface.
- **AI Integration**: Uses Google Gemini API for daily task summaries and automatic category tagging.
- **Smart Reminders**: Recurring schedules (Mon-Sun) and precise timing via APScheduler.
- **System Tray**: Minimizes to tray; runs in background.
- **Notifications**: Native Windows toast notifications.

## Setup

1. **Install Python 3.10+**
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set API Key**:
   Set your Gemini API key as an environment variable:
   - Powershell: `$env:GEMINI_API_KEY="your_key_here"`
   - CMD: `set GEMINI_API_KEY=your_key_here`
   
4. **Run**:
   ```bash
   python main.py
   ```

## Usage
- Click 'X' to minimize to the system tray.
- Right-click the tray icon to access "AI Daily Summary" or exit.
- Tasks are saved locally in `reminders.db`.
