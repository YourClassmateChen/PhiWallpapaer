# PhiWallpapaer
![](https://github.com/YourClassmateChen/PhiWallpapaer/blob/main/lib/small_ico.png)  
**PhiWallpaper——基于Python的动态壁纸软件**<br>
`tip : 程序目前还在测试阶段`<br>
对视频有兼容要求 要求如下：<br>
&emsp;&nbsp;&nbsp;可用帧率&nbsp;&nbsp;&nbsp;60fps<br>
&emsp;可用分辨率&nbsp;1920x1080<br>
目前只有满足以上两个要求的视频可以作为壁纸<br>
建议直接下载发行版中的压缩包<br>
当前已适配Windows11-24H2的更新<br>
之前版本的机型可以查看v0.1.0-gamma发行版<br>
本程序使用系统托盘内的图标控制<br>
启动程序后请查看系统托盘

----------------
## 关于PhiWallpaper
使用opencv创建视频窗体<br>
使用win32嵌入桌面<br>
基于0x052C消息的动态壁纸软件<br>
原理：<br>
&emsp;1.发送0x052C消息创建WorkerW窗口<br>
&emsp;2.找到Progman窗口<br>
&emsp;3.找到Progman下的WorkerW子窗口<br>
&emsp;4.设置WorkerW为视频窗口的父窗口<br>

----------------
## 存在的问题
easygui的窗体有时候使用不灵，关于界面出现相关问题。<br>
重新打开壁纸时显示异常，最终使用了仅能退出程序的妥协办法。<br>
选择动态壁纸/静态壁纸的界面中只能使用GUI选择，路径等方式无效。

----------------
## 关于测试中的难题
目前测试中关于嵌入窗体的部分很完善，但是视频处理部分问题很大。<br>
首先是测试用电脑为1920x1080分辨率，在其他分辨率的电脑上可能显示异常。<br>
然后是opencv处理时的内部问题，opencv每一帧下对窗体的调整都需要时间，会导致窗口播放帧的速度不定，目前只有60fps可以接近原视频速率。<br>
之后是用非1920x1080分辨率时的兼容，程序里原先是有兼容的，机制参考Windows壁纸中的“填充”，不过后来出现问题删除了。<br>
其实这些都是opencv库的问题，我后面可能单独出个程序，试一下FFmpeg作为视频窗体。<br>

