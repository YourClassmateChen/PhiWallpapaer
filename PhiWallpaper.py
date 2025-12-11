from win32gui import GetDC
from win32gui import FindWindow
from win32gui import GetWindowLong
from win32gui import SetWindowLong
from win32gui import SendMessage
from win32gui import FindWindowEx
from win32gui import SetLayeredWindowAttributes
from win32gui import SetParent
from win32gui import SetWindowPos
from win32gui import MoveWindow
from win32gui import ShowWindow
from win32gui import RedrawWindow

from win32con import GWL_EXSTYLE
from win32con import WS_EX_LAYERED
from win32con import GWL_STYLE
from win32con import WS_POPUP
from win32con import WS_CHILD
from win32con import WS_VISIBLE
from win32con import LWA_ALPHA
from win32con import WM_PAINT
from win32con import HWND_TOP
from win32con import SWP_NOACTIVATE
from win32con import SWP_SHOWWINDOW
from win32con import SWP_NOMOVE
from win32con import SWP_NOSIZE
from win32con import HWND_BOTTOM
from win32con import SW_SHOW
from win32con import RDW_INVALIDATE
from win32con import RDW_ALLCHILDREN
from win32con import RDW_UPDATENOW
from win32con import DESKTOPHORZRES
from win32con import DESKTOPVERTRES

from win32process import CreateProcess
from win32process import STARTUPINFO

from easygui import msgbox
from easygui import buttonbox
from easygui import fileopenbox

from win32print import GetDeviceCaps
from time import sleep
from sys import argv
from infi.systray import SysTrayIcon
from subprocess import STARTUPINFO
from subprocess import Popen
from subprocess import DEVNULL
from subprocess import STARTF_USESHOWWINDOW
from subprocess import SW_HIDE
from webbrowser import open_new_tab
from winreg import HKEY_CURRENT_USER, KEY_SET_VALUE, KEY_ALL_ACCESS, KEY_WRITE, KEY_CREATE_SUB_KEY, REG_SZ
from winreg import SetValueEx, CloseKey, DeleteValue, OpenKey
from os.path import realpath


