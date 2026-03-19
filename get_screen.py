import numpy as np
import win32gui, win32ui, win32con
import ctypes
import cv2
import config

# 强制开启 DPI 感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()

# --- 已经校准好的参数 ---
TOP_CROP = 50


def get_screen(window_name="微乐够级"):
    hwnd = win32gui.FindWindow(None, window_name)
    if not hwnd:
        # 模糊匹配逻辑
        hwnds = []
        win32gui.EnumWindows(lambda h, hs: hs.append(h) if (
                    win32gui.IsWindowVisible(h) and window_name in win32gui.GetWindowText(h)) else None, hwnds)
        if hwnds: hwnd = hwnds[0]

    if not hwnd: return None

    # 1. 获取窗口整体尺寸
    rect = win32gui.GetWindowRect(hwnd)
    w, h = rect[2] - rect[0], rect[3] - rect[1]

    # 2. 截图
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

    # 获取物理缩放比例
    bmp = saveBitMap.GetInfo()
    phys_w, phys_h = bmp['bmWidth'], bmp['bmHeight']
    scale = phys_w / w

    # 转换为 numpy 数组
    img = np.frombuffer(saveBitMap.GetBitmapBits(True), dtype='uint8')
    img.shape = (phys_h, phys_w, 4)

    # 释放资源
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    # 3. 物理裁剪 (根据校准好的 50 偏移量)
    offset_y = int(TOP_CROP * scale)
    # 裁剪掉标题栏并去掉 Alpha 通道
    frame = img[offset_y:, :, :3]

    if frame.size == 0: return None

    # 4. 颜色修复：将 BGRA 截取出的 BGR 重新校准为 OpenCV 标准 BGR
    # 因为 img[:, :, :3] 拿到的已经是 BGR 了，我们确保它不被二次颠倒
    frame = np.ascontiguousarray(frame)

    # 5. 强制缩放到基准尺寸 (1458x820)
    frame = cv2.resize(frame, (config.BASE_W, config.BASE_H))
    return frame


if __name__ == "__main__":
    print("🚀 正在检查最终截图效果（颜色与位置）...")
    while True:
        img = get_screen("微乐够级")
        if img is not None:
            cv2.imshow("Final Capture Check", img)

        if cv2.waitKey(1) == ord('q'):
            break
    cv2.destroyAllWindows()