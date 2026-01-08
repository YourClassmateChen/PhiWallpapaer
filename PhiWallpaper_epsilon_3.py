"""
PhiWallpaper
版本: v0.1.0-epsilon
开发版本: v0.1.0-epsilon 第3次开发
最后维护时间: 2026.1.8 00:06

开发者: YourClassmateChen(呈阶梯状分布)
开发环境: Python3.11
本程序遵守 CC BY-SA 4.0 知识共享许可协议
"""

# 开始引入库内函数
from win32con import GWL_EXSTYLE, GWL_STYLE
from win32con import WS_EX_LAYERED, WS_POPUP, WS_CHILD, WS_VISIBLE
from win32con import HWND_TOP, HWND_BOTTOM
from win32con import SWP_NOACTIVATE, SWP_SHOWWINDOW, SWP_NOMOVE, SWP_NOSIZE
from win32con import RDW_INVALIDATE, RDW_UPDATENOW, RDW_ALLCHILDREN
from win32con import DESKTOPVERTRES, DESKTOPHORZRES
from win32con import SW_SHOW, LWA_ALPHA, WM_PAINT

from win32gui import GetDC, GetWindowLong, SetWindowLong, SetParent, FindWindow, SendMessage, FindWindowEx
from win32gui import MoveWindow, ShowWindow, RedrawWindow, SetWindowPos, SetLayeredWindowAttributes

from winreg import HKEY_CURRENT_USER, KEY_SET_VALUE, KEY_ALL_ACCESS, KEY_WRITE, KEY_CREATE_SUB_KEY, REG_SZ
from winreg import SetValueEx, CloseKey, DeleteValue, OpenKey

from subprocess import STARTUPINFO, Popen, DEVNULL, STARTF_USESHOWWINDOW, SW_HIDE
from easygui import msgbox, buttonbox, fileopenbox
from win32print import GetDeviceCaps
from time import sleep
from sys import argv
from infi.systray import SysTrayIcon
from webbrowser import open_new_tab
from os.path import realpath, abspath, dirname, join, exists


# 开始定义用途型函数

def path_build(path) -> bytes:
    """
    格式:lib\example.txt
    :param path: 格式如上的相对路径
    :return: 绝对路径
    """
    current_dir = dirname(abspath(argv[0]))
    # 构建绝对路径
    file_path = join(current_dir, path)
    return file_path


# 开始定义过程型函数

