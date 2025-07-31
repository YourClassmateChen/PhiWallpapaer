from time import sleep
from numpy import zeros
from numpy import uint8
from ctypes import windll
from threading import Thread
from PIL.Image import open as op
from win32print import GetDeviceCaps
from win32api import GetSystemMetrics
from os import system
# easygui
from easygui import msgbox
from easygui import buttonbox
# pystray
from pystray import Icon
from pystray import MenuItem
# tkinter
from tkinter import Tk
from tkinter import filedialog
# win32gui
from win32gui import GetDC
from win32gui import SetParent
from win32gui import ShowWindow
from win32gui import FindWindow
from win32gui import EnumWindows
from win32gui import GetClassName
from win32gui import SetWindowPos
from win32gui import SetWindowLong
from win32gui import IsWindowVisible
from win32gui import EnumChildWindows
from win32gui import SendMessageTimeout
# win32con
from win32con import HWND_TOP
from win32con import WS_CHILD
from win32con import GWL_STYLE
from win32con import SWP_NOMOVE
from win32con import SWP_NOSIZE
from win32con import WS_VISIBLE
from win32con import DESKTOPVERTRES
from win32con import DESKTOPHORZRES
from win32con import SWP_SHOWWINDOW
from win32con import SW_SHOWMAXIMIZED
from win32con import SW_SHOWMINIMIZED
# cv2
from cv2 import resize
from cv2 import imshow
from cv2 import waitKey
from cv2 import cvtColor
from cv2 import INTER_AREA
from cv2 import moveWindow
from cv2 import namedWindow
from cv2 import INTER_LINEAR
from cv2 import resizeWindow
from cv2 import VideoCapture
from cv2 import CAP_PROP_FPS
from cv2 import COLOR_BGR2RGB
from cv2 import WINDOW_NORMAL
from cv2 import setWindowProperty
from cv2 import WINDOW_FULLSCREEN
from cv2 import WND_PROP_FULLSCREEN
from cv2 import CAP_PROP_FRAME_WIDTH
from cv2 import CAP_PROP_FRAME_HEIGHT


def read_all() -> None:
    """
    读取所有文件信息,包括可图片类型,动态壁纸和壁纸的路径
    :return: 无
    """
    global pic_type
    with open("./lib/pic_type", "r", encoding="utf-8") as f:
        pic_type = f.read()
    global path_video
    with open("./lib/path_video", "r") as f:
        path_video = f.read()
    global path_pic
    with open("./lib/path_pic", "r") as f:
        path_pic = f.read()


read_all()

just_open = 0  # 控制壁纸打开更流畅
opening = 0  # 控制是否处于打开状态(真假一致)
open_times = 0  # 视频流窗口次序(打开次数)
close_symbol = 1  # 关闭信号,为真时播放,为假时停止播放
GUI_title = "PhiWallpaper"  # easygui窗口title
GUI_OK = "确认"  # easygui中msgbox的OK键替换字符


def cv2_window_name_updata() -> None:
    """
    更新cv2的窗口名,使视频流推入新的窗口
    :return: 无
    """
    global cv2_window_name
    cv2_window_name = "Video_Window_" + str(open_times)


cv2_window_name_updata()


def write_into(text, file_name) -> None:
    """
    将文本写入指定文件
    :param text: 文本
    :param file_name: 文件路径(请使用相对路径)
    :return: 无
    """
    with open(file_name, "w") as f:
        f.write(text)


def get_file_path_pic() -> str:
    """
    打开寻找静态壁纸文件GUI并返回所选文件的绝对路径
    :return: 文件的绝对路径
    """
    return filedialog.askopenfilename(title="请打开文件", filetypes=[("所有文件", pic_type)])


def get_file_path_video() -> str:
    """
    打开寻找动态壁纸文件GUI并返回所选文件的绝对路径
    :return: 文件的绝对路径
    """
    return filedialog.askopenfilename(title="请打开文件", filetypes=[("所有文件", "*.mp4")])


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
            if class_name == "WorkerW" and IsWindowVisible(hwnd):
                # 枚举 WorkerW 的子窗口
                child_hwnd_list = []
                EnumChildWindows(hwnd, lambda child_hwnd, param: param.append(child_hwnd), child_hwnd_list)

                contains_shelldll_defview = False
                for child_hwnd in child_hwnd_list:
                    child_class_name = GetClassName(child_hwnd)
                    if child_class_name == "SHELLDLL_DefView":
                        contains_shelldll_defview = True
                        break

                if not contains_shelldll_defview:
                    return hwnd
        except Exception as e:
            print(f"Error accessing window {hwnd}: {e}")

    return None


