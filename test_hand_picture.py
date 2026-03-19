import cv2
import numpy as np
import config
from detector import CardDetector


def test_visual_debug():
    det = CardDetector("templates")
    image_path = "test_window_capture1.png"
    raw_frame = cv2.imread(image_path)
    if raw_frame is None:
        print("❌ 找不到图片")
        return

    # 1. 区域截取
    BASE_W, BASE_H = config.BASE_W, config.BASE_H
    std_frame = cv2.resize(raw_frame, (BASE_W, BASE_H))
    rx, ry, rw, rh = 0.0, 0.52, 1.0, 0.45
    x, y, w, h = int(rx * BASE_W), int(ry * BASE_H), int(rw * BASE_W), int(rh * BASE_H)
    roi_raw = std_frame[y:y + h, x:x + w]

    debug_canvas = roi_raw.copy()

    # 预生成缩放图
    roi_110 = cv2.resize(roi_raw, (int(w / 1.1), int(h / 1.1)))
    roi_125 = cv2.resize(roi_raw, (int(w / 1.25), int(h / 1.25)))

    results = {}
    HAND_MIN_GAP = 20

    print("--- 🔍 开始常规牌面与大小王识别 ---")

    for name, temp in det.templates.items():
        if name == "YING":
            continue

        is_joker = (name == "JOKER")
        scale = 1.25 if is_joker else 1.1
        work_roi = roi_125 if is_joker else roi_110

        best_loc = None
        for thresh_val in [140, 120, 155, 100]:
            work_gray = cv2.cvtColor(work_roi, cv2.COLOR_BGR2GRAY)
            _, work_bin = cv2.threshold(work_gray, thresh_val, 255, cv2.THRESH_BINARY)

            res = cv2.matchTemplate(work_bin, temp, cv2.TM_CCOEFF_NORMED)
            current_threshold = 0.70 if is_joker else 0.72
            loc = np.where(res >= current_threshold)

            if len(loc[0]) > 0:
                best_loc = loc
                break

        if best_loc is not None:
            pts = sorted(zip(*best_loc[::-1]), key=lambda p: p[0])
            last_x = -100
            for pt in pts:
                if abs(pt[0] - last_x) >= (HAND_MIN_GAP / scale):
                    tw, th = temp.shape[1], temp.shape[0]
                    display_name = "10" if name == "0" else name
                    color = (0, 255, 0)

                    if is_joker:
                        display_name = det._identify_joker(work_roi, pt, tw, th)
                        color = (0, 0, 255) if "red" in display_name else (255, 0, 255)

                    draw_x = int(pt[0] * scale)
                    draw_y = int(pt[1] * scale)
                    draw_tw = int(tw * scale)
                    draw_th = int(th * scale)

                    cv2.rectangle(debug_canvas, (draw_x, draw_y),
                                  (draw_x + draw_tw, draw_y + draw_th), color, 2)
                    cv2.putText(debug_canvas, display_name, (draw_x, draw_y - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    results[display_name] = results.get(display_name, 0) + 1
                    last_x = pt[0]

    print("--- 🔍 启动鹰(龙)牌色彩特征识别 ---")

    hsv_roi = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2HSV)

    lower_gold = np.array([12, 130, 130])
    upper_gold = np.array([35, 255, 255])
    mask = cv2.inRange(hsv_roi, lower_gold, upper_gold)

    dilate_kernel = np.ones((10, 10), np.uint8)
    mask_clean = cv2.dilate(mask, dilate_kernel, iterations=2)

    mask_clean[0:35, :] = 0
    mask_clean[:, 0:35] = 0

    contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        x_gold, y_gold, w_gold, h_gold = cv2.boundingRect(cnt)

        if area > 150:
            aspect_ratio = w_gold / h_gold if h_gold > 0 else 0
            print(
                f"[Debug] 候选色块: x={x_gold}, y={y_gold}, 宽={w_gold}, 高={h_gold}, 比例={aspect_ratio:.2f}, 面积={area:.0f}")

            # 【核心修复】：面积提高到 2000 过滤小噪点。
            if 2000 < area < 25000 and x_gold < (w * 0.3) and y_gold < (h * 0.5):
                # 【终极防线】：宽必须大于 65，且长宽比必须 > 0.65，彻底秒杀细长的竖条反光！
                if w_gold > 65 and h_gold > 60 and aspect_ratio > 0.65:

                    if w_gold > 115:
                        count = 1 + round((w_gold - 90) / 40)
                        count = max(2, int(count))
                    else:
                        count = 1

                    results["YING"] = results.get("YING", 0) + count

                    cv2.rectangle(debug_canvas, (x_gold, y_gold), (x_gold + w_gold, y_gold + h_gold), (0, 255, 255), 2)
                    cv2.putText(debug_canvas, f"YING x{count}", (x_gold, y_gold - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (0, 255, 255), 2)
                    print(f"✅ 成功锁定 {count} 张鹰(龙)牌！")

    print(f"\n最终识别统计: {results}")
    cv2.imshow("Hand Debug", debug_canvas)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_visual_debug()