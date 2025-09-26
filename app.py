#!/usr/bin/env python3
"""
Fruit Search Bot - Flask Backend
Required packages: pip install Flask Flask-Cors pyautogui

This application provides a web interface for automated browser searching
with support for multiple browsers and Chrome profiles.
"""

import json
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse

# Core imports
try:
    from flask import Flask, jsonify, request, send_from_directory
    from flask_cors import CORS
    import pyautogui
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install Flask Flask-Cors pyautogui")
    sys.exit(1)

# Configure pyautogui safety features
pyautogui.FAILSAFE = True  # Moving mouse to top-left corner stops automation
pyautogui.PAUSE = 0.25  # Delay between pyautogui actions

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for cross-origin requests

# Global thread-safe state management
state_lock = threading.Lock()
state = {
    'is_running': False,
    'status': 'Ready to start...',
    'progress': 0.0,
    'current_search': '',
    'current_profile': '',
    'completed': 0,
    'total': 0
}

# Storage for selected profiles
selected_profiles_memory = []
worker_thread = None


class ChromeProfileManager:
    """Manages Chrome profile discovery and information retrieval"""
    
    def __init__(self):
        self.platform = platform.system()
        self.user_data_dir = self._find_chrome_user_data_dir()
    
    def _find_chrome_user_data_dir(self) -> Optional[Path]:
        """Find Chrome user data directory based on platform"""
        home = Path.home()
        
        if self.platform == 'Windows':
            # Windows: %LOCALAPPDATA%\Google\Chrome\User Data
            local_appdata = os.environ.get('LOCALAPPDATA')
            if local_appdata:
                chrome_dir = Path(local_appdata) / 'Google' / 'Chrome' / 'User Data'
                if chrome_dir.exists():
                    return chrome_dir
        
        elif self.platform == 'Darwin':  # macOS
            # macOS: ~/Library/Application Support/Google/Chrome
            chrome_dir = home / 'Library' / 'Application Support' / 'Google' / 'Chrome'
            if chrome_dir.exists():
                return chrome_dir
        
        elif self.platform == 'Linux':
            # Linux: Try multiple possible locations
            possible_dirs = [
                home / '.config' / 'google-chrome',
                home / '.config' / 'chromium',
                home / '.config' / 'chrome'
            ]
            for chrome_dir in possible_dirs:
                if chrome_dir.exists():
                    return chrome_dir
        
        return None
    
    def get_available_profiles(self) -> List[Dict[str, str]]:
        """
        Get list of available Chrome profiles with friendly names.
        Returns: List of dicts with 'name', 'directory', 'path' keys
        """
        profiles = []
        
        if not self.user_data_dir or not self.user_data_dir.exists():
            print(f"Chrome user data directory not found: {self.user_data_dir}")
            return profiles
        
        # Try to read Local State for profile info
        local_state_file = self.user_data_dir / 'Local State'
        profile_info_cache = {}
        
        if local_state_file.exists():
            try:
                with open(local_state_file, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                    profile_info_cache = local_state.get('profile', {}).get('info_cache', {})
            except (json.JSONDecodeError, KeyError, IOError) as e:
                print(f"Warning: Could not read Local State: {e}")
        
        # Scan for profile directories
        profile_dirs = []
        
        # Always check for Default profile
        default_dir = self.user_data_dir / 'Default'
        if default_dir.exists() and default_dir.is_dir():
            profile_dirs.append('Default')
        
        # Look for Profile 1, Profile 2, etc.
        for item in self.user_data_dir.iterdir():
            if item.is_dir() and item.name.startswith('Profile '):
                profile_dirs.append(item.name)
        
        # Build profile information
        for profile_dir in profile_dirs:
            profile_path = self.user_data_dir / profile_dir
            
            # Try to get friendly name from various sources
            name = None
            
            # 1. Try Local State info_cache
            if profile_dir in profile_info_cache:
                cache_info = profile_info_cache[profile_dir]
                if isinstance(cache_info, dict):
                    name = cache_info.get('name', cache_info.get('gaia_name'))
            
            # 2. Try reading Preferences file
            if not name:
                prefs_file = profile_path / 'Preferences'
                if prefs_file.exists():
                    try:
                        with open(prefs_file, 'r', encoding='utf-8') as f:
                            prefs = json.load(f)
                            profile_info = prefs.get('profile', {})
                            name = profile_info.get('name') or profile_info.get('gaia_name')
                    except (json.JSONDecodeError, IOError):
                        pass
            
            # 3. Fallback to directory name
            if not name:
                name = profile_dir
            
            profiles.append({
                'name': name,
                'directory': profile_dir,
                'path': str(profile_path)
            })
        
        return profiles


def save_to_file(filename: str, data: Any) -> None:
    """Thread-safe file saving"""
    with state_lock:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving to {filename}: {e}")


def load_from_file(filename: str) -> Any:
    """Thread-safe file loading"""
    with state_lock:
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading from {filename}: {e}")
    return None


def launch_browser(browser: str, profile_dir: Optional[str] = None) -> Optional[subprocess.Popen]:
    """
    Launch browser with optional Chrome profile.
    Returns subprocess.Popen object or None if failed.
    """
    system = platform.system()
    
    try:
        if system == 'Windows':
            if browser == 'chrome' and profile_dir:
                # Windows Chrome with profile
                cmd = ['start', 'chrome', f'--profile-directory={profile_dir}']
                return subprocess.Popen(cmd, shell=True)
            else:
                # Other browsers on Windows
                browser_commands = {
                    'chrome': 'start chrome',
                    'edge': 'start msedge',
                    'firefox': 'start firefox',
                    'brave': 'start brave',
                    'opera': 'start opera',
                    'safari': 'echo "Safari not available on Windows"'
                }
                cmd = browser_commands.get(browser, 'start chrome')
                return subprocess.Popen(cmd, shell=True)
        
        elif system == 'Darwin':  # macOS
            if browser == 'chrome' and profile_dir:
                # macOS Chrome with profile
                cmd = ['open', '-a', 'Google Chrome', '--args', f'--profile-directory={profile_dir}']
                return subprocess.Popen(cmd)
            else:
                # Other browsers on macOS
                browser_apps = {
                    'chrome': 'Google Chrome',
                    'edge': 'Microsoft Edge',
                    'firefox': 'Firefox',
                    'brave': 'Brave Browser',
                    'opera': 'Opera',
                    'safari': 'Safari'
                }
                app_name = browser_apps.get(browser, 'Google Chrome')
                cmd = ['open', '-a', app_name]
                return subprocess.Popen(cmd)
        
        elif system == 'Linux':
            if browser == 'chrome' and profile_dir:
                # Try various Chrome executables on Linux
                chrome_cmds = [
                    'google-chrome',
                    'google-chrome-stable',
                    'chromium-browser',
                    'chromium'
                ]
                for chrome_cmd in chrome_cmds:
                    try:
                        cmd = [chrome_cmd, f'--profile-directory={profile_dir}']
                        return subprocess.Popen(cmd)
                    except FileNotFoundError:
                        continue
            else:
                # Other browsers on Linux
                browser_commands = {
                    'chrome': 'google-chrome',
                    'firefox': 'firefox',
                    'brave': 'brave-browser',
                    'opera': 'opera',
                    'edge': 'microsoft-edge'
                }
                cmd = browser_commands.get(browser, 'xdg-open http://google.com')
                return subprocess.Popen(cmd.split())
    
    except Exception as e:
        print(f"Error launching browser: {e}")
    
    return None


def automation_worker(fruits: List[str], delay: float, browser: str, profiles: List[Dict[str, str]]):
    """
    Worker thread that performs the automation using pyautogui.
    Runs searches for each fruit in each selected profile.
    """
    global state
    
    # If no profiles specified (non-Chrome browsers), create a dummy profile
    if not profiles:
        profiles = [{'name': 'Default', 'directory': None, 'path': None}]
    
    total_searches = len(fruits) * len(profiles)
    completed = 0
    
    with state_lock:
        state['total'] = total_searches
        state['completed'] = 0
        state['progress'] = 0.0
    
    try:
        for profile in profiles:
            if not state['is_running']:
                break
            
            profile_name = profile['name']
            profile_dir = profile.get('directory')
            
            # Update current profile
            with state_lock:
                state['current_profile'] = profile_name
                state['status'] = f'Opening browser for profile: {profile_name}'
            
            # Launch browser with profile
            launch_browser(browser, profile_dir)
            
            # Wait for browser to open and become active
            time.sleep(3)
            
            # Perform searches for this profile
            for fruit in fruits:
                if not state['is_running']:
                    break
                
                # Update state
                with state_lock:
                    state['current_search'] = fruit
                    state['status'] = f'Searching for: {fruit}'
                
                # Open new tab
                pyautogui.hotkey('ctrl', 't')
                time.sleep(0.5)
                
                # Focus address bar
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.3)
                
                # Type search term
                pyautogui.typewrite(fruit, interval=0.05)
                time.sleep(0.2)
                
                # Press Enter to search
                pyautogui.press('enter')
                
                # Update progress
                completed += 1
                with state_lock:
                    state['completed'] = completed
                    state['progress'] = (completed / total_searches) * 100
                
                # Wait with random jitter
                sleep_time = max(0.1, delay + random.uniform(0.15, 0.6))
                time.sleep(sleep_time)
    
    except pyautogui.FailSafeException:
        print("Automation stopped: Mouse moved to top-left corner (failsafe triggered)")
    except Exception as e:
        print(f"Automation error: {e}")
    finally:
        # Clean up state
        with state_lock:
            state['is_running'] = False
            state['status'] = 'Automation completed' if completed == total_searches else 'Automation stopped'
            state['current_search'] = ''
            state['current_profile'] = ''