def PlayWallpaper() -> None:
    # 开始创建视频窗口
    with open(path_build("lib/path_video.txt"), "r", encoding="utf-8") as f:  # 查找视频路径
        path_video = f.read()
        if path_video == "default":  # 如果未修改
            path_video = path_build(r"lib\video.mp4")  # 设置为默认
        elif exists(path_video) is False:  # 如果找不到文件
            msgbox("找不到动态壁纸文件，已自动替换为默认壁纸", "PhiWallpaper", "确认")  # 弹出提示
            path_video = path_build(r"lib\video.mp4")  # 替换为默认

    hDC = GetDC(0)  # 获取分辨率
    screen_w = GetDeviceCaps(hDC, DESKTOPHORZRES)  # 横向分辨率
    screen_h = GetDeviceCaps(hDC, DESKTOPVERTRES)  # 纵向分辨率

    ffplay_plan = path_build(r'ffmpeg\bin\ffplay.exe')  # 获取ffplay位置
    canshu = f' \"{path_video}\"' \
             r' -an' \
             r' -noborder' \
             r' -loglevel quiet' \
             f' -x {screen_w} -y {screen_h}' \
             r' -loop 0' \
             r' -enable_vulkan' \
             r' -crf 0' \
             r' -window_title "PhiWallpaper"' \
             f' -vf \"scale={screen_w}:{screen_h}:force_original_aspect_ratio=increase, crop={screen_w}:{screen_h}\"' \
             r' -i'  # 获取参数
    Popen(ffplay_plan + canshu, startupinfo=startinfo_value)  # 创建视频播放线程(非阻塞)

    # 开始获取窗口句柄
    while True:
        hApplication = FindWindow("SDL_app", None)  # 循环查找视频窗口
        if hApplication:  # 找到后
            if GetWindowLong(hApplication, GWL_STYLE):  # 完全打开
                sleep(0.2)
                break  # 进行下一步

    hProgman = FindWindow("Progman", None)  # 查找Progman窗口
    SendMessage(hProgman, 0x52c, 0, 0)  # 发送0x52c消息
    hSHELLDLL_DefView32 = FindWindowEx(hProgman, None, "SHELLDLL_DefView", None)  # 查找SHELLDLL_DefView
    hWorkerW = FindWindowEx(hProgman, None, "WorkerW", None)  # 查找WorkerW

    # 开始设置窗体属性
    application_exstyle = GetWindowLong(hApplication, GWL_EXSTYLE)  # 获取扩展属性
    application_exstyle |= WS_EX_LAYERED  # 增加LAYERED属性
    SetWindowLong(hApplication, GWL_EXSTYLE, application_exstyle)  # 设置为新扩展属性

    application_style = GetWindowLong(hApplication, GWL_STYLE)  # 获取属性
    application_style &= ~WS_POPUP  # 删除POPUP属性
    application_style |= WS_CHILD  # 增加CHILD属性
    application_style |= WS_VISIBLE  # 增加VISIBLE属性
    SetWindowLong(hApplication, GWL_STYLE, application_style)  # 设置为新属性

    SetLayeredWindowAttributes(hApplication, 0, 255, LWA_ALPHA)  # 设置为不透明

    # 开始嵌入窗口
    SetParent(hApplication, hProgman)

    # 开始处理窗口
    SendMessage(hApplication, WM_PAINT, 0, 0)  # 发送重绘消息

    application_style = GetWindowLong(hApplication, GWL_STYLE)  # 获取属性
    application_style |= WS_POPUP  # 添加POPUP属性
    SetWindowLong(hApplication, GWL_STYLE, application_style)  # 设置为新属性

    SetWindowPos(
        hApplication,
        HWND_TOP,
        0, 0, screen_w, screen_h,
        SWP_NOACTIVATE | SWP_SHOWWINDOW
    )  # 设置窗口Pos
    SetWindowPos(hSHELLDLL_DefView32, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)  # 设置SHELLDLL_DefView32Pos
    SetWindowPos(hWorkerW, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)  # 设置WorkerWPos

    # 开始显示窗口
    MoveWindow(hApplication, 0, 0, screen_w, screen_h, True)  # 移动窗口来重置焦点
    ShowWindow(hApplication, SW_SHOW)  # 显示窗口
    SendMessage(hApplication, WM_PAINT, 0, 0)  # 发送重绘消息
    RedrawWindow(
        hApplication,
        None, None,
        RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW
    )  # 重绘窗口


# 开始定义托盘函数

def StopPlay(systray=None) -> None:
    """
    退出视频播放
    通过taskkill命令实现
    :param systray: None
    :return: None
    """
    Popen(r"taskkill /f /im ffplay.exe", startupinfo=startinfo_value, stdout=DEVNULL)  # 杀死ffplay进程非阻塞


def AboutGUI(systray=None) -> None:
    """
    关于界面
    :return: None
    """
    while True:
        about_input = buttonbox(about_info, "PhiWallpaper",
                                ['bilibili', '个人博客', '使用指南'],
                                path_build(r'lib\small_ico.png')
                                )  # 关于主界面
        if about_input is None:  # 选择退出关于
            break  # 退出关于
        if about_input == 'bilibili':  # 选择bilibili
            open_new_tab(r'https://space.bilibili.com/1996208073')  # 打开bilibili主页
            continue
        elif about_input == '个人博客':  # 选择个人博客
            open_new_tab(r'http://106.53.213.36/')  # 打开博客主页
            continue
        elif about_input == "使用指南":  # 选择使用指南
            open_new_tab(r'http://106.53.213.36/PhiWallpaper使用指南')  # 打开使用指南
        elif about_input == path_build(r'lib\small_ico.png'):  # 选择图片
            msgbox('ヾ(≧ ▽ ≦)ゝ', "PhiWallpaper", "确认")  # 弹出提示
            continue
        else:  # 未知领域
            break  # 退出


