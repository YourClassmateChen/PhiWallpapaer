# -*- coding: UTF-8 -*-
"""
PhiWallpaper
版本: v0.2.2-beta.1
开发版本: v0.2.2-beta.1 第1次开发
最后维护时间: 2026.8.30 01:29

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
from tkinter.ttk import Notebook, Frame, Style, Button as TButton
from ctypes import create_unicode_buffer, windll, byref
from pystray import MenuItem, Icon, Menu

# 开始引入第三方库
from win32con import GWL_EXSTYLE, GWL_STYLE, WS_EX_LAYERED, WS_POPUP, WS_CHILD, WS_VISIBLE, HWND_TOP, HWND_BOTTOM, \
    SWP_NOACTIVATE, SWP_SHOWWINDOW, SWP_NOMOVE, SWP_NOSIZE, RDW_INVALIDATE, RDW_UPDATENOW, RDW_ALLCHILDREN, \
    DESKTOPVERTRES, DESKTOPHORZRES, SW_SHOW, LWA_ALPHA, WM_PAINT
from win32gui import GetDC, GetWindowLong, SetWindowLong, SetParent, FindWindow, SendMessage, FindWindowEx, \
    MoveWindow, ShowWindow, RedrawWindow, SetWindowPos, SetLayeredWindowAttributes, GetClientRect, EnumWindows
from win32print import GetDeviceCaps
from psutil import process_iter, NoSuchProcess, AccessDenied, ZombieProcess
from cv2 import VideoCapture, cvtColor, COLOR_BGR2RGB, resize
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
from pathlib import Path


class PhiWallpaperApp:
    """
    主程序类
    """

    def __init__(self):
        # 初始化实例变量
        self.status_var_text = None
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
        self.status_label_dynamic = None  # 动态状态标签
        self.bg_image = None  # 模糊暗色背景图

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
        转化视频路径为视频第一帧图像（预览缩略图）
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

    def create_blurred_background(self, path, width=800, height=500):
        """
        生成模糊暗色的背景图
        :param path: 视频路径
        :param width: 窗口宽度
        :param height: 窗口高度
        :return: ImageTk.PhotoImage对象
        """
        cap = VideoCapture(path)
        ret, frame = cap.read()
        cap.release()
        if ret:
            img = Image.fromarray(cvtColor(frame, COLOR_BGR2RGB))
            img = img.resize((width, height), Image.LANCZOS)
            img = img.filter(ImageFilter.GaussianBlur(10))
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.5)  # 暗色
            return ImageTk.PhotoImage(img)
        else:
            # 若读取失败，返回纯色背景
            return ImageTk.PhotoImage(Image.new('RGB', (width, height), '#222e49'))

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
        for proc in process_iter(['name']):
            try:
                # 获取进程名并比较
                if proc.info['name'] == program_name:
                    return True
            except (NoSuchProcess, AccessDenied, ZombieProcess):
                # 忽略进程已终止、无权限或僵尸进程等异常，继续遍历
                continue
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
        # 更新状态标签
        if hasattr(self, 'status_label_dynamic') and self.status_label_dynamic is not None:
            self.status_label_dynamic.config(text="播放中" if self.is_playing else "已停止")

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
        if self.is_program_running("PhiWallpaper.exe"):
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
        :return:无
        """
        self.main_window = Tk()
        self.main_window.withdraw()
        self.main_window.title("PhiWallpaper")
        self.main_window.geometry("800x500")
        self.main_window.configure(background="#222e49")  # 深蓝紫色背景
        self.main_window.iconbitmap(self.path_build(r"lib\icon.ico"))
        self.main_window.resizable(0, 0)
        self.main_window.protocol("WM_DELETE_WINDOW", self.main_window.withdraw)

        # 生成模糊暗色背景图并铺满窗口
        self.bg_image = self.create_blurred_background(self.path_video, 800, 500)
        bg_label = Label(self.main_window, image=self.bg_image)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # 现代化样式配置（深蓝紫色调）
        style = Style()
        style.theme_use('clam')
        # Notebook样式
        style.configure('TNotebook', background='#222e49', borderwidth=0)
        style.configure('TNotebook.Tab', background='#2a3b5c', foreground='#ffffff', padding=[10, 5],
                        font=('微软雅黑', 10), borderwidth=0, focuscolor='none')
        style.map('TNotebook.Tab',
                  background=[('selected', '#3b4f73'), ('active', '#314568')],
                  foreground=[('selected', '#ffffff')])
        # Frame样式
        style.configure('TFrame', background='#222e49')
        # Label样式
        style.configure('TLabel', background='#222e49', foreground='#e0e0e0', font=('微软雅黑', 10))
        # 按钮样式
        style.configure('Modern.TButton', background='#1a73e8', foreground='white', font=('微软雅黑', 10),
                        borderwidth=0, focusthickness=0, padding=(15, 8))
        style.map('Modern.TButton',
                  background=[('active', '#1765cc'), ('pressed', '#1558b0')],
                  foreground=[('disabled', '#b0b0b0')])
        # 次级按钮样式
        style.configure('Secondary.TButton', background='#2a3b5c', foreground='#e0e0e0', font=('微软雅黑', 10),
                        borderwidth=0, focusthickness=0, padding=(15, 8))
        style.map('Secondary.TButton',
                  background=[('active', '#314568'), ('pressed', '#3b4f73')])

        # 加载壁纸预览图
        self.video_image = self.toImage(self.path_video)

        messagebox.showinfo("PhiWallpaper", "PhiWallpaper已启动于系统托盘")

        # 主Notebook，使用place放置在窗口中央，留出边缘显示背景
        main_notebook = Notebook(self.main_window, padding=(10, 5))
        main_notebook.place(relx=0.5, rely=0.5, anchor="center", width=760, height=440)

        # ========== 主页标签 ==========
        frame_main = Frame(main_notebook, padding=(20, 20), style='TFrame')
        frame_main.pack(fill="both", expand=True)

        # 左侧信息区
        left_frame = Frame(frame_main, style='TFrame')
        left_frame.grid(row=0, column=0, sticky="nw")

        # 标题
        title_label = Label(left_frame, text="PhiWallpaper", font=('微软雅黑', 24, 'bold'),
                            fg="#1a73e8", bg="#222e49")
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        # 版本信息
        version_label = Label(left_frame, text=f"版本：{self.phiwallpaper_vision}",
                              font=('微软雅黑', 10), fg="#b0b0b0", bg="#222e49")
        version_label.grid(row=1, column=0, sticky="w", pady=2)

        # 系统信息
        system_label = Label(left_frame, text=f"系统：{self.system_vision}",
                             font=('微软雅黑', 10), fg="#b0b0b0", bg="#222e49")
        system_label.grid(row=2, column=0, sticky="w", pady=2)

        # 当前壁纸状态
        status_label = Label(left_frame, text="当前壁纸状态：", font=('微软雅黑', 10, 'bold'),
                             fg="#e0e0e0", bg="#222e49")
        status_label.grid(row=3, column=0, sticky="w", pady=(20, 5))

        self.status_var_text = "播放中" if self.is_playing else "已停止"
        self.status_label_dynamic = Label(left_frame, text=self.status_var_text,
                                          font=('微软雅黑', 10), fg="#1a73e8", bg="#222e49")
        self.status_label_dynamic.grid(row=4, column=0, sticky="w")

        # 按钮区域
        button_frame = Frame(left_frame, style='TFrame')
        button_frame.grid(row=5, column=0, sticky="w", pady=(30, 0))

        toggle_btn = TButton(button_frame, text="开启/关闭动态壁纸", command=self.MainWallpaper,
                             style='Modern.TButton')
        toggle_btn.pack(side="left", padx=(0, 10))

        # 右侧预览区
        right_frame = Frame(frame_main, style='TFrame')
        right_frame.grid(row=0, column=1, sticky="ne", padx=(40, 0))

        preview_label = Label(right_frame, text="壁纸预览", font=('微软雅黑', 10, 'bold'),
                              fg="#b0b0b0", bg="#222e49")
        preview_label.pack(anchor="nw", pady=(0, 10))

        self.Lable_video_image = Label(right_frame, image=self.video_image, anchor="center",
                                       bg="#222e49", relief="solid", bd=1)
        self.Lable_video_image.pack()

        # 调整布局
        frame_main.columnconfigure(0, weight=1)
        frame_main.columnconfigure(1, weight=1)

        # ========== 关于标签 ==========
        frame_about = Frame(main_notebook, padding=(20, 20), style='TFrame')
        frame_about.pack(fill="both", expand=True)

        about_text = Label(frame_about, text=self.about_info, font=('微软雅黑', 11),
                           fg="#e0e0e0", bg="#222e49", justify="left", wraplength=700)
        about_text.pack(anchor="w", pady=(0, 20))

        about_buttons_frame = Frame(frame_about, style='TFrame')
        about_buttons_frame.pack(anchor="w", pady=10)

        def ABOUT_open_github():
            open_new_tab(r'https://github.com/YourClassmateChen/PhiWallpaper')

        def ABOUT_open_bilibili():
            open_new_tab(r'https://space.bilibili.com/1996208073')

        def ABOUT_open_blog():
            open_new_tab(r'http://106.53.213.36/')

        def ABOUT_open_guide():
            open_new_tab(r'http://106.53.213.36/信息技术の教程/PhiWallpaper使用指南')

        # 次级按钮
        btn_github = TButton(about_buttons_frame, text="项目地址", command=ABOUT_open_github,
                             style='Secondary.TButton')
        btn_github.pack(side="left", padx=(0, 10))

        btn_bilibili = TButton(about_buttons_frame, text="bilibili主页", command=ABOUT_open_bilibili,
                               style='Secondary.TButton')
        btn_bilibili.pack(side="left", padx=(0, 10))

        btn_blog = TButton(about_buttons_frame, text="个人博客", command=ABOUT_open_blog,
                           style='Secondary.TButton')
        btn_blog.pack(side="left", padx=(0, 10))

        btn_guide = TButton(about_buttons_frame, text="使用指南", command=ABOUT_open_guide,
                            style='Secondary.TButton')
        btn_guide.pack(side="left")

        # ========== 设置标签 ==========
        frame_set = Frame(main_notebook, padding=(20, 20), style='TFrame')
        frame_set.pack(fill="both", expand=True)

        settings_frame = Frame(frame_set, style='TFrame')
        settings_frame.pack(anchor="w", pady=(0, 20))

        # 开机自启
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

        # 修改壁纸
        def SET_change_wallpaper():
            path = filedialog.askopenfilename(filetypes=[("视频文件", "*.mp4")], title="PhiWallpaper")
            if not path:
                return
            else:
                with open(self.path_build(r"lib\path_video.txt"), "w", encoding="utf-8") as f:
                    f.write(path)
                messagebox.showinfo("PhiWallpaper", "动态壁纸修改成功!请点击确认生效")
                self.reread_video_path()
                self.video_image = self.toImage(self.path_video)
                self.Lable_video_image.configure(image=self.video_image)
                # 更新背景图
                self.bg_image = self.create_blurred_background(self.path_video, 800, 500)
                bg_label.configure(image=self.bg_image)
                if self.is_playing is True:
                    self.StopPlay()
                    while self.is_program_running("ffplay.exe"):
                        pass
                    self.PlayWallpaper()
                elif self.is_playing is False:
                    pass
                return

        # 设置项：开机自启
        auto_start_row = Frame(settings_frame, style='TFrame')
        auto_start_row.pack(fill="x", pady=5)
        Label(auto_start_row, text="开机自启：", font=('微软雅黑', 10), bg="#222e49", fg="#e0e0e0").pack(side="left")
        btn_autostart = TButton(auto_start_row, text="设置/取消", command=SET_start,
                                style='Secondary.TButton')
        btn_autostart.pack(side="left", padx=10)

        # 设置项：修改壁纸
        change_wallpaper_row = Frame(settings_frame, style='TFrame')
        change_wallpaper_row.pack(fill="x", pady=5)
        Label(change_wallpaper_row, text="动态壁纸：", font=('微软雅黑', 10), bg="#222e49", fg="#e0e0e0").pack(side="left")
        btn_change = TButton(change_wallpaper_row, text="选择视频文件", command=SET_change_wallpaper,
                             style='Modern.TButton')
        btn_change.pack(side="left", padx=10)

        # 提示
        note_label = Label(frame_set, text="提示：修改壁纸后需要重新开启壁纸才能生效。",
                           font=('微软雅黑', 9), fg="#b0b0b0", bg="#222e49")
        note_label.pack(anchor="w", pady=(10, 0))

        # 将三个页面添加到Notebook
        main_notebook.add(frame_main, text="主页")
        main_notebook.add(frame_about, text="关于")
        main_notebook.add(frame_set, text="设置")

        main_notebook.select(frame_main)

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
