from datetime import date
import json
import os
import subprocess
from urllib.request import urlopen, Request

FEED_URL = 'https://peapix.com/bing/feed?country='
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:99.0) Gecko/20100101 Firefox/99.0',
}


def main() -> None:
    if not os.environ.get('DISPLAY', None):
        print('$DISPLAY not set')
        return

    # Load configuration from environment variable
    country = os.environ.get('BING_WALLPAPER_COUNTRY', '')
    wallpapers_dir = os.environ.get('BING_WALLPAPER_PATH', os.path.expanduser('~/.wallpapers'))
    # check store directory
    os.makedirs(wallpapers_dir, exist_ok=True)

    # download feed json
    with urlopen(Request(f'{FEED_URL}{country}', headers=DEFAULT_HEADERS)) as resp:
        feed = json.load(resp)

    # download new wallpapers
    for item in feed:
        path = os.path.join(wallpapers_dir, f'{item["date"]}.jpg')
        if not os.path.exists(path):
            with urlopen(Request(item['imageUrl'], headers=DEFAULT_HEADERS)) as resp:
                with open(path, 'wb') as f:
                    f.write(resp.read())

    # check xfce4-desktop wallpaper configuration mode
    proc = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-p', '/backdrop/single-workspace-mode'],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        print('xfconf-query failed for single-workspace-mode, fallback to multi-workspace mode')
        proc = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-n', '-t', 'bool',
                               '-p', '/backdrop/single-workspace-mode', '-s', 'false'])
        if proc.returncode != 0:
            print('xfconf-query failed to set single-workspace-mode')
            return
        single_workspace_mode = False
    else:
        single_workspace_mode = proc.stdout.strip() == 'true'

    print(f'Running in {"single" if single_workspace_mode else "multi"} workspace mode')
    workspace_num_cmd = ['xfconf-query', '-c', 'xfce4-desktop', '-p', '/backdrop/single-workspace-number'] \
        if single_workspace_mode \
        else ['xfconf-query', '-c', 'xfwm4', '-p', '/general/workspace_count']
    proc = subprocess.run(workspace_num_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print('xfconf-query failed to get workspace number')
        return
    workspace_num = int(proc.stdout.strip())
    workspaces = range(workspace_num) if not single_workspace_mode else [workspace_num]

    # update xfce4-desktop wallpaper configuration
    today_wallpaper = os.path.join(wallpapers_dir, f'{date.today().isoformat()}.jpg')
    if not os.path.exists(today_wallpaper):
        return

    proc = subprocess.run(['xrandr | grep " connected"'], 
                          capture_output=True, shell=True, text=True)
    if proc.returncode != 0:
        print('xrandr failed to get connected monitors')
        return
    monitors = [line.split()[0] for line in proc.stdout.split('\n') if line]
    
    for monitor in monitors:
        for workspace_n in workspaces:
            print(f'Setting wallpaper for monitor {monitor} workspace {workspace_n}')
            prop_name = f'/backdrop/screen0/monitor{monitor}/workspace{workspace_n}/last-image'
            proc = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-n', '-t', 'string', 
                                   '-p', prop_name, '-s', today_wallpaper])
            if proc.returncode != 0:
                print(f'xfconf-query failed for monitor {monitor} workspace {workspace_n}')


if __name__ == '__main__':
    main()
