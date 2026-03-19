import cv2
import numpy as np
import os
from config import BASE_W, BASE_H

class CardDetector:
    def __init__(self, template_dir="templates"):
        self.templates = {}
        self.ying_template = None
        self.min_gap = 20
        self._load_templates(template_dir)

    def _load_templates(self, path):
        if not os.path.exists(path): return
        for file in os.listdir(path):
            if not file.endswith('.png'): continue
            name = os.path.splitext(file)[0].upper()
            img = cv2.imread(os.path.join(path, file))
            if img is None: continue

            if name == "YING":
                self.ying_template = img
            else:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                self.templates[name] = thresh

    def _identify_joker(self, roi_bgr, pt, tw, th):
        """
        精确切片并判定颜色
        pt: 匹配点坐标 (x, y)
        tw, th: 模板的宽高
        """
        # 核心修复：matchTemplate 的坐标就是左上角，直接切即可
        # 但要确保不越界
        ex, ey = pt[0] + tw, pt[1] + th
        patch = roi_bgr[pt[1]:ey, pt[0]:ex]
        
        if patch.size == 0: return "blackJOKER"

        # 计算均值
        b_avg = np.mean(patch[:, :, 0])
        g_avg = np.mean(patch[:, :, 1])
        r_avg = np.mean(patch[:, :, 2])
        
        # 降低红王门槛到 +20，增加对暗红色的兼容
        if r_avg > b_avg + 20 and r_avg > g_avg + 20:
            return "redJOKER"
        return "blackJOKER"

    def detect_player_cards(self, frame, zone_ratio):
        std_frame = cv2.resize(frame, (BASE_W, BASE_H))
        rx, ry, rw, rh = zone_ratio
        x, y, w, h = int(rx*BASE_W), int(ry*BASE_H), int(rw*BASE_W), int(rh*BASE_H)
        
        roi_bgr = std_frame[y:y+h, x:x+w]
        roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        _, roi_bin = cv2.threshold(roi_gray, 150, 255, cv2.THRESH_BINARY)
        
        found = {}

        for name, temp in self.templates.items():
            res = cv2.matchTemplate(roi_bin, temp, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= 0.75)
            
            # 这里的 pt 是 (x, y)
            pts = sorted(zip(*loc[::-1]), key=lambda p: p[0])
            
            last_x = -100
            for pt in pts:
                if abs(pt[0] - last_x) >= self.min_gap:
                    if name == "JOKER":
                        th, tw = temp.shape[:2]
                        # 传入坐标和宽高进行精准鉴定
                        real_name = self._identify_joker(roi_bgr, pt, tw, th)
                        found[real_name] = found.get(real_name, 0) + 1
                    else:
                        display_name = "10" if name == "0" else name
                        found[display_name] = found.get(display_name, 0) + 1
                    last_x = pt[0]

        # 鹰的处理保持不变
        if self.ying_template is not None:
            res_y = cv2.matchTemplate(roi_bgr, self.ying_template, cv2.TM_CCOEFF_NORMED)
            loc_y = np.where(res_y >= 0.7)
            pts_y = sorted(zip(*loc_y[::-1]), key=lambda p: p[0])
            last_x_y = -100
            for pt in pts_y:
                if abs(pt[0] - last_x_y) >= self.min_gap:
                    found["YING"] = found.get("YING", 0) + 1
                    last_x_y = pt[0]
                    
        return found

    def detect_my_hands(self, raw_frame, debug=False):
        import cv2
        import numpy as np
        import config

        # 1. 区域截取与高质量缩放
        BASE_W, BASE_H = getattr(config, 'BASE_W', 1458), getattr(config, 'BASE_H', 820)
        # 【关键修改】：使用 INTER_LANCZOS4 保证拉伸后的数字边缘依然锐利
        std_frame = cv2.resize(raw_frame, (BASE_W, BASE_H), interpolation=cv2.INTER_LANCZOS4)

        rx, ry, rw, rh = 0.0, 0.52, 1.0, 0.45
        x, y, w, h = int(rx * BASE_W), int(ry * BASE_H), int(rw * BASE_W), int(rh * BASE_H)
        roi_raw = std_frame[y:y + h, x:x + w]

        debug_canvas = roi_raw.copy() if debug else None

        # 预生成缩放图
        roi_110 = cv2.resize(roi_raw, (int(w / 1.1), int(h / 1.1)), interpolation=cv2.INTER_LANCZOS4)
        roi_125 = cv2.resize(roi_raw, (int(w / 1.25), int(h / 1.25)), interpolation=cv2.INTER_LANCZOS4)

        results = {}
        # 【关键修改】：间距压到 10 像素，专门对付叠在一起的 4, 5, 6
        HAND_MIN_GAP = 10

        for name, temp in self.templates.items():
            if name == "YING":
                continue

            is_joker = (name == "JOKER")
            scale = 1.25 if is_joker else 1.1
            work_roi = roi_125 if is_joker else roi_110

            # 【关键修改】：全员降门槛。只要像数字，统统算进来
            current_threshold = 0.65 if not is_joker else 0.70

            best_loc = None
            # 增加一个更宽的二值化搜索范围
            for thresh_val in [140, 125, 155, 110]:
                work_gray = cv2.cvtColor(work_roi, cv2.COLOR_BGR2GRAY)
                _, work_bin = cv2.threshold(work_gray, thresh_val, 255, cv2.THRESH_BINARY)

                res = cv2.matchTemplate(work_bin, temp, cv2.TM_CCOEFF_NORMED)
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

                        if debug:
                            color = (0, 255, 0)
                            if is_joker:
                                display_name = self._identify_joker(work_roi, pt, tw, th)
                                color = (0, 0, 255) if "red" in display_name else (255, 0, 255)

                            draw_x = int(pt[0] * scale)
                            draw_y = int(pt[1] * scale)
                            cv2.rectangle(debug_canvas, (draw_x, draw_y),
                                          (draw_x + int(tw * scale), draw_y + int(th * scale)), color, 2)
                            cv2.putText(debug_canvas, display_name, (draw_x, draw_y - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                        results[display_name] = results.get(display_name, 0) + 1
                        last_x = pt[0]

                        # 如果开启了调试模式，把框画在 canvas 上
                        if debug:
                            draw_x = int(pt[0] * scale)
                            draw_y = int(pt[1] * scale)
                            draw_tw = int(tw * scale)
                            draw_th = int(th * scale)
                            cv2.rectangle(debug_canvas, (draw_x, draw_y),
                                          (draw_x + draw_tw, draw_y + draw_th), color, 2)
                            cv2.putText(debug_canvas, display_name, (draw_x, draw_y - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 3. 鹰(龙)牌色彩特征识别
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
                if 2000 < area < 25000 and x_gold < (w * 0.3) and y_gold < (h * 0.5):
                    if w_gold > 65 and h_gold > 60 and aspect_ratio > 0.65:

                        if w_gold > 115:
                            count = 1 + round((w_gold - 90) / 40)
                            count = max(2, int(count))
                        else:
                            count = 1

                        results["YING"] = results.get("YING", 0) + count

                        if debug:
                            cv2.rectangle(debug_canvas, (x_gold, y_gold), (x_gold + w_gold, y_gold + h_gold),
                                          (0, 255, 255), 2)
                            cv2.putText(debug_canvas, f"YING x{count}", (x_gold, y_gold - 5), cv2.FONT_HERSHEY_SIMPLEX,
                                        0.6, (0, 255, 255), 2)

        if debug:
            return results, debug_canvas
        return (results, debug_canvas) if debug else results
    def visualize_all(self, frame, player_zones):
        canvas = cv2.resize(frame, (BASE_W, BASE_H))
        for z_name, ratio in player_zones.items():
            cards = self.detect_player_cards(canvas, ratio)
            rx, ry, rw, rh = ratio
            ix, iy, iw, ih = int(rx*BASE_W), int(ry*BASE_H), int(rw*BASE_W), int(rh*BASE_H)
            
            clr = (0, 255, 0) if cards else (0, 0, 255)
            cv2.rectangle(canvas, (ix, iy), (ix+iw, iy+ih), clr, 2)
            cv2.putText(canvas, z_name, (ix, iy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
            
            if cards:
                # 强制排序，确保 redJOKER/blackJOKER 显示在前面
                sorted_items = sorted(cards.items(), key=lambda x: ("JOKER" not in x[0], x[0]))
                txt = ", ".join([f"{k}x{v}" for k, v in sorted_items])
                cv2.putText(canvas, txt, (ix, iy+ih+22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return canvas