def set_parent(hwnd_child, hwnd_new_parent) -> None:
    """
    设置窗口子父级关系
    :param hwnd_child: 子窗口
    :param hwnd_new_parent: 父窗口
    :return: 无
    """
    print(f"TRY:Set parent of {hwnd_child} to {hwnd_new_parent}")
    # 设置窗口父级（需要管理员权限）
    try:
        SetParent(hwnd_child, hwnd_new_parent)
        SetWindowLong(hwnd_child, GWL_STYLE, WS_CHILD | WS_VISIBLE)
        SetWindowPos(hwnd_child, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        print(f"Set parent of {hwnd_child} to {hwnd_new_parent}")
    except Exception as e:
        print(f"Failed to set parent: {e}")


def cv2_play(plan) -> None:
    """
    播放视频的核心部分
    :param plan: 视频路径
    :return: 无
    """
    global just_open
    video_cap = VideoCapture(plan)
    cap_total_fps = video_cap.get(CAP_PROP_FPS)
    hDC = GetDC(0)
    screen_width = GetDeviceCaps(hDC, DESKTOPHORZRES)
    screen_height = GetDeviceCaps(hDC, DESKTOPVERTRES)
    for i in range(1000 * int(cap_total_fps)):
        if not close_symbol:
            break

        ret, frame = video_cap.read()
        if not ret:
            break

        # 获取帧的原始大小
        original_height, original_width, _ = frame.shape

        # 计算缩放比例
        x_ratio = screen_width / original_width
        y_ratio = screen_height / original_height

        # 选择较大的缩放比例以确保帧覆盖整个屏幕
        ratio = max(x_ratio, y_ratio)

        # 计算新尺寸
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)

        # 调整帧大小
        resized_frame = resize(frame, (new_width, new_height), interpolation=INTER_AREA)

        # 创建一个空白的屏幕大小图像
        screen_frame = cvtColor(zeros((screen_height, screen_width, 3), dtype=uint8), COLOR_BGR2RGB)

        if new_height != screen_height:
            # 计算裁剪区域的起始和结束行
            start_row = (new_height - screen_height) // 2
            end_row = start_row + screen_height
            # 裁剪图像
            resized_frame = resized_frame[start_row:end_row, 0:screen_width]
        # 将调整大小后的帧放置在屏幕图像的相应位置
        # screen_frame[0:new_height, 0:new_width] = resized_frame[0:new_height, 0:new_width]
        screen_frame[0:screen_height, 0:screen_width] = resized_frame[0:screen_height, 0:screen_width]

        namedWindow(cv2_window_name, WINDOW_NORMAL)
        # video_cap.set(CAP_PROP_FRAME_WIDTH, 1920)
        # video_cap.set(CAP_PROP_FRAME_HEIGHT, 1080)
        setWindowProperty(cv2_window_name, WND_PROP_FULLSCREEN, WINDOW_FULLSCREEN)
        # resizeWindow(cv2_window_name, 1920, 1080)
        moveWindow(cv2_window_name, 0, 0)
        resizeWindow(cv2_window_name, screen_width, screen_height)

        imshow(cv2_window_name, screen_frame)
        if just_open == 1:
            ShowWindow(FindWindow(None, cv2_window_name), SW_SHOWMINIMIZED)
            just_open = 2
        if waitKey(1) & 0xFF == ord('q'):
            break


def play() -> None:
    """
    循环播放视频
    :return: 无
    """
    global close_symbol
    close_symbol = 1
    while close_symbol:
        cv2_play(path_video)
    exit_func()


def close_play() -> None:
    """
    停止播放
    :return: 无
    """
    global close_symbol
    close_symbol = 0


def exit_func() -> None:
    """
    最终退出(包括关闭系统托盘和WorkerW)
    :return: 无
    """
    hwnd_PM = FindWindow("Progman", "Program Manager")
    windll.user32.SystemParametersInfoW(20, 0, path_pic, 3)
    SendMessageTimeout(hwnd_PM, 0x052C, 0, None, 0, 0x03E8)


def start_thread() -> None:
    """
    启动线程,便于整理
    :return: 无
    """
    thread = Thread(target=play)
    thread.start()


