from datetime import date
import json
import os
import subprocess
from urllib.request import urlopen, Request

FEED_URL = 'https://peapix.com/bing/feed?country='
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:99.0) Gecko/20100101 Firefox/99.0',
}

def get_feed(country: str) -> list[dict]:
    """
    Get feed json from Bing.
    """
    with urlopen(Request(f'{FEED_URL}{country}', headers=DEFAULT_HEADERS)) as resp:
        return json.load(resp)

def get_wallpaper_path(wallpapers_dir: str, date: date) -> str:
    """
    Get wallpaper path for date.
    """
    return os.path.join(wallpapers_dir, f'{date}.jpg')
    
def download_wallpaper(url: str, path: str) -> None:
    """
    Download wallpaper from url to path.
    """
    with urlopen(Request(url, headers=DEFAULT_HEADERS)) as resp:
        with open(path, 'wb') as f:
            f.write(resp.read())

def download_new_wallpapers(wallpapers_dir: str, feed: list[dict]) -> None:
    """
    Download new wallpapers from feed.
    """
    for item in feed:
        path = get_wallpaper_path(wallpapers_dir, item['date'])
        if not os.path.exists(path):
            print(f'Downloading wallpaper for {item["date"]}')
            download_wallpaper(item['imageUrl'], path)

def check_workspace_mode() -> bool:
    """
    Check xfce4-desktop wallpaper configuration mode.
    """
    proc = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-p', '/backdrop/single-workspace-mode'],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        print('xfconf-query failed for single-workspace-mode, fallback to multi-workspace mode')
        proc = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-n', '-t', 'bool',
                               '-p', '/backdrop/single-workspace-mode', '-s', 'false'])
        if proc.returncode != 0:
            raise Exception('xfconf-query failed to set single-workspace-mode')
        return False
    return proc.stdout.strip() == 'true'

def get_workspaces(single_workspace_mode) -> list[int]:
    """
    Get list of workspaces. If single_workspace_mode is True, get the single workspace number.
    """
    print(f'Running in {"single" if single_workspace_mode else "multi"} workspace mode')
    workspace_num_cmd = ['xfconf-query', '-c', 'xfce4-desktop', '-p', '/backdrop/single-workspace-number'] \
        if single_workspace_mode \
        else ['xfconf-query', '-c', 'xfwm4', '-p', '/general/workspace_count']
    proc = subprocess.run(workspace_num_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Exception('xfconf-query failed to get workspace number')
    workspace_num = int(proc.stdout.strip())
    return range(workspace_num) if not single_workspace_mode else [workspace_num]

def get_connected_monitors() -> list[str]:
    """
    Get the connected monitors.
    """
    proc = subprocess.run(['xrandr | grep " connected"'],
                          capture_output=True, shell=True, text=True)
    if proc.returncode != 0:
        raise Exception('xrandr failed to get connected monitors')
    return [line.split()[0] for line in proc.stdout.split('\n') if line]

def set_wallpaper(monitor: str, workspace_n: int, wallpaper_path: str) -> None:
    """
    Set wallpaper for monitor and workspace.
    """
    print(f'Setting wallpaper for monitor {monitor} workspace {workspace_n}')
    prop_name = f'/backdrop/screen0/monitor{monitor}/workspace{workspace_n}/last-image'
    proc = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-n', '-t', 'string',
                           '-p', prop_name, '-s', wallpaper_path])
    if proc.returncode != 0:
        print(f'xfconf-query failed for monitor {monitor} workspace {workspace_n}')

def set_wallpaper_for_all_monitors_and_workspaces(wallpaper_path: str) -> None:
    """
    Set wallpaper for all monitors and workspaces.
    """
    workspaces = get_workspaces(check_workspace_mode())
    for monitor in get_connected_monitors():
        for workspace in workspaces:
            set_wallpaper(monitor, workspace, wallpaper_path)

def main() -> None:
    try:
        if not os.environ.get('DISPLAY', None):
            print('$DISPLAY not set')
            return

        # Load configuration from environment variable
        country = os.environ.get('BING_WALLPAPER_COUNTRY', '')
        wallpapers_dir = os.environ.get('BING_WALLPAPER_PATH', os.path.expanduser('~/.wallpapers'))
        # check store directory
        os.makedirs(wallpapers_dir, exist_ok=True)

        # download new wallpapers
        feed = get_feed(country)
        # print feed for debugging if APP_DEBUG is set
        if os.environ.get('APP_DEBUG', None) == '1':
            print(json.dumps(feed, indent=4))
        download_new_wallpapers(wallpapers_dir, feed)

        # get today's wallpaper
        today_wallpaper = os.path.join(wallpapers_dir, f'{date.today().isoformat()}.jpg')
        if not os.path.exists(today_wallpaper):
            print(f'No wallpaper for {date.today()}')
            return

        print(f'Setting wallpaper for {date.today()}')
        # set wallpaper for all monitors and workspaces
        set_wallpaper_for_all_monitors_and_workspaces(today_wallpaper)

    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()
