import sys
import os
import shutil
import signal
import platform
import subprocess
import colorama
from colorama import Fore, Style
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

colorama.init(autoreset=True)

SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_LINUX = SYSTEM == "Linux"
IS_MAC = SYSTEM == "Darwin"

global_drivers = []

def signal_handler(signum, frame):
    print(Fore.YELLOW + "\nCtrl+C detected! Closing all browser instances...")
    close_all_drivers()
    sys.exit(0)

def close_all_drivers():
    for driver, profile_dir in global_drivers:
        try:
            driver.quit()
        except Exception as e:
            print(Fore.RED + f"Error while closing driver: {e}")
        finally:
            if os.path.exists(profile_dir):
                try:
                    shutil.rmtree(profile_dir, ignore_errors=True)
                except Exception:
                    pass
    global_drivers.clear()
    print(Fore.BLUE + "All browser instances closed.")

def get_profile_base_dir():
    if IS_WINDOWS:
        return os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'selenium_profiles')
    else:
        return os.path.expanduser('~/selenium_profiles')

def ensure_webdriver_manager():
    try:
        import webdriver_manager
        return True
    except ImportError:
        print(Fore.YELLOW + "Installing webdriver-manager...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "webdriver-manager", "-q"])
        return True

def check_browser_installed(browser_type: str):
    browser_type = browser_type.lower()
    if IS_WINDOWS:
        paths = {
            "chrome": [
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            ],
            "edge": [
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
            ],
            "firefox": [
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'Mozilla Firefox', 'firefox.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Mozilla Firefox', 'firefox.exe'),
            ],
        }
        for p in paths.get(browser_type, []):
            if p and os.path.isfile(p):
                return p
    elif IS_LINUX:
        cmd_map = {
            "chrome": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
            "edge": ["microsoft-edge", "microsoft-edge-stable"],
            "firefox": ["firefox"],
        }
        for cmd in cmd_map.get(browser_type, []):
            result = shutil.which(cmd)
            if result:
                return result
    elif IS_MAC:
        app_map = {
            "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "edge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "firefox": "/Applications/Firefox.app/Contents/MacOS/firefox",
        }
        path = app_map.get(browser_type, "")
        if os.path.isfile(path):
            return path

    return None

def _stealth_webdriver(driver):
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })
    except:
        pass

def _platform_args():
    args = []
    if IS_LINUX:
        args.append("--no-sandbox")
        args.append("--disable-dev-shm-usage")
    return args

def launch_chrome(profile_dir: str):
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
    for arg in _platform_args():
        options.add_argument(arg)

    binary = check_browser_installed("chrome")
    if binary:
        options.binary_location = binary

    prefs = {
        "credentials_enable_service": True,
        "profile.password_manager_enabled": True,
        "profile.default_content_setting_values.notifications": 1,
        "download.prompt_for_download": True,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": False
    }
    options.add_experimental_option("prefs", prefs)

    driver = None
    errors = []

    try:
        from selenium.webdriver.chrome.service import Service as ChromeService
        driver = webdriver.Chrome(service=ChromeService(), options=options)
        print(Fore.GREEN + "  Chrome launched (system chromedriver)")
    except Exception as e1:
        errors.append(str(e1))
        try:
            ensure_webdriver_manager()
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service as ChromeService
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            print(Fore.GREEN + "  Chrome launched (auto-downloaded chromedriver)")
        except Exception as e2:
            errors.append(str(e2))

    if driver is None:
        raise Exception(
            "Chrome launch failed.\n" +
            "\n".join(f"  - {e}" for e in errors) +
            "\n\nFix: pip install --upgrade selenium webdriver-manager"
        )

    _stealth_webdriver(driver)
    return driver