def PlayWallpaper():
    with open("./lib/path_video.txt", "r", encoding="utf-8") as f:
        path_video = f.read()
    hDC = GetDC(0)
    # 横向分辨率
    screen_w = GetDeviceCaps(hDC, DESKTOPHORZRES)
    # 纵向分辨率
    screen_h = GetDeviceCaps(hDC, DESKTOPVERTRES)

    ffplay_plan = r'./ffmpeg/bin/ffplay.exe'
    canshu = f' \"{path_video}\"' \
             r' -an' \
             r' -noborder' \
             r' -loglevel quiet' \
             f' -x {screen_w} -y {screen_h}' \
             r' -loop 0' \
             r' -window_title "PhiWallpaper"'
    # r' -hide_banner' \
    # CreateProcess(ffplay_plan, canshu, None, None, 0, 0, None, None, STARTUPINFO())
    # run(ffplay_plan+canshu)
    # _ = None
    # Thread(target=Popen, args=(ffplay_plan + canshu, _, _, _, _, _, _, _, _, _, _, _, STARTUPINFO())).start()
    Popen(ffplay_plan + canshu, startupinfo=startinfo_value)
    # Find window handle
    while True:
        hApplication = FindWindow("SDL_app", None)  # SDL_app
        if hApplication:
            if GetWindowLong(hApplication, GWL_STYLE):
                sleep(0.01)
                break

    hProgman = FindWindow("Progman", None)
    SendMessage(hProgman, 0x52c, 0, 0)  # Send 0x52c message
    hSHELLDLL_DefView32 = FindWindowEx(hProgman, None, "SHELLDLL_DefView", None)
    hWorkerW = FindWindowEx(hProgman, None, "WorkerW", None)

    # Set window long
    application_exstyle = GetWindowLong(hApplication, GWL_EXSTYLE)  # Get window long
    application_exstyle |= WS_EX_LAYERED
    SetWindowLong(hApplication, GWL_EXSTYLE, application_exstyle)

    application_style = GetWindowLong(hApplication, GWL_STYLE)  # Get window long
    application_style &= ~WS_POPUP
    application_style |= WS_CHILD
    application_style |= WS_VISIBLE
    SetWindowLong(hApplication, GWL_STYLE, application_style)

    SetLayeredWindowAttributes(hApplication, 0, 255, LWA_ALPHA)
    # Set parent window
    SetParent(hApplication, hProgman)
    SendMessage(hApplication, WM_PAINT, 0, 0)  # Send PAINT message

    application_style = GetWindowLong(hApplication, GWL_STYLE)  # Get window long
    application_style |= WS_POPUP
    SetWindowLong(hApplication, GWL_STYLE, application_style)

    # Set window pos
    SetWindowPos(
        hApplication,
        HWND_TOP,
        0, 0, screen_w, screen_h,
        SWP_NOACTIVATE | SWP_SHOWWINDOW
    )
    SetWindowPos(hSHELLDLL_DefView32, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    SetWindowPos(hWorkerW, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

    # Show window
    MoveWindow(hApplication, 0, 0, screen_w, screen_h, True)
    ShowWindow(hApplication, SW_SHOW)
    SendMessage(hApplication, WM_PAINT, 0, 0)

    RedrawWindow(
        hApplication,
        None, None,
        RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW
    )


def StopPlay(systray=None):
    # system(r"taskkill /B /f /im ffplay.exe >nul 2>nul")
    # system(r"taskkill /B /f /im ffplay.exe")
    Popen(r"taskkill /f /im ffplay.exe", startupinfo=startinfo_value, stdout=DEVNULL)


def AboutGUI(systray=None) -> None:
    """
    关于界面
    :return: 无
    """
    while True:
        about_input = buttonbox("""
                PhiWallpaper epsilon
                -呈阶梯状分布-
                2025.12.12 最后维护
                """, "PhiWallpaper",
                                ['bilibili', '个人博客', '使用指南'],
                                './lib/small_ico.png'
                                )
        if about_input is None:
            break
        if about_input == 'bilibili':
            # system(r'start /B https://space.bilibili.com/1996208073')
            open_new_tab(r'https://space.bilibili.com/1996208073')
            continue
        elif about_input == '个人博客':
            # system(r'start /B http://106.53.213.36/')
            open_new_tab(r'http://106.53.213.36/')
            continue
        elif about_input == "使用指南":
            open_new_tab(r'http://106.53.213.36/%e4%bf%a1%e6%81%af%e6%8a%80%e6%9c%af%e3%81%ae%e6%95%99%e7%a8%8b'
                         r'/phiwallpaper%e4%bd%bf%e7%94%a8%e6%8c%87%e5%8d%97')
        elif about_input == './lib/small_ico.png':
            msgbox('ヾ(≧ ▽ ≦)ゝ', "PhiWallpaper", "确认")
            continue
        else:
            break


def MainChangeVideo(systray=None) -> None:
    """
    修改动态壁纸
    :return: 无
    """
    global is_playing
    path = fileopenbox("请打开文件", "PhiWallpaper", "*.mp4", None, False)
    if path is None:
        pass
    elif path[-4:] != ".mp4":
        msgbox("请选择mp4格式的视频作为动态壁纸", "PhiWallpaper", "确认")
    else:
        with open("./lib/path_video.txt", "w", encoding="utf-8") as f:
            f.write(path)
        msgbox("动态壁纸修改成功!", "PhiWallpaper", "确认")
        if is_playing is True:
            StopPlay()
            StartPlay()
        elif is_playing is False:
            pass


def MainWallpaper(systray=None):
    global is_playing
    if is_playing is False:
        is_playing = True
        PlayWallpaper()
    elif is_playing is True:
        is_playing = False
        StopPlay()


def SetPhiWallpaper(systray=None):
    while True:
        about_input = buttonbox("""
                        PhiWallpaper epsilon
                        -呈阶梯状分布-
                        2025.12.12 最后维护
                        """, "PhiWallpaper",
                                ['设置/取消开机自启'],
                                './lib/small_ico.png'
                                )
        if about_input is None:
            break
        if about_input == '设置/取消开机自启':
            key = OpenKey(HKEY_CURRENT_USER, "Software\Microsoft\Windows\CurrentVersion\Run",
                          KEY_SET_VALUE,
                          KEY_ALL_ACCESS | KEY_WRITE | KEY_CREATE_SUB_KEY)
            try:  # 删除自启
                DeleteValue(key, "PhiWallpaper")
                msgbox("已取消开机自启", "PhiWallpaper", "确认")
            except FileNotFoundError:  # 添加自启
                SetValueEx(key, "PhiWallpaper", 0, REG_SZ, realpath(argv[0]))
                msgbox("已设置开机自启", "PhiWallpaper", "确认")
            CloseKey(key)
            continue
        elif about_input == './lib/small_ico.png':
            msgbox('ヾ(≧ ▽ ≦)ゝ', "PhiWallpaper", "确认")
            continue
        else:
            break


is_playing = True
startinfo_value = STARTUPINFO()
startinfo_value.dwFlags |= STARTF_USESHOWWINDOW
startinfo_value.wShowWindow = SW_HIDE

if __name__ == '__main__':
    PlayWallpaper()
    menu_p = (
        ("开启/关闭", None, MainWallpaper),
        ("修改动态壁纸", None, MainChangeVideo),
        ("关于", None, AboutGUI),
        ("设置", None, SetPhiWallpaper),
    )
    systray = SysTrayIcon("./lib/icon.ico", "PhiWallpaper", menu_p, on_quit=StopPlay)
    systray.start()
    msgbox("PhiWallpaper已启动于系统托盘", "PhiWallpaper", "确认")