def PlayWallpaer() -> None:
    """
    壁纸启动和放入桌面的核心部分
    :return: 无
    """
    global just_open
    start_thread()
    hwnd_PM = FindWindow("Progman", "Program Manager")
    SendMessageTimeout(hwnd_PM, 0x052C, 0, None, 0, 0x03E8)
    # 找到符合条件的 WorkerW 窗口
    worker_w_hwnd = False
    while not worker_w_hwnd:
        worker_w_hwnd = find_worker_w_without_shelldll_defview()
    if worker_w_hwnd:
        # 假设我们要更改的窗口句柄（这里你需要替换成你自己的窗口句柄）
        # 你可以使用 win32gui.FindWindow 或其他方法来获取你的窗口句柄
        your_window_hwnd = False
        while not your_window_hwnd:
            your_window_hwnd = FindWindow(None, cv2_window_name)  # 替换为你的窗口标题
        if your_window_hwnd:
            set_parent(your_window_hwnd, worker_w_hwnd)
            while just_open != 2:
                pass
            ShowWindow(FindWindow(None, cv2_window_name), SW_SHOWMAXIMIZED)
            just_open = 0
        else:
            msgbox("动态壁纸打开失败\n错误:找不到动态壁纸窗口", GUI_title, GUI_OK)
            MainWindow()
    else:
        msgbox("动态壁纸打开失败\n错误:找不到WorkerW窗口", GUI_title, GUI_OK)
        MainWindow()


def MainWallpaper() -> None:
    """
    控制壁纸打开关闭,是壁纸核心控制的对外接口
    :return: 无
    """
    global opening
    global open_times
    global just_open
    if not opening:
        just_open = 1
        opening = 1
        open_times += 1
        cv2_window_name_updata()
        PlayWallpaer()
    else:
        opening = 0
        close_play()
        windll.user32.SystemParametersInfoW(20, 0, path_pic, 3)


def MainChangeVideo() -> None:
    """
    修改动态壁纸
    :return: 无
    """
    global opening
    global open_times
    global just_open
    path = get_file_path_video()
    if path == "":
        pass
    else:
        write_into(path, "./lib/path_video")
        msgbox("动态壁纸修改成功!", GUI_title, GUI_OK)
        read_all()
        # close
        opening = 0
        close_play()
        windll.user32.SystemParametersInfoW(20, 0, path_pic, 3)
        # open
        just_open = 1
        opening = 1
        open_times += 1
        cv2_window_name_updata()
        PlayWallpaer()


def MainChangePic() -> None:
    """
    修改静态壁纸
    :return: 无
    """
    path = get_file_path_pic()
    if path == "":
        pass
    else:
        write_into(path, "./lib/path_pic")
        msgbox("静态壁纸修改成功!", GUI_title, GUI_OK)
        read_all()


def MainExit() -> None:
    """
    完全退出,退出的对外接口
    :return: 无
    """
    close_play()
    exit_func()
    icon.stop()


def AboutGUI() -> None:
    """
    关于界面
    :return: 无
    """
    about_input = buttonbox("""
    PhiWallpaper γ
    -呈阶梯状分布-
    2025.2.5 最后维护
    """, GUI_title,
                            ['联系作者:-呈阶梯状分布-', '作者个人网页'],
                            './lib/small_ico.png')
    print(about_input)
    if about_input == '联系作者:-呈阶梯状分布-':
        system('start https://space.bilibili.com/1996208073')
    elif about_input == '作者个人网页':
        system('start https://yourclassmatechen.github.io/')
    elif about_input == './lib/small_ico.png':
        msgbox('ヾ(≧ ▽ ≦)ゝ', GUI_title, GUI_OK)
        return
    else:
        return


if __name__ == "__main__":
    # 菜单栏与函数的设置
    menu = (MenuItem('打开/关闭动态壁纸', MainWallpaper),
            MenuItem('修改动态壁纸', MainChangeVideo),
            MenuItem('修改静态壁纸', MainChangePic),
            MenuItem('关于PhiWallpaper', AboutGUI),
            MenuItem('退出PhiWallpaper', MainExit))
    # 托盘图标的设置
    image = op("./lib/ico.jpg")
    # 托盘的设置
    icon = Icon("name", image, "PhiWallpaper", menu)
    # 托盘运行
    icon.run()
