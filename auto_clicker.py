# auto_clicker.py （保存为此文件名！）
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import cv2
import numpy as np
import time
import threading
import os
import queue
from PIL import Image, ImageTk

# 尝试导入keyboard（全局快捷键）
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎯 桌面自动点击工具 v3.1 (精简无OCR版)")
        self.root.geometry("800x600")
        self.root.minsize(750, 550)
        
        # 核心变量
        self.target_images = []
        self.interval_time = tk.DoubleVar(value=1.0)
        self.loop_count = tk.IntVar(value=5)
        self.is_running = False
        self.stop_flag = False
        self.click_type = tk.StringVar(value="single")
        self.infinite_loop = tk.BooleanVar(value=False)
        self.hotkey_enabled = tk.BooleanVar(value=False)
        self.start_hotkey = "F6"
        self.stop_hotkey = "F7"
        self.log_queue = queue.Queue()
        self.hotkey_registered = False
        
        # 初始化
        self.setup_hotkeys()
        self.create_widgets()
        self.process_log_queue()
    
    def setup_hotkeys(self):
        if KEYBOARD_AVAILABLE and hasattr(keyboard, 'add_hotkey'):
            try:
                keyboard.add_hotkey(self.start_hotkey.lower(), self.trigger_start)
                keyboard.add_hotkey(self.stop_hotkey.lower(), self.trigger_stop)
                self.hotkey_registered = True
            except: pass
    
    def trigger_start(self): 
        if not self.is_running: self.root.after(0, self.start_clicking_safe)
    def trigger_stop(self): 
        if self.is_running: self.root.after(0, self.stop_clicking)
    
    def create_widgets(self):
        # 顶部状态栏
        status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(status_bar, text="状态:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.hotkey_label = ttk.Label(status_bar, text="⌨️ 快捷键: F6开始 / F7停止", foreground="green")
        self.hotkey_label.pack(side=tk.LEFT, padx=10)
        
        # 主容器
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)
        
        # ====== 图片管理区（唯一目标模式）======
        img_frame = ttk.LabelFrame(main, text="🖼️ 目标图片管理（截图添加）", padding="10")
        img_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 列表
        list_f = ttk.Frame(img_frame)
        list_f.pack(fill=tk.BOTH, expand=True, pady=5)
        self.img_list = tk.Listbox(list_f, height=6)
        sb = ttk.Scrollbar(list_f, orient=tk.VERTICAL, command=self.img_list.yview)
        self.img_list.config(yscrollcommand=sb.set)
        self.img_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮
        btn_f = ttk.Frame(img_frame)
        btn_f.pack(fill=tk.X, pady=5)
        ttk.Button(btn_f, text="➕ 添加图片", command=self.add_image, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="➖ 删除选中", command=self.del_image, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="🗑️ 清空列表", command=self.clear_images, width=12).pack(side=tk.LEFT, padx=2)
        
        # ====== 高级设置 ======
        set_frame = ttk.LabelFrame(main, text="⚙️ 点击设置", padding="10")
        set_frame.pack(fill=tk.X, pady=5)
        
        # 点击类型
        click_f = ttk.Frame(set_frame)
        click_f.pack(fill=tk.X, pady=3)
        ttk.Label(click_f, text="🖱️ 点击方式:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(click_f, text="单击", variable=self.click_type, value="single").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(click_f, text="双击", variable=self.click_type, value="double").pack(side=tk.LEFT, padx=5)
        
        # 循环设置
        loop_f = ttk.Frame(set_frame)
        loop_f.pack(fill=tk.X, pady=3)
        ttk.Label(loop_f, text="⏱️ 间隔(秒):").pack(side=tk.LEFT, padx=5)
        ttk.Spinbox(loop_f, from_=0.1, to=60, increment=0.1, textvariable=self.interval_time, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(loop_f, text="🔄 循环次数:").pack(side=tk.LEFT, padx=15)
        ttk.Spinbox(loop_f, from_=1, to=9999, textvariable=self.loop_count, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(loop_f, text="♾️ 无限循环", variable=self.infinite_loop, 
                       command=lambda: self.loop_count_spin.config(state=tk.DISABLED if self.infinite_loop.get() else tk.NORMAL)).pack(side=tk.LEFT, padx=15)
        self.loop_count_spin = ttk.Spinbox(loop_f, from_=1, to=9999, textvariable=self.loop_count, width=6)
        self.loop_count_spin.pack(side=tk.LEFT, padx=2)
        
        # ====== 控制按钮 ======
        ctrl_f = ttk.Frame(main)
        ctrl_f.pack(pady=15)
        self.start_btn = ttk.Button(ctrl_f, text="▶️ 开始执行 (F6)", command=self.start_clicking_safe, width=18, style="Accent.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=10)
        self.stop_btn = ttk.Button(ctrl_f, text="⏹️ 停止 (F7)", command=self.stop_clicking, width=18, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        # ====== 日志区 ======
        log_f = ttk.LabelFrame(main, text="📋 运行日志", padding="5")
        log_f.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_txt = tk.Text(log_f, height=10, state=tk.DISABLED, wrap=tk.WORD, font=("Consolas", 9))
        sb2 = ttk.Scrollbar(log_f, orient=tk.VERTICAL, command=self.log_txt.yview)
        self.log_txt.configure(yscrollcommand=sb2.set)
        self.log_txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 底部提示
        hint = ttk.Frame(main)
        hint.pack(fill=tk.X, pady=(10,0))
        ttk.Label(hint, text="💡 提示：截图目标区域 → 添加图片 → 设置参数 → 按F6开始 | 首次测试建议循环=2, 间隔=3秒", 
                 foreground="#1a5fb4", font=("Arial", 9)).pack()
        
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
    
    # ====== 核心功能（精简版仅保留图片识别）======
    def add_image(self):
        paths = filedialog.askopenfilenames(filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp")])
        for p in paths:
            if p not in self.target_images:
                self.target_images.append(p)
                self.img_list.insert(tk.END, os.path.basename(p))
        if paths: self.add_log(f"✅ 添加 {len(paths)} 个图片目标")
    
    def del_image(self):
        sel = self.img_list.curselection()
        if sel: 
            idx = sel[0]
            self.target_images.pop(idx)
            self.img_list.delete(idx)
            self.add_log("➖ 已删除选中图片")
        else: messagebox.showinfo("提示", "请先选择图片")
    
    def clear_images(self):
        if messagebox.askyesno("确认", "清空所有图片?"): 
            self.target_images.clear()
            self.img_list.delete(0, tk.END)
            self.add_log("🗑️ 已清空图片列表")
    
    def find_image(self):
        try:
            screen = pyautogui.screenshot()
            screen_np = np.array(screen)
            screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)
            
            for i, path in enumerate(self.target_images):
                if not os.path.exists(path): continue
                tmpl = cv2.imread(path)
                if tmpl is None: continue
                res = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val >= 0.75:
                    h, w = tmpl.shape[:2]
                    x, y = max_loc[0] + w//2, max_loc[1] + h//2
                    self.add_log(f"🔍 找到 '{os.path.basename(path)}' | 匹配度:{max_val:.0%} | 位置:({x},{y})")
                    return x, y
            self.add_log(f"⚠️ 未找到匹配（已扫描{len(self.target_images)}个目标）")
            return None
        except Exception as e:
            self.add_log(f"❌ 查找错误: {str(e)}")
            return None
    
    def click_target(self, x, y):
        try:
            sw, sh = pyautogui.size()
            if not (0 <= x <= sw and 0 <= y <= sh):
                self.add_log(f"❌ 坐标无效: ({x},{y})")
                return False
            pyautogui.moveTo(x, y, duration=0.1)
            if self.click_type.get() == "double":
                pyautogui.doubleClick(x, y, interval=0.1)
                self.add_log(f"🖱️ 双击位置: ({x},{y})")
            else:
                pyautogui.click(x, y)
                self.add_log(f"🖱️ 单击位置: ({x},{y})")
            return True
        except Exception as e:
            self.add_log(f"❌ 点击失败: {str(e)}")
            return False
    
    def validate(self):
        if not self.target_images:
            messagebox.showerror("错误", "请先添加至少1张目标图片！")
            return False
        if not self.infinite_loop.get() and self.loop_count.get() < 1:
            messagebox.showerror("错误", "循环次数需≥1")
            return False
        return True
    
    def start_clicking_safe(self):
        if self.validate(): self.start_clicking()
    
    def start_clicking(self):
        self.is_running = True
        self.stop_flag = False
        self.start_btn.config(state=tk.DISABLED, text="⏳ 运行中...")
        self.stop_btn.config(state=tk.NORMAL)
        
        # 清空日志
        self.log_txt.config(state=tk.NORMAL)
        self.log_txt.delete(1.0, tk.END)
        self.log_txt.config(state=tk.DISABLED)
        
        mode = "双击" if self.click_type.get()=="double" else "单击"
        loop = "♾️ 无限循环" if self.infinite_loop.get() else f"{self.loop_count.get()}次"
        self.add_log("="*50)
        self.add_log(f"🚀 任务启动 | 点击:{mode} | 循环:{loop} | 间隔:{self.interval_time.get()}秒")
        self.add_log(f"🎯 目标图片: {len(self.target_images)}个")
        self.add_log("="*50)
        
        threading.Thread(target=self.worker, daemon=True).start()
    
    def stop_clicking(self):
        self.stop_flag = True
        self.add_log("\n🛑 停止信号已发送...")
        self.stop_btn.config(state=tk.DISABLED)
    
    def worker(self):
        interval = self.interval_time.get()
        success, fail, iters = 0, 0, 0
        try:
            while True:
                if self.stop_flag: break
                iters += 1
                self.add_log(f"\n🔄 第 {iters} 次查找...")
                pos = self.find_image()
                if pos and self.click_target(*pos): success += 1
                else: fail += 1
                if not self.infinite_loop.get() and iters >= self.loop_count.get(): break
                if not self.stop_flag: time.sleep(interval)
        finally:
            self.add_log("\n" + "="*50)
            if self.stop_flag:
                self.add_log(f"⏹️ 任务中断 | 成功:{success} | 失败:{fail} | 总计:{iters}次")
            else:
                self.add_log(f"✅ 任务完成 | 成功:{success} | 失败:{fail} | 总计:{iters}次")
            self.add_log("="*50)
            self.root.after(0, lambda: [
                self.start_btn.config(state=tk.NORMAL, text="▶️ 开始执行 (F6)"),
                self.stop_btn.config(state=tk.DISABLED)
            ])
            self.is_running = False
    
    def add_log(self, msg):
        t = time.strftime('%H:%M:%S')
        self.log_queue.put(f"[{t}] {msg}")
    
    def process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_txt.config(state=tk.NORMAL)
                self.log_txt.insert(tk.END, msg + "\n")
                self.log_txt.see(tk.END)
                self.log_txt.config(state=tk.DISABLED)
        except: pass
        self.root.after(100, self.process_log_queue)
    
    def on_closing(self):
        self.stop_flag = True
        if self.hotkey_registered and KEYBOARD_AVAILABLE:
            try: keyboard.unhook_all_hotkeys()
            except: pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClickerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    try: root.iconphoto(True, ImageTk.PhotoImage(Image.new('RGBA', (1,1), (0,0,0,0))))
    except: pass
    root.mainloop()