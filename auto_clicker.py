# DesktopAutoClicker 【定制版】- 无OpenCV依赖 | 纯PIL+numpy实现
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import time
import os
import keyboard
from PIL import ImageGrab, Image
import numpy as np
import pyautogui

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("DesktopAutoClicker 【定制版】✨ | 作者：weekstarR25")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        self.watermark = "【weekstarR25 定制版】"
        self.target_images = []
        self.is_running = False
        self.create_widgets()
        self.setup_hotkeys()
        self.log(f"✅ 程序启动成功 | {self.watermark}")
        self.log("💡 操作指南：截图目标区域 → 添加图片 → 设置参数 → 按F6开始")

    def create_widgets(self):
        tk.Label(self.root, text=self.watermark, fg="blue", font=("Arial", 10, "bold")).pack(pady=5)
        frame_list = tk.Frame(self.root); frame_list.pack(fill="x", padx=10, pady=5)
        tk.Label(frame_list, text="🎯 已添加目标图片:").pack(anchor="w")
        self.listbox = tk.Listbox(frame_list, height=6); self.listbox.pack(fill="x", pady=5)
        frame_btn = tk.Frame(self.root); frame_btn.pack(fill="x", padx=10)
        tk.Button(frame_btn, text="➕ 添加图片", command=self.add_image, width=15).pack(side="left", padx=2)
        tk.Button(frame_btn, text="➖ 删除选中", command=self.remove_image, width=15).pack(side="left", padx=2)
        tk.Button(frame_btn, text="🧹 清空列表", command=self.clear_list, width=15).pack(side="left", padx=2)
        frame_param = tk.Frame(self.root); frame_param.pack(fill="x", padx=10, pady=10)
        tk.Label(frame_param, text="⏱️ 点击间隔(秒):").pack(anchor="w")
        self.interval_var = tk.StringVar(value="1.0")
        tk.Entry(frame_param, textvariable=self.interval_var, width=10).pack(anchor="w", pady=2)
        tk.Label(frame_param, text="🔄 循环次数 (0=无限):").pack(anchor="w")
        self.loop_var = tk.StringVar(value="0")
        tk.Entry(frame_param, textvariable=self.loop_var, width=10).pack(anchor="w", pady=2)
        self.status_label = tk.Label(self.root, text="⏹️ 状态：空闲中", fg="gray", font=("Arial", 10))
        self.status_label.pack(pady=5)
        tk.Label(self.root, text="📜 运行日志:").pack(anchor="w", padx=10)
        self.log_text = scrolledtext.ScrolledText(self.root, height=12, state="disabled")
        self.log_text.pack(fill="both", padx=10, pady=5)
        tk.Label(self.root, text="⌨️ 快捷键：F6=开始 | F7=停止", fg="darkgreen", font=("Arial", 9)).pack(pady=3)

    def log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see("end"); self.log_text.config(state="disabled")

    def add_image(self):
        path = filedialog.askopenfilename(filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp")])
        if path and os.path.exists(path):
            self.target_images.append(path)
            self.listbox.insert("end", os.path.basename(path))
            self.log(f"✅ 已添加: {os.path.basename(path)}")

    def remove_image(self):
        sel = self.listbox.curselection()
        if sel: del self.target_images[sel[0]]; self.listbox.delete(sel); self.log("🗑️ 已删除选中图片")

    def clear_list(self):
        self.listbox.delete(0, "end"); self.target_images = []; self.log("🧹 已清空图片列表")

    def setup_hotkeys(self):
        keyboard.add_hotkey('f6', self.start_clicking)
        keyboard.add_hotkey('f7', self.stop_clicking)

    def find_image_pil(self, template_path):
        try:
            screen = ImageGrab.grab().convert('L'); screen_gray = np.array(screen)
            tmpl = Image.open(template_path).convert('L'); tmpl_np = np.array(tmpl)
            h, w = tmpl_np.shape
            if h > screen_gray.shape[0] or w > screen_gray.shape[1]: return None
            best_score, best_loc = -1, None
            step = max(1, w // 4)
            for y in range(0, screen_gray.shape[0] - h + 1, step):
                for x in range(0, screen_gray.shape[1] - w + 1, step):
                    roi = screen_gray[y:y+h, x:x+w]
                    if roi.shape != tmpl_np.shape: continue
                    roi_norm = (roi - roi.mean()) / (roi.std() + 1e-8)
                    tmpl_norm = (tmpl_np - tmpl_np.mean()) / (tmpl_np.std() + 1e-8)
                    score = np.mean(roi_norm * tmpl_norm)
                    if score > best_score and score > 0.75:
                        best_score, best_loc = score, (x, y)
            if best_loc:
                cx, cy = best_loc[0] + w//2, best_loc[1] + h//2
                self.log(f"🔍 找到 '{os.path.basename(template_path)}' | 匹配度:{best_score:.0%} | 位置:({cx},{cy})")
                return cx, cy
            return None
        except Exception as e:
            self.log(f"❌ 匹配错误: {str(e)}"); return None

    def click_loop(self):
        self.current_loop = 0
        max_loop = int(self.loop_var.get()) if self.loop_var.get().isdigit() else 0
        while self.is_running:
            if max_loop > 0 and self.current_loop >= max_loop: break
            for img_path in self.target_images:
                if not self.is_running: break
                pos = self.find_image_pil(img_path)
                if pos:
                    pyautogui.click(pos[0], pos[1]); self.log(f"🖱️ 已点击 | 间隔 {self.interval}s"); break
            self.current_loop += 1
            self.status_label.config(text=f"▶️ 运行中 | 循环:{self.current_loop}/{max_loop if max_loop>0 else '∞'}", fg="green")
            time.sleep(float(self.interval_var.get()) if self.interval_var.get().replace('.','',1).isdigit() else 1.0)
        self.is_running = False; self.status_label.config(text="⏹️ 状态：已停止", fg="gray"); self.log("⏹️ 任务已停止")

    def start_clicking(self):
        if not self.is_running:
            if not self.target_images: messagebox.showwarning("提示", "请先添加目标图片！"); return
            try:
                self.interval = float(self.interval_var.get())
                if self.interval < 0.5: self.interval = 0.5; self.interval_var.set("0.5")
            except: self.interval = 1.0
            self.is_running = True
            self.log(f"\n🚀 任务启动 | {self.watermark}")
            self.log(f"⏱️ 间隔: {self.interval}s | 循环: {'无限' if self.loop_var.get()=='0' else self.loop_var.get()}")
            threading.Thread(target=self.click_loop, daemon=True).start()

    def stop_clicking(self):
        if self.is_running: self.is_running = False; self.log("🛑 收到停止指令...")

    def on_closing(self):
        self.stop_clicking(); self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