def launch_firefox(profile_dir: str):
    options = webdriver.FirefoxOptions()
    options.add_argument('-profile')
    options.add_argument(profile_dir)
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", profile_dir)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    options.set_preference("pdfjs.disabled", False)

    binary = check_browser_installed("firefox")
    if binary:
        options.binary_location = binary

    driver = None
    errors = []

    try:
        from selenium.webdriver.firefox.service import Service as FirefoxService
        driver = webdriver.Firefox(service=FirefoxService(), options=options)
        print(Fore.GREEN + "  Firefox launched (system geckodriver)")
    except Exception as e1:
        errors.append(str(e1))
        try:
            ensure_webdriver_manager()
            from webdriver_manager.firefox import GeckoDriverManager
            from selenium.webdriver.firefox.service import Service as FirefoxService
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            print(Fore.GREEN + "  Firefox launched (auto-downloaded geckodriver)")
        except Exception as e2:
            errors.append(str(e2))

    if driver is None:
        raise Exception(
            "Firefox launch failed.\n" +
            "\n".join(f"  - {e}" for e in errors) +
            "\n\nFix: pip install --upgrade selenium webdriver-manager"
        )

    return driver

def launch_edge(profile_dir: str):
    options = webdriver.EdgeOptions()

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-features=msEdgeAutoImport,msEdgeSidebarV2,msEdgeIdentityOnNewTabPageMode")

    for arg in _platform_args():
        options.add_argument(arg)

    binary = check_browser_installed("edge")
    if binary:
        options.binary_location = binary

    prefs = {
        "credentials_enable_service": True,
        "profile.password_manager_enabled": True,
        "profile.default_content_setting_values.notifications": 1,
        "download.prompt_for_download": True,
        "safebrowsing.enabled": True,
        "browser.show_hub_popup_on_browser_launch": False,
        "user_experience_metrics.personalization_data_consent_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    driver = None
    errors = []

    try:
        from selenium.webdriver.edge.service import Service as EdgeService
        driver = webdriver.Edge(service=EdgeService(), options=options)
        print(Fore.GREEN + "  Edge launched (system msedgedriver)")
    except Exception as e1:
        errors.append(str(e1))
        try:
            ensure_webdriver_manager()
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            from selenium.webdriver.edge.service import Service as EdgeService
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
            print(Fore.GREEN + "  Edge launched (auto-downloaded msedgedriver)")
        except Exception as e2:
            errors.append(str(e2))

    if driver is None:
        raise Exception(
            "Edge launch failed.\n" +
            "\n".join(f"  - {e}" for e in errors) +
            "\n\nFix: pip install --upgrade selenium webdriver-manager"
        )

    _stealth_webdriver(driver)
    return driver

def clean_stale_profiles(browser_type: str):
    base_dir = get_profile_base_dir()
    if not os.path.isdir(base_dir):
        return
    prefix = f"{browser_type}_instance_"
    removed = 0
    for entry in os.listdir(base_dir):
        if entry.startswith(prefix):
            full_path = os.path.join(base_dir, entry)
            if os.path.isdir(full_path):
                try:
                    shutil.rmtree(full_path, ignore_errors=True)
                    removed += 1
                except Exception:
                    pass
    if removed > 0:
        print(Fore.YELLOW + f"  Cleaned {removed} old {browser_type} profile(s)")

def open_browser_instances(browser_type: str, num_instances: int):
    browser_type = browser_type.lower()
    if browser_type not in ["chrome", "firefox", "edge"]:
        print(Fore.RED + "Invalid browser type. Choose 'chrome', 'edge', or 'firefox'.")
        return

    binary = check_browser_installed(browser_type)
    if binary:
        print(Fore.GREEN + f"  Found {browser_type}: {binary}")
    else:
        print(Fore.YELLOW + f"  {browser_type} not found in standard paths — Selenium will try to locate it")

    base_dir = get_profile_base_dir()
    os.makedirs(base_dir, exist_ok=True)

    clean_stale_profiles(browser_type)

    for i in range(num_instances):
        profile_dir = os.path.join(base_dir, f"{browser_type}_instance_{i+1}")

        if os.path.exists(profile_dir):
            try:
                shutil.rmtree(profile_dir)
            except Exception as e:
                print(Fore.YELLOW + f"  Warning: Could not remove old profile: {e}")

        os.makedirs(profile_dir, exist_ok=True)

        try:
            print(Fore.CYAN + f"  Launching {browser_type} instance {i+1}...")
            if browser_type == "chrome":
                driver = launch_chrome(profile_dir)
            elif browser_type == "firefox":
                driver = launch_firefox(profile_dir)
            else:
                driver = launch_edge(profile_dir)

            try:
                driver.maximize_window()
            except Exception:
                pass

            print(Fore.GREEN + f"  Instance {i+1} ready — profile: {profile_dir}")
            global_drivers.append((driver, profile_dir))

        except Exception as e:
            print(Fore.RED + f"  Failed to launch instance {i+1}: {e}")

    if not global_drivers:
        print(Fore.RED + "\nNo browser instances were successfully launched.")
        return

    print()
    print(Fore.GREEN + f"  {len(global_drivers)} instance(s) running on {SYSTEM}")
    print(Fore.YELLOW + "  Type 'q' + Enter to close all, or press Ctrl+C")
    print()

    while True:
        still_open = []
        for (driver, prof) in global_drivers:
            try:
                _ = driver.current_url
                still_open.append((driver, prof))
            except WebDriverException:
                pass

        global_drivers[:] = still_open

        if not global_drivers:
            print(Fore.BLUE + "All browser instances have been manually closed.")
            break

        user_input = input(Fore.CYAN + "  > ").strip().lower()
        if user_input == 'q':
            print(Fore.YELLOW + "  Closing all browser instances...")
            break

    close_all_drivers()

def print_banner():
    print()
    if IS_WINDOWS:
        os_label = "Windows"
        os_color = Fore.CYAN
        home = os.environ.get('USERPROFILE', '~')
    elif IS_LINUX:
        os_label = "Linux"
        os_color = Fore.GREEN
        home = os.path.expanduser('~')
    else:
        os_label = "macOS"
        os_color = Fore.MAGENTA
        home = os.path.expanduser('~')

    print(Fore.YELLOW + Style.BRIGHT + r"   ____                                        ")
    print(Fore.YELLOW + Style.BRIGHT + r"  | __ ) _ __ _____      _____  ___ _ __        ")
    print(Fore.YELLOW + Style.BRIGHT + r"  |  _ \| '__/ _ \ \ /\ / / __|/ _ \ '__|       ")
    print(Fore.YELLOW + Style.BRIGHT + r"  | |_) | | | (_) \ V  V /\__ \  __/ |          ")
    print(Fore.YELLOW + Style.BRIGHT + r"  |____/|_|  \___/ \_/\_/ |___/\___|_|          ")
    print(Fore.YELLOW + Style.BRIGHT + r"  __  __                                        ")
    print(Fore.YELLOW + Style.BRIGHT + r" |  \/  | __ _ _ __   __ _  __ _  ___ _ __      ")
    print(Fore.YELLOW + Style.BRIGHT + r" | |\/| |/ _` | '_ \ / _` |/ _` |/ _ \ '__|     ")
    print(Fore.YELLOW + Style.BRIGHT + r" | |  | | (_| | | | | (_| | (_| |  __/ |        ")
    print(Fore.YELLOW + Style.BRIGHT + r" |_|  |_|\__,_|_| |_|\__,_|\__, |\___|_|        ")
    print(Fore.YELLOW + Style.BRIGHT + r"                           |___/                 ")
    print()
    print(os_color + Style.BRIGHT + f"  Platform : {os_label}")
    print(Fore.WHITE + f"  Home     : {home}")
    print(Fore.WHITE + f"  Profiles : {get_profile_base_dir()}")
    print(Fore.WHITE + f"  Python   : {sys.version.split()[0]}")
    print()
    print(Fore.WHITE + "  Supports : Chrome | Firefox | Edge")
    print(Fore.WHITE + "  Author   : krainium")
    print()

if __name__ == "__main__":
    print_banner()

    signal.signal(signal.SIGINT, signal_handler)
    if IS_WINDOWS:
        import atexit
        atexit.register(close_all_drivers)
        try:
            signal.signal(signal.SIGBREAK, signal_handler)
        except (AttributeError, OSError):
            pass
    else:
        signal.signal(signal.SIGTERM, signal_handler)

    browser_type = input(Fore.CYAN + "  Browser (chrome/edge/firefox): ").strip()
    try:
        num_instances = int(input(Fore.CYAN + "  Number of instances: ").strip())
        if num_instances <= 0:
            raise ValueError("Must be greater than 0")
    except ValueError as e:
        print(Fore.RED + f"  Invalid input: {e}")
        sys.exit(1)

    print()

    try:
        open_browser_instances(browser_type, num_instances)
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n  Keyboard interrupt!")
        close_all_drivers()
        sys.exit(0)
