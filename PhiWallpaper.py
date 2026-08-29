# -*- coding: UTF-8 -*-
"""
PhiWallpaper
版本: v0.2.1-beta.2
开发版本: v0.2.1-beta.2 第2次开发
最后维护时间: 2026.8.29 18:49

开发者: YourClassmateChen(呈阶梯状分布)
开发环境: Python 3.11 64-bit
本程序遵守 GPL-3.0 知识共享许可协议
"""
# 开始引入原生库
from threading import Thread
from platform import version
from os.path import realpath, abspath, dirname, join, exists
from os import environ
from webbrowser import open_new_tab
from time import sleep
import sys
from subprocess import STARTUPINFO, Popen, DEVNULL, STARTF_USESHOWWINDOW, SW_HIDE
from winreg import HKEY_CURRENT_USER, KEY_SET_VALUE, KEY_ALL_ACCESS, KEY_WRITE, KEY_CREATE_SUB_KEY, REG_SZ, \
    SetValueEx, CloseKey, DeleteValue, OpenKey
from tkinter import Tk, Label, messagebox, Button, filedialog, Canvas
from tkinter.ttk import Notebook, Frame, Style
from ctypes import create_unicode_buffer, windll, byref
from pystray import MenuItem, Icon, Menu

# 开始引入第三方库
from win32con import GWL_EXSTYLE, GWL_STYLE, WS_EX_LAYERED, WS_POPUP, WS_CHILD, WS_VISIBLE, HWND_TOP, HWND_BOTTOM, \
    SWP_NOACTIVATE, SWP_SHOWWINDOW, SWP_NOMOVE, SWP_NOSIZE, RDW_INVALIDATE, RDW_UPDATENOW, RDW_ALLCHILDREN, \
    DESKTOPVERTRES, DESKTOPHORZRES, SW_SHOW, LWA_ALPHA, WM_PAINT
from win32gui import GetDC, GetWindowLong, SetWindowLong, SetParent, FindWindow, SendMessage, FindWindowEx, \
    MoveWindow, ShowWindow, RedrawWindow, SetWindowPos, SetLayeredWindowAttributes, GetClientRect, EnumWindows
from win32print import GetDeviceCaps
from infi.systray import SysTrayIcon
from psutil import process_iter
from cv2 import VideoCapture, cvtColor, COLOR_BGR2RGB, resize
from PIL import Image, ImageTk
from pathlib import Path


# 开始定义外部函数
def load_font(font_path):
    """
    动态加载字体到Windows系统（私有加载，仅当前进程可用）

    Args:
        font_path: 字体文件路径

    Returns:
        bool: 加载成功返回True，失败返回False
    """
    # 获取实际路径（支持PyInstaller打包）
    try:
        base_path = Path(sys._MEIPASS)
        actual_path = str(base_path.joinpath(font_path))
    except AttributeError:
        actual_path = str(font_path)

    # 私有加载标志（字体只对当前进程可见，不安装到系统）
    FR_PRIVATE = 0x10
    FR_NOT_ENUM = 0x20  # 不显示在系统字体列表中

    # 组合标志：私有 + 不可枚举
    flags = FR_PRIVATE | FR_NOT_ENUM

    try:
        path_buf = create_unicode_buffer(actual_path)
        add_font = windll.gdi32.AddFontResourceExW
        result = add_font(byref(path_buf), flags, 0)
        return result > 0
    except Exception:
        return False


def reread_video_path() -> None:
    """
    更新视频路径
    :return: 无
    """
    global path_video
    with open(path_build("lib/path_video.txt"), "r", encoding="utf-8") as f:  # 查找视频路径
        path_video = f.read()
        if path_video == "default":  # 如果未修改
            path_video = path_build(r"lib\video.mp4")  # 设置为默认
        elif exists(path_video) is False:  # 如果找不到文件
            messagebox.showinfo("PhiWallpaper", "找不到动态壁纸文件，已自动替换为默认壁纸")  # 弹出提示
            path_video = path_build(r"lib\video.mp4")  # 替换为默认