# Flask Routes

@app.route('/')
def index():
    """Serve the main index.html file"""
    return app.send_static_file('index.html')


@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    """Get available Chrome profiles"""
    manager = ChromeProfileManager()
    profiles = manager.get_available_profiles()
    return jsonify({'profiles': profiles})


@app.route('/api/profiles/refresh', methods=['POST'])
def refresh_profiles():
    """Force refresh of Chrome profiles"""
    manager = ChromeProfileManager()
    profiles = manager.get_available_profiles()
    return jsonify({'profiles': profiles})


@app.route('/api/apply-profiles', methods=['POST'])
def apply_profiles():
    """Apply selected Chrome profiles"""
    global selected_profiles_memory
    
    data = request.json
    selected = data.get('selectedProfiles', [])
    
    # Validate selected profiles against available profiles
    manager = ChromeProfileManager()
    available = manager.get_available_profiles()
    available_dirs = {p['directory'] for p in available}
    
    valid_profiles = []
    invalid_profiles = []
    
    for profile in selected:
        if profile.get('directory') in available_dirs:
            valid_profiles.append(profile)
        else:
            invalid_profiles.append(profile.get('name', 'Unknown'))
    
    selected_profiles_memory = valid_profiles
    
    # Persist to file
    save_to_file('selected_profiles.json', valid_profiles)
    
    response = {
        'message': f'Applied {len(valid_profiles)} profiles',
        'selected': valid_profiles
    }
    
    if invalid_profiles:
        response['warning'] = f'Invalid profiles ignored: {", ".join(invalid_profiles)}'
    
    return jsonify(response)


