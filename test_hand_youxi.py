import cv2
import time
from get_screen import get_screen
from detector import CardDetector


def main():
    # 1. 初始化识别器
    # 确保你的 templates 文件夹路径正确
    det = CardDetector("templates")

    print("--- 🚀 够级助手：实时手牌识别测试 ---")
    print("提示：请确保游戏窗口可见（可以被遮挡，但不能最小化）")
    print("提示：按下 'q' 键退出程序")

    while True:
        # 2. 获取实时截图 (已经由 get_screen 处理好了裁剪和颜色)
        frame = get_screen("微乐够级")

        if frame is None:
            print("\r⚠️ 未能找到窗口，请检查游戏是否运行...", end="")
            time.sleep(1)
            continue

        # 3. 调用识别逻辑
        # debug=True 会返回识别后的可视化画面 (debug_canvas)
        # 注意：如果识别不到牌，请去 detector.py 修改 rx, ry, rw, rh 比例
        results, debug_canvas = det.detect_my_hands(frame, debug=True)

        # 4. 控制台实时打印手牌字典
        # 使用 \r 实现原地刷新，不刷屏
        print(f"\r当前手牌: {results}          ", end="")

        # 5. 显示识别结果窗口
        # 你在这个窗口里看绿色的框有没有正好套在牌的数字上
        cv2.imshow("Recognition Debug (Press 'q' to Quit)", debug_canvas)

        # 6. 退出逻辑
        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()
    print("\n测试已结束。")


if __name__ == "__main__":
    main()