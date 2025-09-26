# FruitsSearchAutomata
🍎 #Fruit #Search #Bot 🚀

A web-based automation tool that opens your favorite browser, switches Chrome profiles if needed, and searches for a list of fruits (or any items you provide).

Built with:

Flask (backend API + static file server)

PyAutoGUI (keyboard/mouse automation)

HTML/CSS/JS (frontend, glassmorphic dark theme)

✨ Features

🔍 Automated Searches — Opens new tabs, types fruit names, presses Enter.

🌐 Multi-browser Support — Chrome, Edge, Firefox, Brave, Opera, Safari.

👤 Real Chrome Profile Detection — Detects and uses your actual Chrome profiles by name (Personal, Work, etc.).

📋 Smart Profile Selection — Select specific profiles via the web UI (with Select All & Clear All options).

💾 Fruit List Management — Load default fruits, save your own to fruits.json, reload anytime.

📊 Progress & Status — Live status, current fruit, current profile, progress bar.

🛑 Safety — Move your mouse to the TOP-LEFT corner anytime to immediately abort automation.

💻 CLI Mode — Run automation without the web UI using --cli.

📂 Project Structure
fruit-search-bot/
├── app.py          # Flask backend (API + automation logic)
├── index.html      # Frontend (UI)
├── style.css       # Glassmorphic dark theme
├── script.js       # Frontend logic + API calls
├── fruits.json     # Saved fruit list (auto-created)
├── selected_profiles.json  # Saved Chrome profiles (auto-created)
└── README.md       # Project documentation

⚙️ Installation
1. Clone the repository
git clone https://github.com/your-username/fruit-search-bot.git
cd fruit-search-bot

2. Install dependencies

Python 3.9+ recommended.

pip install Flask Flask-Cors pyautogui


On Linux/macOS you may also need:

sudo apt install xdotool   # (Ubuntu/Debian for automation reliability)

▶️ Running the Web App
python app.py


Then open in your browser:
👉 http://localhost:5000

🌐 Using the Web UI

Open http://localhost:5000
.

Manage your fruit list (add/remove fruits, or load defaults).

Select your browser from the dropdown.

If Chrome:

Enter max profiles (1–10).

Click 📋 Select Profiles and pick from your actual Chrome profiles.

Click ✅ Use Selected Profiles.

Set the delay (seconds between searches).

Click ▶ START SEARCH.

Watch live progress.

Click ⏹ STOP SEARCH anytime or move mouse to TOP-LEFT corner for emergency stop.

🖥️ CLI Mode

You can also run the bot without the UI:

python app.py --cli --file fruits.json --delay 3 --browser chrome --profiles "Personal" "Work"


Options:

--cli → run in CLI mode instead of starting Flask server

--file → JSON file containing ["Apple","Banana",...]

--delay → delay between searches (min 0.5s)

--browser → chrome, edge, firefox, brave, opera, safari

--profiles → Chrome profile names to use

Example:

python app.py --cli --file fruits.json --delay 2 --browser chrome --profiles "Work Account"

⚠️ Safety Notes

Failsafe: Move mouse to TOP-LEFT corner of screen to immediately abort automation.

Only works on machines with a graphical environment (Windows, macOS, Linux with GUI).

On headless servers, PyAutoGUI cannot type into browsers.

✅ Health Check

Backend exposes /api/health:

curl http://localhost:5000/api/health


Example response:

{
  "status": "healthy",
  "platform": "Windows",
  "chrome_dir": "C:\\Users\\Me\\AppData\\Local\\Google\\Chrome\\User Data",
  "pyautogui_available": true,
  "failsafe_enabled": true
}