@app.route('/api/selected-profiles', methods=['GET'])
def get_selected_profiles():
    """Get currently selected profiles"""
    return jsonify({'profiles': selected_profiles_memory})


@app.route('/api/save', methods=['POST'])
def save_fruits():
    """Save fruits to file"""
    data = request.json
    fruits = data.get('fruits', [])
    
    save_to_file('fruits.json', fruits)
    
    return jsonify({'message': f'Saved {len(fruits)} fruits'})


@app.route('/api/load', methods=['GET'])
def load_fruits():
    """Load fruits from file"""
    fruits = load_from_file('fruits.json')
    
    if fruits is not None:
        return jsonify({'fruits': fruits})
    else:
        return jsonify({'fruits': []})


@app.route('/api/start', methods=['POST'])
def start_automation():
    """Start the automation process"""
    global state, worker_thread, selected_profiles_memory
    
    # Check if already running
    if state['is_running']:
        return jsonify({'error': 'Automation is already running'}), 400
    
    data = request.json
    fruits = data.get('fruits', [])
    delay = data.get('delay', 3.0)
    browser = data.get('browser', 'chrome')
    request_profiles = data.get('selectedProfiles', [])
    use_default = data.get('useDefaultIfNoProfile', False)
    
    # Validate inputs
    if not fruits:
        return jsonify({'error': 'No fruits provided'}), 400
    
    if delay < 0.5:
        delay = 3.0
        warning = 'Delay was below minimum (0.5s), set to 3.0s'
    else:
        warning = None
    
    # Handle Chrome profile selection
    profiles_to_use = []
    
    if browser == 'chrome':
        # Priority: request body > memory > default
        if request_profiles:
            profiles_to_use = request_profiles
        elif selected_profiles_memory:
            profiles_to_use = selected_profiles_memory
        elif use_default:
            manager = ChromeProfileManager()
            available = manager.get_available_profiles()
            default = next((p for p in available if p['directory'] == 'Default'), None)
            if default:
                profiles_to_use = [default]
        
        if not profiles_to_use:
            return jsonify({'error': 'No Chrome profiles selected. Provide selectedProfiles in request body or call /api/apply-profiles first.'}), 400
    
    # Check for GUI availability (basic check)
    if platform.system() == 'Linux' and not os.environ.get('DISPLAY'):
        warning = 'Warning: No display detected. Automation may fail on headless systems.'
    
    # Update state and start worker
    with state_lock:
        state['is_running'] = True
        state['status'] = 'Starting automation...'
        state['progress'] = 0
        state['completed'] = 0
        state['total'] = len(fruits) * (len(profiles_to_use) if profiles_to_use else 1)
    
    # Start worker thread
    worker_thread = threading.Thread(
        target=automation_worker,
        args=(fruits, delay, browser, profiles_to_use),
        daemon=True
    )
    worker_thread.start()
    
    response = {
        'message': 'Automation started',
        'total_searches': state['total']
    }
    
    if profiles_to_use and browser == 'chrome':
        response['profiles_in_use'] = [p['name'] for p in profiles_to_use]
    
    if warning:
        response['warning'] = warning
    
    return jsonify(response), 202