def toImage(path: str | bytes) -> ImageTk.PhotoImage:
    """
    转化视频路径为视频第一帧图像
    :param path: 视频路径，建议使用path_build()创建
    :return: 视频第一帧，ImageTk.PhotoImage对象，在tkinter中使用
    """
    img = VideoCapture(path).read()[1]
    h = img.shape[0]
    w = img.shape[1]
    bw, bh = 384, 216
    if h > w:
        w = int(w * bh / h)
        h = bh
    elif w > h:
        h = int(h * bw / w)
        w = bw
    else:
        w = bw
        h = bh
    return ImageTk.PhotoImage(
        Image.fromarray(
            cvtColor(img, COLOR_BGR2RGB)).resize((w, h))
    )


def get_window_client_size(hwnd: any) -> any:
    """
    获取窗口客户区尺寸(渲染层实际尺寸)
    :param hwnd: 窗口句柄
    :return: 尺寸
    """
    if not hwnd:
        return 0, 0
    try:
        rect = GetClientRect(hwnd)
        return rect[2] - rect[0], rect[3] - rect[1]
    except:
        return 0, 0


def wait_for_render_ready(hwnd, target_w, target_h, interval=0.1) -> None:
    """
    等待ffplay渲染层就绪（客户区尺寸匹配目标分辨率）
    :param hwnd: ffplay窗口句柄
    :param target_w: 屏幕宽度
    :param target_h: 屏幕高度
    :param interval: 检测间隔
    :return: True=就绪，False=超时
    """
    while True:
        client_w, client_h = get_window_client_size(hwnd)
        # 渲染层就绪判定：客户区尺寸≥目标尺寸80%（兼容加载中的小幅偏差）
        if client_w >= target_w * 0.8 and client_h >= target_h * 0.8:
            return True
        sleep(interval)


# 开始定义用途型函数

def StopPlay() -> None:
    """
    退出视频播放
    通过taskkill命令实现
    :return: 无
    """
    Popen(r"taskkill /f /im ffplay.exe", startupinfo=startinfo_value, stdout=DEVNULL)  # 杀死ffplay进程非阻塞


def path_build(path) -> str | bytes:
    """
    格式:lib\example.txt
    :param path: 格式如上的相对路径
    :return: 绝对路径
    """
    current_dir = dirname(abspath(sys.argv[0]))
    # 构建绝对路径
    file_path = join(current_dir, path)
    return file_path


def is_program_running(program_name: str) -> bool:
    """
    检查是否已经运行了一个PhiWallpaper
    :param program_name: 程序名
    :return: 是否正在运行的bool值
    """
    for process in process_iter(['name']):
        if process.info['name'] == program_name:
            return True
    return False


