import cv2
from detector import CardDetector


def main():
    print("--- 🚀 初始化视觉识别引擎 ---")
    det = CardDetector("templates")

    image_path = "test_window_capture6.png"
    raw_frame = cv2.imread(image_path)

    if raw_frame is None:
        print(f"❌ 找不到图片: {image_path}")
        return

    print("--- 🔍 正在调用 detector.py 识别手牌 ---")
    # 核心：调用一行代码，开启 debug=True 接收字典和带框的图片
    results, debug_canvas = det.detect_my_hands(raw_frame, debug=True)

    print("\n✅ 最终识别手牌字典:")
    print("-" * 40)
    print(results)
    print("-" * 40)

    cv2.imshow("Module Test - Detect My Hands", debug_canvas)
    print("图片已弹出，按键盘任意键退出...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()