def MainChangeVideo(systray=None) -> None:
    """
    修改动态壁纸
    :return: None
    """
    global is_playing  # 关联全局变量is_playing
    while True:
        path = fileopenbox("请打开文件", "PhiWallpaper", "*.mp4", None, False)  # 打开选择文件窗口
        if path is None:  # 选择退出
            break  # 退出修改动态壁纸介面
        elif path[-4:] != ".mp4":  # 如果格式不是.mp4
            msgbox("请选择mp4格式的视频作为动态壁纸", "PhiWallpaper", "确认")  # 提示
            continue
        else:  # 正确选择文件时
            with open(path_build(r"lib\path_video.txt"), "w", encoding="utf-8") as f:  # 写入到视频路径文件
                f.write(path)  # 写入
            msgbox("动态壁纸修改成功!请启动壁纸", "PhiWallpaper", "确认")  # 提示
            if is_playing is True:  # 如果正在播放
                is_playing = False  # 修改状态
                StopPlay()  # 停止播放
            elif is_playing is False:  # 如果未播放
                pass  # pass
            break


def MainWallpaper(systray=None) -> None:
    """
    根据is_playing调整播放/关闭
    :param systray: None
    :return: None
    """
    global is_playing  # 关联全局变量is_playing
    if is_playing is False:  # 未播放时
        is_playing = True  # 修改状态
        PlayWallpaper()  # 开始播放
    elif is_playing is True:  # 正在播放时
        is_playing = False  # 修改状态
        StopPlay()  # 停止播放


def SetPhiWallpaper(systray=None) -> None:
    """
    设置界面
    :param systray: None
    :return: None
    """
    while True:
        set_input = buttonbox(about_info, "PhiWallpaper",
                              ['设置/取消开机自启'],
                              path_build(r'lib\small_ico.png')
                              )  # 设置界面
        if set_input is None:  # 选择退出
            break  # 退出设置界面
        if set_input == '设置/取消开机自启':  # 选择设置/取消开机自启
            key = OpenKey(HKEY_CURRENT_USER, "Software\Microsoft\Windows\CurrentVersion\Run",
                          KEY_SET_VALUE,
                          KEY_ALL_ACCESS | KEY_WRITE | KEY_CREATE_SUB_KEY)  # 打开注册表
            try:  # 删除自启
                DeleteValue(key, "PhiWallpaper")  # 删除PhiWallpaper键
                msgbox("已取消开机自启", "PhiWallpaper", "确认")  # 提示
            except FileNotFoundError:  # 添加自启
                SetValueEx(key, "PhiWallpaper", 0, REG_SZ, realpath(argv[0]))  # 添加PhiWallpaper键
                msgbox("已设置开机自启", "PhiWallpaper", "确认")  # 提示
            CloseKey(key)  # 关闭注册表
            continue
        elif set_input == path_build(r'lib\small_ico.png'):  # 点击图片
            msgbox('ヾ(≧ ▽ ≦)ゝ', "PhiWallpaper", "确认")  # 提示
            continue
        else:  # 未知领域
            break  # 退出


# 开始定义全局变量

about_info = """
                        PhiWallpaper epsilon
                        -呈阶梯状分布-
                        2025.12.12 最后维护
                        """
is_playing = True  # 01广播 指示是否正在播放
startinfo_value = STARTUPINFO()  # 创建启动信息对象
startinfo_value.dwFlags |= STARTF_USESHOWWINDOW  # 使用显示类窗口属性
startinfo_value.wShowWindow = SW_HIDE  # 设置不显示窗口

# 开始主程序循环

if __name__ == '__main__':  # 程序启动
    PlayWallpaper()  # 启动动态壁纸
    menu_p = (
        ("开启/关闭", None, MainWallpaper),
        ("修改动态壁纸", None, MainChangeVideo),
        ("关于", None, AboutGUI),
        ("设置", None, SetPhiWallpaper),
    )  # 菜单栏设置
    systray = SysTrayIcon(path_build(r"lib\icon.ico"), "PhiWallpaper", menu_p, on_quit=StopPlay)  # 设置托盘对象
    systray.start()  # 启动托盘
    msgbox("PhiWallpaper已启动于系统托盘", "PhiWallpaper", "确认")  # 提示