# 开始定义过程型函数
def PlayWallpaper() -> None:
    """
    负责动态壁纸部分
    :return: 无
    """
    global system_vision, path_video

    hDC = GetDC(0)  # 获取分辨率
    screen_w = GetDeviceCaps(hDC, DESKTOPHORZRES)  # 横向分辨率
    screen_h = GetDeviceCaps(hDC, DESKTOPVERTRES)  # 纵向分辨率

    ffplay_plan = path_build(r'lib\ffplay.exe')  # 获取ffplay位置
    canshu = r' -hwaccel vulkan' \
             r' -flags2 fast' \
             r' -avioflags direct' \
             r' -lowres 1' \
             r' -fast' \
             r' -an' \
             r' -noborder' \
             r' -i' \
             f' \"{path_video}\"' \
             r' -loglevel panic' \
             f' -x {str(screen_w)} -y {str(screen_h)}' \
             r' -loop 0' \
             r' -crf 0' \
             r' -window_title "PhiWallpaper"' \
             f' -vf \"scale={screen_w}:{screen_h}:force_original_aspect_ratio=increase, crop={screen_w}:{screen_h}, setsar=1:1\" '
    print(ffplay_plan + canshu)
    Popen(ffplay_plan + canshu, startupinfo=startinfo_value)  # 创建视频播放线程(非阻塞)

    # 开始获取窗口句柄
    while True:
        hApplication = FindWindow("SDL_app", None)  # 循环查找视频窗口
        if hApplication:  # 找到后
            if wait_for_render_ready(hApplication, screen_w, screen_h):
                break
        sleep(0.1)

    hProgman = FindWindow("Progman", None)  # 查找Progman窗口
    SendMessage(hProgman, 0x52c, 0, 0)  # 发送0x52c消息

    # Windows10
    if 10240 <= int(version().split('.')[2]) < 22000:
        print("Windows 10")
        system_vision = "Windows 10"

        def EnumWindowsProc(h, l):
            hdef = FindWindowEx(h, None, "SHELLDLL_DefView", None)
            if hdef:
                hwork = FindWindowEx(None, h, "WorkerW", None)
                ShowWindow(hwork, SW_HIDE)
                return False
            return True

        SetParent(hApplication, hProgman)
        EnumWindows(EnumWindowsProc, None)

    elif int(version().split('.')[2]) >= 22000:
        print("Windows 11")
        system_vision = "Windows 11"

        hSHELLDLL_DefView32 = FindWindowEx(hProgman, None, "SHELLDLL_DefView", None)  # 查找SHELLDLL_DefView
        if not hSHELLDLL_DefView32:  # 21H2~23H2
            print("21H2~23H2")

            def find_worker_w_without_shelldll_defview() -> any:
                """
                找出WorkerW的句柄
                :return:无
                """
                # 枚举所有顶层窗口
                hwnd_list = []
                EnumWindows(lambda hwnd, param: param.append(hwnd), hwnd_list)

                for hwnd in hwnd_list:
                    try:
                        # 获取窗口类名
                        class_name = GetClassName(hwnd)
                        if class_name == "Progman":
                            # 枚举 Progman 的子窗口
                            child_hwnd_list = []
                            EnumChildWindows(hwnd, lambda child_hwnd, param: param.append(child_hwnd), child_hwnd_list)

                            contains_shelldll_defview = False
                            for child_hwnd in child_hwnd_list:
                                child_class_name = GetClassName(child_hwnd)
                                if child_class_name == "WorkerW":
                                    contains_shelldll_defview = True
                                    hwnd = child_hwnd
                                    break

                            if contains_shelldll_defview:
                                return hwnd
                    except Exception as e:
                        print(f"Error accessing window {hwnd}: {e}")

                return None

            hWorkerW = find_worker_w_without_shelldll_defview()
            SetParent(hApplication, hWorkerW)
        else:  # 24H2+
            print("24H2+")
            system_vision = "Windows 11"

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
def open_window(systray=None):
    """
    打开主页面
    :param systray: 托盘对象
    :return:
    """
    main_window.deiconify()


def MainWallpaper(systray=None) -> None:
    """
    根据is_playing调整播放/关闭
    :param systray: 托盘对象
    :return: 无
    """
    global is_playing  # 关联全局变量is_playing
    if is_playing is False:  # 未播放时
        is_playing = True  # 修改状态
        PlayWallpaper()  # 开始播放
    elif is_playing is True:  # 正在播放时
        is_playing = False  # 修改状态
        StopPlay()  # 停止播放


def AllExit(systray=None) -> None:
    """
    托盘使用，完全退出程序
    :param systray: 托盘对象
    :return: 无
    """
    StopPlay()
    main_window.destroy()


# 开始定义全局变量
with open(path_build("lib/about_info.txt"), "r", encoding="utf-8") as f:
    about_info = f.read()
is_playing = True  # 01广播 指示是否正在播放
system_vision = ""
path_video = ""
phiwallpaper_vision = "v0.2.1-beta.2"
reread_video_path()

