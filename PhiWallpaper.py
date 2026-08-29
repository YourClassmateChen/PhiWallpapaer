# -*- coding: UTF-8 -*-
"""
PhiWallpaper
版本: v0.2.1-beta.2
开发版本: v0.2.1-beta.2 第4次开发
最后维护时间: 2026.8.30 00:05

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
from psutil import process_iter
from cv2 import VideoCapture, cvtColor, COLOR_BGR2RGB, resize
from PIL import Image, ImageTk
from pathlib import Path


class PhiWallpaperApp:
    """
    主程序类
    """

    def __init__(self):
        # 初始化实例变量
        self.Lable_video_image = None
        self.about_info = ""
        self.is_playing = True
        self.system_vision = ""
        self.path_video = ""
        self.phiwallpaper_vision = "v0.2.1-beta.2"
        self.startinfo_value = None
        self.systray = None
        self.main_window = None
        self.video_image = None

        # 读取关于信息
        with open(self.path_build("lib/about_info.txt"), "r", encoding="utf-8") as f:
            self.about_info = f.read()

        # 加载字体
        self.load_font(self.path_build('lib/SHSSHR.ttf'))
        self.load_font(self.path_build('lib/msyhl.ttc'))

        # 初始化启动信息
        self.startinfo_value = STARTUPINFO()
        self.startinfo_value.dwFlags |= STARTF_USESHOWWINDOW
        self.startinfo_value.wShowWindow = SW_HIDE

        # 读取视频路径
        self.reread_video_path()

    # ==================== 工具函数 ====================
    def create_image(self) -> None:
        """
        创建托盘图像
        :return: 托盘图像对象
        """
        return Image.open(self.path_build(r"lib\icon.ico"))

    def load_font(self, font_path):
        """
        动态加载字体
        :param font_path: 字体路径
        :return:
        """
        try:
            base_path = Path(sys._MEIPASS)
            actual_path = str(base_path.joinpath(font_path))
        except AttributeError:
            actual_path = str(font_path)

        FR_PRIVATE = 0x10
        FR_NOT_ENUM = 0x20
        flags = FR_PRIVATE | FR_NOT_ENUM

        try:
            path_buf = create_unicode_buffer(actual_path)
            add_font = windll.gdi32.AddFontResourceExW
            result = add_font(byref(path_buf), flags, 0)
            return result > 0
        except Exception:
            return False

    def reread_video_path(self):
        """
        读取视频路径文件
        :return:
        """
        with open(self.path_build("lib/path_video.txt"), "r", encoding="utf-8") as f:
            self.path_video = f.read()
            if self.path_video == "default":
                self.path_video = self.path_build(r"lib\video.mp4")
            elif not exists(self.path_video):
                messagebox.showinfo("PhiWallpaper", "找不到动态壁纸文件，已自动替换为默认壁纸")
                self.path_video = self.path_build(r"lib\video.mp4")

    def toImage(self, path):
        """
        转化视频路径为视频第一帧图像
        :param path: 视频路径
        :return: ImageTk.PhotoImage对象
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
            Image.fromarray(cvtColor(img, COLOR_BGR2RGB)).resize((w, h))
        )

    def get_window_client_size(self, hwnd: int) -> tuple:
        """
        获取窗口尺寸
        :param hwnd: 目标窗口句柄
        :return: 窗口尺寸
        """
        if not hwnd:
            return 0, 0
        try:
            rect = GetClientRect(hwnd)
            return rect[2] - rect[0], rect[3] - rect[1]
        except:
            return 0, 0

    def wait_for_render_ready(self, hwnd: int, target_w: int, target_h: int, interval: float | int = 0.1) -> None:
        """
        等待直至ffplay渲染完成
        :param hwnd: ffplay句柄
        :param target_w: 目标宽
        :param target_h: 目标高
        :param interval: 检测间隔
        :return:无
        """
        while True:
            client_w, client_h = self.get_window_client_size(hwnd)
            if client_w >= target_w * 0.8 and client_h >= target_h * 0.8:
                return True
            sleep(interval)

    def StopPlay(self) -> None:
        """
        停止播放
        :return: 无
        """
        Popen(r"taskkill /f /im ffplay.exe", startupinfo=self.startinfo_value, stdout=DEVNULL)

    def path_build(self, path: str):
        """
        构建绝对路径
        :param path: 相对路径（如 "lib\example.txt"）
        :return: 绝对路径
        """
        current_dir = dirname(abspath(sys.argv[0]))
        return join(current_dir, path)

    def is_program_running(self, program_name: str) -> None:
        """
        检测是否多开
        :param program_name: 程序名
        :return:无
        """
        for process in process_iter(['name']):
            if process.info['name'] == program_name:
                return True
        return False

    # ==================== 过程型函数 ====================
    def PlayWallpaper(self) -> None:
        """
        程序启动和壁纸嵌入
        :return: 无
        """
        hDC = GetDC(0)
        screen_w = GetDeviceCaps(hDC, DESKTOPHORZRES)
        screen_h = GetDeviceCaps(hDC, DESKTOPVERTRES)

        ffplay_plan = self.path_build(r'lib\ffplay.exe')
        canshu = (r' -hwaccel vulkan'
                  r' -flags2 fast'
                  r' -avioflags direct'
                  r' -lowres 1'
                  r' -fast'
                  r' -an'
                  r' -noborder'
                  r' -i'
                  f' \"{self.path_video}\"'
                  r' -loglevel panic'
                  f' -x {str(screen_w)} -y {str(screen_h)}'
                  r' -loop 0'
                  r' -crf 0'
                  r' -window_title "PhiWallpaper"'
                  f' -vf \"scale={screen_w}:{screen_h}:force_original_aspect_ratio=increase, crop={screen_w}:{screen_h}, setsar=1:1\" ')
        print(ffplay_plan + canshu)
        Popen(ffplay_plan + canshu, startupinfo=self.startinfo_value)

        # 获取窗口句柄
        while True:
            hApplication = FindWindow("SDL_app", None)
            if hApplication:
                if self.wait_for_render_ready(hApplication, screen_w, screen_h):
                    break
            sleep(0.1)

        hProgman = FindWindow("Progman", None)
        SendMessage(hProgman, 0x52c, 0, 0)

        # Windows 10
        if 10240 <= int(version().split('.')[2]) < 22000:
            print("Windows 10")
            self.system_vision = "Windows 10"

            def EnumWindowsProc(h, l):
                hdef = FindWindowEx(h, None, "SHELLDLL_DefView", None)
                if hdef:
                    hwork = FindWindowEx(None, h, "WorkerW", None)
                    ShowWindow(hwork, SW_HIDE)
                    return False
                return True

            SetParent(hApplication, hProgman)
            try:
                EnumWindows(EnumWindowsProc, None)
            except Exception:
                pass

        # Windows 11
        elif int(version().split('.')[2]) >= 22000:
            print("Windows 11")
            self.system_vision = "Windows 11"

            hSHELLDLL_DefView32 = FindWindowEx(hProgman, None, "SHELLDLL_DefView", None)
            if not hSHELLDLL_DefView32:  # 21H2~23H2
                print("21H2~23H2")

                def find_worker_w_without_shelldll_defview():
                    hwnd_list = []
                    EnumWindows(lambda hwnd, param: param.append(hwnd), hwnd_list)

                    for hwnd in hwnd_list:
                        try:
                            class_name = GetClassName(hwnd)
                            if class_name == "Progman":
                                child_hwnd_list = []
                                EnumChildWindows(hwnd, lambda child_hwnd, param: param.append(child_hwnd),
                                                 child_hwnd_list)

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
                self.system_vision = "Windows 11"

                hWorkerW = FindWindowEx(hProgman, None, "WorkerW", None)

                application_exstyle = GetWindowLong(hApplication, GWL_EXSTYLE)
                application_exstyle |= WS_EX_LAYERED
                SetWindowLong(hApplication, GWL_EXSTYLE, application_exstyle)

                application_style = GetWindowLong(hApplication, GWL_STYLE)
                application_style &= ~WS_POPUP
                application_style |= WS_CHILD
                application_style |= WS_VISIBLE
                SetWindowLong(hApplication, GWL_STYLE, application_style)

                SetLayeredWindowAttributes(hApplication, 0, 255, LWA_ALPHA)

                SetParent(hApplication, hProgman)

                SendMessage(hApplication, WM_PAINT, 0, 0)

                application_style = GetWindowLong(hApplication, GWL_STYLE)
                application_style |= WS_POPUP
                SetWindowLong(hApplication, GWL_STYLE, application_style)

                SetWindowPos(
                    hApplication,
                    HWND_TOP,
                    0, 0, screen_w, screen_h,
                    SWP_NOACTIVATE | SWP_SHOWWINDOW
                )
                SetWindowPos(hSHELLDLL_DefView32, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                SetWindowPos(hWorkerW, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

                MoveWindow(hApplication, 0, 0, screen_w, screen_h, True)
                ShowWindow(hApplication, SW_SHOW)
                SendMessage(hApplication, WM_PAINT, 0, 0)
                RedrawWindow(
                    hApplication,
                    None, None,
                    RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW
                )
        else:
            messagebox.showinfo("PhiWallpaper", "你当前的系统并不支持PhiWallpaper")
            if self.systray:  # 防止未初始化调用
                self.systray.stop()
            self.AllExit()
            sys.exit(0)

    # ==================== 托盘函数 ====================
    def open_window(self) -> None:
        """
        打开管理界面
        :return: 无
        """
        self.main_window.deiconify()

    def MainWallpaper(self):
        """
        调整播放/关闭
        :return:
        """
        if self.is_playing is False:
            self.is_playing = True
            self.PlayWallpaper()
        elif self.is_playing is True:
            self.is_playing = False
            self.StopPlay()

    def AllExit(self):
        """
        退出前的准备
        :return: 无
        """
        self.StopPlay()
        if self.main_window:
            self.main_window.destroy()
        if self.systray:
            self.systray.stop()

    def action(self, icon: Icon, item: any) -> None:
        """
        托盘菜单回调函数
        :param icon: 托盘对象
        :param item: 目标选项
        :return:
        """
        i = str(item)
        if i == "打开PhiWallpaper":
            self.open_window()
        elif i == "开启/关闭壁纸":
            self.MainWallpaper()
        elif i == "退出":
            self.AllExit()
            sys.exit(0)

    # ==================== 托盘主入口 ====================
    def run(self) -> None:
        """
        启动托盘图像
        :return: 无
        """
        if self.is_program_running("ffplay.exe"):
            messagebox.showinfo("PhiWallpaper", "PhiWallpaper已经在系统托盘中了")
            sys.exit()

        self.PlayWallpaper()

        stray_menu = Menu(
            MenuItem("打开PhiWallpaper", action=self.action),
            MenuItem("开启/关闭壁纸", action=self.action),
            MenuItem("退出", action=self.action)
        )
        self.systray = Icon("PhiWallpaper", self.create_image(), "PhiWallpaper", stray_menu)
        self.systray.run()

    # ==================== 主窗口线程 ====================
    def main_window_thread(self) -> None:
        """
        tkinter窗口设置
        :return:
        """
        self.main_window = Tk()
        self.main_window.withdraw()

        style = Style()
        style.configure('TFrame', background="#99FFFF")
        style.configure("TNotebook.Tab", borderwidth=0)
        style.configure("TNotebook", borderwidth=0)

        self.video_image = self.toImage(self.path_video)
        self.main_window.title("PhiWallpaper")
        self.main_window.geometry("768x432")
        self.main_window.configure(background="#AAFFEE")
        self.main_window.iconbitmap(self.path_build(r"lib\icon.ico"))
        self.main_window.resizable(0, 0)
        self.main_window.protocol("WM_DELETE_WINDOW", self.main_window.withdraw)

        messagebox.showinfo("PhiWallpaper", "PhiWallpaper已启动于系统托盘")

        main_notebook = Notebook(self.main_window, padding=(0, 0, 0, 0))
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
              bg="#99FFFF").grid(row=0, column=1, sticky="w")
        Label(frame_main, text=f"版本:{self.phiwallpaper_vision}", font=("微软雅黑 Light",), anchor="w",
              bg="#99FFFF").grid(row=1, column=1, sticky="w")
        Label(frame_main, text=f"系统:{self.system_vision}", font=("微软雅黑 Light",), anchor="w",
              bg="#99FFFF").grid(row=2, column=1, sticky="w")
        Label(frame_main, text="当前壁纸:", font=("微软雅黑 Light",), anchor="w", bg="#99FFFF").grid(row=0, column=2,
                                                                                                     sticky="nw")
        self.Lable_video_image = Label(frame_main, image=self.video_image, anchor="e")
        self.Lable_video_image.grid(row=0, column=3, rowspan=99, sticky="e")
        Button(frame_main, text="开启/关闭动态壁纸", font=("微软雅黑 Light",), anchor="w",
               command=self.MainWallpaper).grid(
            row=3, column=1, sticky="w")

        # 关于
        def ABOUT_open_github():
            open_new_tab(r'https://github.com/YourClassmateChen/PhiWallpaper')

        def ABOUT_open_bilibili():
            open_new_tab(r'https://space.bilibili.com/1996208073')

        def ABOUT_open_blog():
            open_new_tab(r'http://106.53.213.36/')

        def ABOUT_open_guide():
            open_new_tab(r'http://106.53.213.36/信息技术の教程/PhiWallpaper使用指南')

        Label(frame_about, text=self.about_info, font=("微软雅黑 Light", 16), anchor="w", justify="left",
              bg="#99FFFF").grid(row=0, column=0, columnspan=999, sticky="w")
        Button(frame_about, text="项目地址", command=ABOUT_open_github, height=1, width=15,
               font=("微软雅黑 Light",)).grid(row=1, column=0)
        Button(frame_about, text="bilibili主页", command=ABOUT_open_bilibili, height=1, width=15,
               font=("微软雅黑 Light",)).grid(row=1, column=1)
        Button(frame_about, text="个人博客", command=ABOUT_open_blog, height=1, width=15,
               font=("微软雅黑 Light",)).grid(row=1, column=2)
        Button(frame_about, text="使用指南", command=ABOUT_open_guide, height=1, width=15,
               font=("微软雅黑 Light",)).grid(row=1, column=3)

        # 设置
        def SET_start():
            key = OpenKey(HKEY_CURRENT_USER, "Software\Microsoft\Windows\CurrentVersion\Run",
                          KEY_SET_VALUE, KEY_ALL_ACCESS | KEY_WRITE | KEY_CREATE_SUB_KEY)
            try:
                DeleteValue(key, "PhiWallpaper")
                messagebox.showinfo("PhiWallpaper", "已取消开机自启")
            except FileNotFoundError:
                SetValueEx(key, "PhiWallpaper", 0, REG_SZ, realpath(sys.argv[0]))
                messagebox.showinfo("PhiWallpaper", "已设置开机自启")
            CloseKey(key)

        def SET_change_wallpaper():
            path = filedialog.askopenfilename(filetypes=[("视频文件", "*.mp4")], title="PhiWallpaper")
            if not path:
                return
            else:
                with open(self.path_build(r"lib\path_video.txt"), "w", encoding="utf-8") as f:
                    f.write(path)
                messagebox.showinfo("PhiWallpaper", "动态壁纸修改成功!请启动壁纸")
                self.reread_video_path()
                self.video_image = self.toImage(self.path_video)
                self.Lable_video_image.configure(image=self.video_image)
                if self.is_playing is True:
                    self.is_playing = False
                    self.StopPlay()
                elif self.is_playing is False:
                    pass
                return

        Label(frame_set, text=self.about_info, font=("微软雅黑 Light", 16), anchor="w", justify="left",
              bg="#99FFFF").grid(row=0, column=0, columnspan=999, sticky="w")
        Button(frame_set, text="设置/取消开机自启", command=SET_start, height=1, width=17,
               font=("微软雅黑 Light",)).grid(row=1, column=0)
        Button(frame_set, text="修改动态壁纸", command=SET_change_wallpaper, height=1, width=15,
               font=("微软雅黑 Light",)).grid(row=1, column=1)

        self.main_window.mainloop()


# ==================== 程序入口 ====================
if __name__ == '__main__':
    app = PhiWallpaperApp()

    # 启动窗口线程和托盘线程
    window_thread = Thread(target=app.main_window_thread, daemon=True)
    tray_thread = Thread(target=app.run, daemon=True)

    window_thread.start()
    tray_thread.start()

    # 等待窗口线程结束
    window_thread.join()