@app.route('/api/stop', methods=['POST'])
def stop_automation():
    """Stop the automation process"""
    global state
    
    with state_lock:
        if state['is_running']:
            state['is_running'] = False
            state['status'] = 'Stopping automation...'
    
    return jsonify({'message': 'Stopping'})


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current automation status"""
    with state_lock:
        return jsonify({
            'is_running': state['is_running'],
            'status': state['status'],
            'current_search': state['current_search'],
            'current_profile': state['current_profile'],
            'progress': round(state['progress'], 1),
            'completed': state['completed'],
            'total': state['total']
        })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with system info"""
    manager = ChromeProfileManager()
    
    return jsonify({
        'status': 'healthy',
        'platform': platform.system(),
        'chrome_dir': str(manager.user_data_dir) if manager.user_data_dir else 'Not found',
        'pyautogui_available': True,
        'failsafe_enabled': pyautogui.FAILSAFE
    })


def search_from_file(filename='fruits.json', delay=3, browser='chrome', profile_names=None):
    """
    CLI function to run automation from a file.
    Args:
        filename: JSON file containing fruits list
        delay: Delay between searches in seconds
        browser: Browser to use (chrome, edge, firefox, etc.)
        profile_names: List of Chrome profile names to use (optional)
    """
    # Load fruits from file
    fruits = load_from_file(filename)
    if not fruits:
        print(f"No fruits found in {filename}")
        return
    
    print(f"Loaded {len(fruits)} fruits from {filename}")
    
    # Get profiles if Chrome
    profiles = []
    if browser == 'chrome' and profile_names:
        manager = ChromeProfileManager()
        available = manager.get_available_profiles()
        
        for name in profile_names:
            profile = next((p for p in available if p['name'] == name), None)
            if profile:
                profiles.append(profile)
            else:
                print(f"Warning: Profile '{name}' not found")
    
    # Run automation
    print(f"Starting automation with {browser}...")
    automation_worker(fruits, delay, browser, profiles)
    print("Automation completed")


def main():
    """Main entry point with CLI support"""
    parser = argparse.ArgumentParser(description='Fruit Search Bot')
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode')
    parser.add_argument('--file', default='fruits.json', help='Fruits file (CLI mode)')
    parser.add_argument('--delay', type=float, default=3.0, help='Delay between searches')
    parser.add_argument('--browser', default='chrome', help='Browser to use')
    parser.add_argument('--profiles', nargs='*', help='Chrome profile names (CLI mode)')
    parser.add_argument('--port', type=int, default=5000, help='Flask port')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    
    args = parser.parse_args()
    
    if args.cli:
        # Run in CLI mode
        search_from_file(args.file, args.delay, args.browser, args.profiles)
    else:
        # Load persisted profiles on startup
        global selected_profiles_memory
        persisted = load_from_file('selected_profiles.json')
        if persisted:
            selected_profiles_memory = persisted
            print(f"Loaded {len(persisted)} persisted profiles")
        
        # Run Flask server
        print(f"Starting Flask server on port {args.port}...")
        print(f"Open http://localhost:{args.port} in your browser")
        print("Safety: Move mouse to TOP-LEFT corner to stop automation")
        app.run(host='0.0.0.0', port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()