load_font(path_build('lib/SHSSHR.ttf'))
load_font(path_build('lib/msyhl.ttc'))
startinfo_value = STARTUPINFO()  # 创建启动信息对象
startinfo_value.dwFlags |= STARTF_USESHOWWINDOW  # 使用显示类窗口属性
startinfo_value.wShowWindow = SW_HIDE  # 设置不显示窗口

def action(icon, item):
    i = str(item)
    if i == "打开PhiWallpaper":
        open_window()
    elif i == "开启/关闭壁纸":
        MainWallpaper()
    elif i == "退出":
        icon.stop()
        AllExit()
        sys.exit(0)

def create_image():
    return Image.open(path_build(r"lib\icon.ico"))

def main():
    # 防止多开
    if is_program_running("ffplay.exe"):
        messagebox.showinfo("PhiWallpaper", "PhiWallpaper已经在系统托盘中了")
        sys.exit()
    PlayWallpaper()  # 启动动态壁纸
    stray_menu = Menu(
        MenuItem("打开PhiWallpaper", action=action),
        MenuItem("开启/关闭壁纸", action=action),
        MenuItem("退出", action=action)
    )
    systray = Icon("PhiWallpaper", create_image(), "PhiWallpaper", stray_menu)
    systray.run()  # 启动托盘

def MainWindowThread():
    global main_window
    main_window = Tk()
    main_window.withdraw()

    style = Style()
    style.configure('TFrame', background="#99FFFF")
    style.configure("TNotebook.Tab", borderwidth=0)
    style.configure("TNotebook", borderwidth=0)

    video_image = toImage(path_video)
    main_window.title("PhiWallpaper")
    main_window.geometry("768x432")
    main_window.configure(background="#AAFFEE")
    main_window.iconbitmap(path_build(r"lib\icon.ico"))
    main_window.resizable(0, 0)
    main_window.protocol("WM_DELETE_WINDOW", main_window.withdraw)

    messagebox.showinfo("PhiWallpaper", "PhiWallpaper已启动于系统托盘")

    main_notebook = Notebook(main_window, padding=(0, 0, 0, 0))
    main_notebook.place(x=0, y=0)

    frame_main = Frame(main_notebook, padding=(0, 0, 0, 0))
    frame_main.pack(fill="both", expand=True)

    frame_about = Frame(main_notebook)
    frame_about.pack(fill="both", expand=True)

    frame_set = Frame(main_notebook)
    frame_set.pack(fill="both", expand=True)

    main_notebook.add(frame_main, text="主页")
    main_notebook.add(frame_about, text="关于")
    main_notebook.add(frame_set, text="设置")

    # 主页
    Label(frame_main, text="PhiWallpaper", font=("思源黑体 CN Regular", 30), anchor="w", fg="#5599FF",
          bg="#99FFFF").grid(
        row=0, column=1, sticky="w")  # 标题
    Label(frame_main, text=f"版本:{phiwallpaper_vision}", font=("微软雅黑 Light",), anchor="w", bg="#99FFFF").grid(row=1,
                                                                                                          column=1,
                                                                                                          sticky="w")  # 版本
    Label(frame_main, text=f"系统:{system_vision}", font=("微软雅黑 Light",), anchor="w", bg="#99FFFF").grid(row=2,
                                                                                                             column=1,
                                                                                                             sticky="w")  # 系统
    Label(frame_main, text="当前壁纸:", font=("微软雅黑 Light",), anchor="w", bg="#99FFFF").grid(row=0, column=2,
                                                                                                 sticky="nw")
    Lable_video_image = Label(frame_main, image=video_image, anchor="e")
    Lable_video_image.grid(row=0, column=3, rowspan=99, sticky="e")
    Button(frame_main, text="开启/关闭动态壁纸", font=("微软雅黑 Light",), anchor="w", command=MainWallpaper).grid(
        row=3, column=1,
        sticky="w")

    # 关于
    def ABOUT_open_github():
        open_new_tab(r'https://github.com/YourClassmateChen/PhiWallpaper')

    def ABOUT_open_bilibili():
        open_new_tab(r'https://space.bilibili.com/1996208073')  # 打开bilibili主页

    def ABOUT_open_blog():
        open_new_tab(r'http://106.53.213.36/')  # 打开博客主页

    def ABOUT_open_guide():
        open_new_tab(r'http://106.53.213.36/信息技术の教程/PhiWallpaper使用指南')  # 打开使用指南

    Label(frame_about, text=about_info, font=("微软雅黑 Light", 16), anchor="w", justify="left", bg="#99FFFF").grid(
        row=0, column=0, columnspan=999, sticky="w")
    Button(frame_about, text="项目地址", command=ABOUT_open_github, height=1, width=15, font=("微软雅黑 Light",)).grid(
        row=1, column=0)
    Button(frame_about, text="bilibili主页", command=ABOUT_open_bilibili, height=1, width=15,
           font=("微软雅黑 Light",)).grid(row=1, column=1)
    Button(frame_about, text="个人博客", command=ABOUT_open_blog, height=1, width=15, font=("微软雅黑 Light",)).grid(
        row=1, column=2)
    Button(frame_about, text="使用指南", command=ABOUT_open_guide, height=1, width=15, font=("微软雅黑 Light",)).grid(
        row=1, column=3)

    # 设置
    def SET_start():
        key = OpenKey(HKEY_CURRENT_USER, "Software\Microsoft\Windows\CurrentVersion\Run",
                      KEY_SET_VALUE,
                      KEY_ALL_ACCESS | KEY_WRITE | KEY_CREATE_SUB_KEY)  # 打开注册表
        try:  # 删除自启
            DeleteValue(key, "PhiWallpaper")  # 删除PhiWallpaper键
            messagebox.showinfo("PhiWallpaper", "已取消开机自启")
        except FileNotFoundError:  # 添加自启
            SetValueEx(key, "PhiWallpaper", 0, REG_SZ, realpath(sys.argv[0]))  # 添加PhiWallpaper键
            messagebox.showinfo("PhiWallpaper", "已设置开机自启")
        CloseKey(key)  # 关闭注册表

    def SET_change_wallpaper():
        global is_playing, video_image  # 关联全局变量is_playing
        path = filedialog.askopenfilename(filetypes=[("视频文件", "*.mp4")], title="PhiWallpaper")
        if not path:  # 选择退出
            return  # 退出修改动态壁纸介面
        else:  # 正确选择文件时
            with open(path_build(r"lib\path_video.txt"), "w", encoding="utf-8") as f:  # 写入到视频路径文件
                f.write(path)  # 写入
            messagebox.showinfo("PhiWallpaper", "动态壁纸修改成功!请启动壁纸")  # 提示
            reread_video_path()
            video_image = toImage(path_video)
            Lable_video_image.configure(image=video_image)
            if is_playing is True:  # 如果正在播放
                is_playing = False  # 修改状态
                StopPlay()  # 停止播放
            elif is_playing is False:  # 如果未播放
                pass  # pass
            return

    Label(frame_set, text=about_info, font=("微软雅黑 Light", 16), anchor="w", justify="left", bg="#99FFFF").grid(
        row=0, column=0, columnspan=999, sticky="w")
    Button(frame_set, text="设置/取消开机自启", command=SET_start, height=1, width=17, font=("微软雅黑 Light",)
           ).grid(row=1, column=0)
    Button(frame_set, text="修改动态壁纸", command=SET_change_wallpaper, height=1, width=15, font=("微软雅黑 Light",)
           ).grid(row=1, column=1)

    main_window.mainloop()


# 开始主程序循环

if __name__ == '__main__':  # 程序启动
    main_thread = Thread(target=main, daemon=True)
    main_thread.start()
    # main_thread.join()
    main_thread2 = Thread(target=MainWindowThread, daemon=True)
    main_thread2.start()
    main_thread2.join()

