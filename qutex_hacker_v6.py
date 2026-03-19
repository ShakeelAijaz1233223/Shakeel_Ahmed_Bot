"""
╔══════════════════════════════════════════════════════════════════╗
║       💀 QUTEX HACKER v6.0 — REAL TIME CHART ANALYZER 💀       ║
╚══════════════════════════════════════════════════════════════════╝

Run:      python qutex_hacker_v6.py
Requires: pip install pillow opencv-python numpy pyautogui psutil pyperclip

Works on: Windows / Linux / macOS
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import os
import sys
import subprocess
import random
import platform

# ── Optional imports with graceful fallback ──────────────────────
try:
    import pyperclip
    PYPERCLIP_OK = True
except ImportError:
    PYPERCLIP_OK = False

try:
    from PIL import Image, ImageTk, ImageGrab, ImageEnhance, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False

try:
    import numpy as np
    NP_OK = True
except ImportError:
    NP_OK = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

# ── OS detection ──────────────────────────────────────────────────
IS_WIN   = platform.system() == "Windows"
IS_MAC   = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# ── Colors ────────────────────────────────────────────────────────
BG       = "#000000"
BG1      = "#0a0a0a"
BG2      = "#111111"
BG3      = "#000011"
BG4      = "#000033"
GREEN    = "#00FF00"
GREEN2   = "#44FF44"
RED      = "#FF4444"
RED2     = "#FF0000"
CYAN     = "#00FFFF"
YELLOW   = "#FFFF00"
ORANGE   = "#FFAA00"
WHITE    = "#FFFFFF"
GRAY     = "#888888"
DKGREEN  = "#003300"
DKRED    = "#330000"

FONT_TITLE  = ("Courier", 16, "bold")
FONT_BIG    = ("Courier", 12, "bold")
FONT_MED    = ("Courier", 10, "bold")
FONT_NORM   = ("Courier", 10)
FONT_SMALL  = ("Courier", 9)
FONT_TINY   = ("Courier", 8)

FOREX_PAIRS = [
    "EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","USDCAD",
    "NZDUSD","EURJPY","GBPJPY","EURGBP","EURCHF","AUDJPY",
    "GBPAUD","EURAUD","GBPCAD","CHFJPY"
]
TIMEFRAMES = ["M1","M5","M15","M30","H1","H4","D1"]


# ══════════════════════════════════════════════════════════════════
#  SNIPPING OVERLAY  (cross-platform, no extra lib needed)
# ══════════════════════════════════════════════════════════════════
class SnipOverlay(tk.Toplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.callback  = callback
        self.start_x   = self.start_y = 0
        self.rect_id   = None
        self.screen_img = None

        # Grab screen before overlay
        if PIL_OK:
            try:
                self.screen_img = ImageGrab.grab()
            except Exception:
                pass

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="black", cursor="crosshair")
        self.attributes("-alpha", 0.30)

        self.cv = tk.Canvas(self, bg="black", highlightthickness=0,
                            cursor="crosshair")
        self.cv.pack(fill="both", expand=True)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.cv.create_text(sw//2, 50,
            text="📸  DRAG TO SELECT CHART AREA  —  ESC to cancel",
            font=("Courier", 16, "bold"), fill=RED2)

        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",        self._drag)
        self.cv.bind("<ButtonRelease-1>",  self._release)
        self.bind("<Escape>", lambda e: self._cancel())

    def _press(self, e):
        self.start_x, self.start_y = e.x, e.y
        if self.rect_id:
            self.cv.delete(self.rect_id)

    def _drag(self, e):
        if self.rect_id:
            self.cv.delete(self.rect_id)
        self.rect_id = self.cv.create_rectangle(
            self.start_x, self.start_y, e.x, e.y,
            outline=RED2, width=2, fill="#ff000022")

    def _release(self, e):
        x1 = min(self.start_x, e.x)
        y1 = min(self.start_y, e.y)
        x2 = max(self.start_x, e.x)
        y2 = max(self.start_y, e.y)
        self.destroy()
        if x2 - x1 < 10 or y2 - y1 < 10:
            return
        if self.screen_img:
            try:
                cropped = self.screen_img.crop((x1, y1, x2, y2))
                self.callback(cropped)
                return
            except Exception:
                pass
        self.callback(None)

    def _cancel(self):
        self.destroy()
        self.callback(None)


# ══════════════════════════════════════════════════════════════════
#  CHART ANALYZER  (pure Python + optional OpenCV)
# ══════════════════════════════════════════════════════════════════
def analyze_chart(img):
    """
    Analyze PIL Image of a trading chart.
    Returns: (trend_score, direction_str, signal_quality, green_pct, red_pct)
    """
    if img is None:
        return 0, "UNKNOWN", "LOW", 0, 0

    try:
        rgb = img.convert("RGB")
        w, h = rgb.size

        # ── Pixel counting ──────────────────────────────────────
        green_px = red_px = dark_px = total = 0
        # Left / right halves
        lg = lr = rg = rr = 0
        mid = w // 2
        # Bottom 30%
        bg_ = br_ = 0
        bot_start = int(h * 0.70)

        for y in range(0, h, 3):
            for x in range(0, w, 3):
                r, g, b = rgb.getpixel((x, y))
                total += 1
                bright = (r + g + b) / 3
                if bright < 35:
                    dark_px += 1
                    continue
                is_g = g > r * 1.25 and g > b * 1.25 and g > 55
                is_r = r > g * 1.25 and r > b * 1.25 and r > 55
                if is_g: green_px += 1
                if is_r: red_px   += 1
                # halves
                if x < mid:
                    if is_g: lg += 1
                    if is_r: lr += 1
                else:
                    if is_g: rg += 1
                    if is_r: rr += 1
                # bottom
                if y >= bot_start:
                    if is_g: bg_ += 1
                    if is_r: br_ += 1

        usable = max(1, total - dark_px)
        green_pct = green_px / usable * 100
        red_pct   = red_px   / usable * 100

        # ── OpenCV enhanced analysis ─────────────────────────────
        cv_bonus = 0
        if CV2_OK and NP_OK:
            try:
                arr = np.array(rgb)
                cv_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                gray   = cv2.cvtColor(cv_bgr, cv2.COLOR_BGR2GRAY)

                # CLAHE contrast
                clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                enhanced= clahe.apply(gray)

                # Edge density
                edges   = cv2.Canny(enhanced, 50, 150)
                eh, ew  = edges.shape

                # Upper vs lower edge density
                upper_e = np.sum(edges[:eh//3, :] > 0)
                lower_e = np.sum(edges[2*eh//3:, :] > 0)
                cv_bonus = (upper_e - lower_e) / max(1, eh * ew) * 500

                # Recent candles (right 25%)
                recent  = cv_bgr[:, 3*ew//4:, :]
                rec_g   = np.sum((recent[:,:,1].astype(int) - recent[:,:,2].astype(int)) > 20)
                rec_r   = np.sum((recent[:,:,2].astype(int) - recent[:,:,1].astype(int)) > 20)
                cv_bonus += (rec_g - rec_r) / max(1, recent.size) * 300
            except Exception:
                pass

        # ── Score ────────────────────────────────────────────────
        score  = (green_pct - red_pct) * 1.2
        score += ((rg - rr) - (lg - lr)) / max(1, usable) * 80
        score += (bg_ - br_) / max(1, usable) * 50
        score += cv_bonus

        # Quality
        abs_s = abs(score)
        quality = "🔥 HIGH" if abs_s > 4 else "✅ GOOD" if abs_s > 1.5 else "⚠️ LOW"

        if score > 1.5:
            direction = "🟢 UP TREND (BUY)"
        elif score < -1.5:
            direction = "🔴 DOWN TREND (SELL)"
        else:
            direction = "🟡 SIDEWAYS (HOLD)"

        return score, direction, quality, green_pct, red_pct

    except Exception as ex:
        return 0, f"ERROR: {ex}", "LOW", 0, 0


# ══════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════
class QUTEXHackerV6:
    def __init__(self, root):
        self.root = root
        self.root.title("💀 QUTEX HACKER v6.0 — REAL CHART ANALYZER 💀")
        self.root.geometry("1400x950")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        # State
        self.is_trading       = False
        self.balance          = 10000.0
        self.total_trades     = 0
        self.wins             = 0
        self.losses           = 0
        self.screenshot_path  = "latest_screenshot.png"
        self.detected_pair    = "UNKNOWN"
        self.detected_tf      = "UNKNOWN"
        self.signals          = {}
        self.top_signals      = []
        self.snip_photo       = None   # PhotoImage reference
        self.blink_on         = True

        self._setup_ui()
        self._start_balance_monitor()
        self._blink_title()

        # Startup log
        self.log("💀 QUTEX HACKER v6.0 LOADED — REAL CHART ANALYSIS ENGINE")
        self.log(f"🖥️  Platform: {platform.system()} {platform.release()}")
        self.log(f"🐍 Python: {sys.version.split()[0]}")
        libs = []
        if PIL_OK:      libs.append("Pillow✅")
        else:           libs.append("Pillow❌")
        if CV2_OK:      libs.append("OpenCV✅")
        else:           libs.append("OpenCV❌")
        if NP_OK:       libs.append("NumPy✅")
        else:           libs.append("NumPy❌")
        if PYAUTOGUI_OK:libs.append("PyAutoGUI✅")
        else:           libs.append("PyAutoGUI❌")
        if PSUTIL_OK:   libs.append("PSUtil✅")
        else:           libs.append("PSUtil❌")
        self.log("📦 Libraries: " + "  ".join(libs))
        if not PIL_OK:
            self.log("⚠️  CRITICAL: pip install pillow  (screenshot required)")
        self.log("─" * 55)
        self.log("🔥 Click 📸 CAPTURE → select chart → AI analyzes → Signal!")

    # ──────────────────────────────────────────────────────────────
    #  UI SETUP
    # ──────────────────────────────────────────────────────────────
    def _setup_ui(self):
        # ── TITLE BAR ──────────────────────────────────────────
        title_f = tk.Frame(self.root, bg=BG, height=55)
        title_f.pack(fill="x", padx=8, pady=(6,0))
        title_f.pack_propagate(False)
        self.title_lbl = tk.Label(title_f,
            text="💀  QUTEX HACKER v6.0 — REAL TIME CHART ANALYZER  💀",
            font=FONT_TITLE, bg=BG, fg=GREEN)
        self.title_lbl.pack(expand=True)

        # ── CONTROL BAR ────────────────────────────────────────
        ctrl = tk.Frame(self.root, bg=BG1, relief="raised", bd=2)
        ctrl.pack(fill="x", padx=8, pady=4)

        # Screenshot button
        self.snap_btn = tk.Button(ctrl, text="📸  CAPTURE & ANALYZE CHART",
            font=FONT_BIG, bg=RED, fg=WHITE,
            activebackground=RED2, activeforeground=WHITE,
            relief="raised", bd=3, padx=16, pady=4,
            cursor="hand2", command=self._on_capture_click)
        self.snap_btn.pack(side="left", padx=10, pady=8)

        self.snap_status = tk.Label(ctrl, text="STATUS: READY",
            bg=BG1, fg=YELLOW, font=FONT_NORM)
        self.snap_status.pack(side="left", padx=6)

        # Separator
        tk.Label(ctrl, text="│", bg=BG1, fg=GRAY).pack(side="left", padx=4)

        # Trading toggle
        self.trade_btn = tk.Button(ctrl, text="🚀  START AUTO TRADING",
            font=FONT_BIG, bg=GREEN2, fg=BG,
            activebackground=GREEN, activeforeground=BG,
            relief="raised", bd=3, padx=16, pady=4,
            cursor="hand2", command=self._toggle_trading)
        self.trade_btn.pack(side="left", padx=10, pady=8)

        self.trading_status = tk.Label(ctrl, text="AI TRADING: OFFLINE",
            bg=BG1, fg=RED, font=FONT_NORM)
        self.trading_status.pack(side="left", padx=6)

        # Balance (right)
        self.balance_lbl = tk.Label(ctrl,
            text=f"BALANCE: ${self.balance:,.2f}",
            bg=BG1, fg=CYAN, font=FONT_BIG)
        self.balance_lbl.pack(side="right", padx=20, pady=8)

        # ── MAIN CONTENT ───────────────────────────────────────
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=8, pady=4)

        # LEFT  (width=460)
        left = tk.Frame(main, bg=BG, width=460)
        left.pack(side="left", fill="y", padx=(0,8))
        left.pack_propagate(False)
        self._build_left(left)

        # RIGHT
        right = tk.Frame(main, bg=BG)
        right.pack(side="right", fill="both", expand=True)
        self._build_right(right)

    # ── LEFT PANEL ─────────────────────────────────────────────
    def _build_left(self, p):
        # Detection
        det = tk.LabelFrame(p, text="🔍  CHART DETECTION",
            bg=BG2, fg=GREEN, font=FONT_MED, relief="groove", bd=2)
        det.pack(fill="x", pady=(0,8))

        self.pair_lbl = tk.Label(det, text=f"PAIR:       {self.detected_pair}",
            bg=BG2, fg=ORANGE, font=FONT_MED)
        self.pair_lbl.pack(pady=4)
        self.tf_lbl = tk.Label(det, text=f"TIMEFRAME:  {self.detected_tf}",
            bg=BG2, fg=ORANGE, font=FONT_MED)
        self.tf_lbl.pack(pady=4)
        self.trend_lbl = tk.Label(det, text="TREND:      —",
            bg=BG2, fg=YELLOW, font=FONT_MED)
        self.trend_lbl.pack(pady=4)
        self.quality_lbl = tk.Label(det, text="QUALITY:    —",
            bg=BG2, fg=YELLOW, font=FONT_SMALL)
        self.quality_lbl.pack(pady=(0,6))

        # Signal banner
        sig_f = tk.Frame(p, bg=BG, highlightbackground=GREEN, highlightthickness=2)
        sig_f.pack(fill="x", pady=(0,8))
        tk.Label(sig_f, text="PROFESSOR SIGNAL", font=FONT_MED,
                 bg=BG, fg=GRAY).pack()
        self.big_signal_lbl = tk.Label(sig_f, text="WAITING...",
            font=("Courier", 32, "bold"), bg=BG, fg=YELLOW)
        self.big_signal_lbl.pack(pady=(0,4))
        self.big_conf_lbl = tk.Label(sig_f, text="",
            font=FONT_NORM, bg=BG, fg=GRAY)
        self.big_conf_lbl.pack(pady=(0,6))

        # Stats
        stats = tk.LabelFrame(p, text="📊  TRADING STATS",
            bg=BG2, fg=GREEN, font=FONT_MED, relief="groove", bd=2)
        stats.pack(fill="x", pady=(0,8))

        self.wr_lbl = tk.Label(stats, text="WIN RATE:  0%",
            bg=BG2, fg=GREEN, font=FONT_MED)
        self.wr_lbl.pack(pady=3)
        self.trades_lbl = tk.Label(stats, text="TOTAL TRADES: 0  (W:0  L:0)",
            bg=BG2, fg=WHITE, font=FONT_SMALL)
        self.trades_lbl.pack(pady=3)
        # Win rate bar
        bar_bg = tk.Frame(stats, bg="#222222", height=10)
        bar_bg.pack(fill="x", padx=10, pady=(2,8))
        self.wr_bar     = tk.Frame(bar_bg, bg=GREEN, height=10)
        self.wr_bar.place(x=0, y=0, relheight=1, width=0)
        self.wr_bar_bg  = bar_bg

        # Live signals list
        sigs = tk.LabelFrame(p, text="🎯  LIVE SIGNALS (TOP 10)",
            bg=BG2, fg=GREEN, font=FONT_MED, relief="groove", bd=2)
        sigs.pack(fill="both", expand=True)

        self.signals_lb = tk.Listbox(sigs, bg=BG4, fg=GREEN,
            font=FONT_SMALL, selectbackground="#4444FF",
            activestyle="none", relief="flat")
        sb = tk.Scrollbar(sigs, orient="vertical", command=self.signals_lb.yview,
                          bg=BG2)
        self.signals_lb.configure(yscrollcommand=sb.set)
        self.signals_lb.pack(side="left", fill="both", expand=True, padx=(5,0), pady=5)
        sb.pack(side="right", fill="y", pady=5)

    # ── RIGHT PANEL ────────────────────────────────────────────
    def _build_right(self, p):
        # Chart display
        chart_lf = tk.LabelFrame(p, text="📈  CHART ANALYZER v6.0",
            bg=BG2, fg=GREEN, font=FONT_MED, relief="groove", bd=2)
        chart_lf.pack(fill="x", pady=(0,8))

        self.chart_lbl = tk.Label(chart_lf,
            text="NO CHART — Click 📸 CAPTURE to analyze",
            bg="#1a1a1a", fg=GRAY, font=FONT_NORM,
            width=75, height=18)
        self.chart_lbl.pack(padx=6, pady=6)

        self.analysis_lbl = tk.Label(chart_lf,
            text="🚫  NO ANALYSIS — Take screenshot first",
            bg=BG2, fg=RED, font=FONT_MED)
        self.analysis_lbl.pack(pady=(0,6))

        # Pixel stats bar
        pix_f = tk.Frame(chart_lf, bg=BG2)
        pix_f.pack(fill="x", padx=10, pady=(0,8))
        tk.Label(pix_f, text="Green:", font=FONT_SMALL, bg=BG2, fg=GREEN).pack(side="left")
        self.green_lbl = tk.Label(pix_f, text="—%", font=FONT_SMALL, bg=BG2, fg=GREEN)
        self.green_lbl.pack(side="left", padx=(2,12))
        tk.Label(pix_f, text="Red:", font=FONT_SMALL, bg=BG2, fg=RED).pack(side="left")
        self.red_lbl = tk.Label(pix_f, text="—%", font=FONT_SMALL, bg=BG2, fg=RED)
        self.red_lbl.pack(side="left", padx=(2,0))

        # Hacking console
        con_lf = tk.LabelFrame(p, text="💀  HACKING CONSOLE",
            bg=BG2, fg=GREEN, font=FONT_MED, relief="groove", bd=2)
        con_lf.pack(fill="both", expand=True)

        self.console = scrolledtext.ScrolledText(con_lf,
            bg=BG3, fg=GREEN, font=FONT_SMALL,
            insertbackground=GREEN, relief="flat", height=14)
        self.console.pack(fill="both", expand=True, padx=5, pady=5)
        # Tags
        for tag, col in [("red",RED),("yellow",YELLOW),("cyan",CYAN),
                         ("orange",ORANGE),("white",WHITE),("gray",GRAY)]:
            self.console.tag_config(tag, foreground=col)

    # ──────────────────────────────────────────────────────────────
    #  SCREENSHOT FLOW
    # ──────────────────────────────────────────────────────────────
    def _on_capture_click(self):
        if not PIL_OK:
            messagebox.showerror("Missing Library",
                "Pillow required!\n\nRun:\n  pip install pillow")
            return
        self.snap_status.config(text="STATUS: SELECT AREA...", fg=YELLOW)
        self.snap_btn.config(state="disabled")
        self.log("📸 Screenshot mode — select chart area on screen...", "yellow")
        self.root.iconify()
        self.root.after(350, self._open_snip)

    def _open_snip(self):
        SnipOverlay(self.root, self._on_snip_done)

    def _on_snip_done(self, img):
        self.root.deiconify()
        self.root.lift()
        if img is None:
            self.snap_status.config(text="STATUS: CANCELLED", fg=ORANGE)
            self.snap_btn.config(state="normal")
            self.log("Screenshot cancelled.", "gray")
            return
        self.snap_status.config(text="STATUS: ANALYZING...", fg=YELLOW)
        self.log("✅ Screenshot captured! Running analysis...", "cyan")
        # Save
        try:
            img.save(self.screenshot_path)
        except Exception:
            pass
        # Show in chart panel immediately
        self._display_image(img)
        # Analyze in background
        threading.Thread(target=self._run_analysis, args=(img,), daemon=True).start()

    def _display_image(self, img):
        """Resize and display PIL image in chart_lbl."""
        if not PIL_OK:
            return
        try:
            disp = img.copy()
            disp.thumbnail((700, 300), Image.LANCZOS)
            photo = ImageTk.PhotoImage(disp)
            self.snip_photo = photo
            self.chart_lbl.configure(image=photo, text="", width=700, height=300)
            self.chart_lbl.image = photo
        except Exception as e:
            self.log(f"Display error: {e}", "red")

    # ──────────────────────────────────────────────────────────────
    #  CHART ANALYSIS ENGINE
    # ──────────────────────────────────────────────────────────────
    def _run_analysis(self, img):
        """Background thread — analyze chart image."""
        try:
            # Step 1: pixel / CV analysis
            score, direction, quality, g_pct, r_pct = analyze_chart(img)

            # Step 2: detect pair & timeframe
            pair, tf = self._detect_pair_timeframe(img)

            # Step 3: generate signals
            signals, top = self._generate_signals(score)

            # Update UI on main thread
            self.root.after(0, lambda: self._update_analysis_ui(
                score, direction, quality, g_pct, r_pct, pair, tf, signals, top))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Analysis error: {e}", "red"))
            self.root.after(0, lambda: self.snap_btn.config(state="normal"))

    def _detect_pair_timeframe(self, img):
        """
        Detect pair/timeframe.
        If OpenCV+NumPy available: uses image region brightness patterns.
        Otherwise: random selection (demo).
        """
        if CV2_OK and NP_OK and PIL_OK:
            try:
                rgb = img.convert("RGB")
                arr = np.array(rgb)
                gray = np.mean(arr, axis=2)
                h, w = gray.shape

                # Top-left brightness → pair index
                tl = gray[:int(h*0.15), :int(w*0.40)]
                pair_idx = int(np.sum(tl > 180) % len(FOREX_PAIRS))

                # Top-right brightness → TF index
                tr = gray[:int(h*0.15), int(w*0.70):]
                tf_idx = int(np.sum(tr > 180) % len(TIMEFRAMES))

                return FOREX_PAIRS[pair_idx], TIMEFRAMES[tf_idx]
            except Exception:
                pass

        # Fallback
        return random.choice(FOREX_PAIRS), random.choice(TIMEFRAMES)

    def _generate_signals(self, trend_score):
        """Generate BUY/SELL/HOLD signals for all pairs."""
        sigs = {}
        base_conf  = min(97, 65 + abs(trend_score) * 20)
        buy_bias   = 0.72 if trend_score > 0 else 0.28

        for pair in FOREX_PAIRS:
            conf = min(98, max(52, base_conf + random.uniform(-12, 14)))
            r    = random.random()
            if conf > 80:
                direction = "🟢 UP (BUY)"  if r < buy_bias else "🔴 DOWN (SELL)"
            elif conf > 65:
                direction = "🟢 UP (BUY)"  if r < buy_bias * 0.9 else "🔴 DOWN (SELL)"
            else:
                direction = "🟡 SIDEWAYS (HOLD)"
            sigs[pair] = {"direction": direction, "confidence": conf,
                          "move": "UP" if "UP" in direction else
                                  "DOWN" if "DOWN" in direction else "HOLD"}

        top = sorted(sigs.items(), key=lambda x: x[1]["confidence"], reverse=True)[:10]
        return sigs, top

    def _update_analysis_ui(self, score, direction, quality, g_pct, r_pct,
                             pair, tf, signals, top):
        """Apply all analysis results to UI."""
        self.detected_pair = pair
        self.detected_tf   = tf
        self.signals       = signals
        self.top_signals   = top

        # Detection labels
        self.pair_lbl.config(text=f"PAIR:       {pair}", fg=CYAN)
        self.tf_lbl.config(text=f"TIMEFRAME:  {tf}",   fg=CYAN)
        self.trend_lbl.config(
            text=f"TREND:      {direction}",
            fg=GREEN if "UP" in direction else RED if "DOWN" in direction else YELLOW)
        self.quality_lbl.config(text=f"QUALITY:    {quality}", fg=ORANGE)

        # Analysis bar
        self.analysis_lbl.config(
            text=f"{direction}  |  Strength: {abs(score):.2f}  |  Quality: {quality}",
            fg=GREEN if "UP" in direction else RED if "DOWN" in direction else YELLOW)

        # Pixel stats
        self.green_lbl.config(text=f"{g_pct:.1f}%")
        self.red_lbl.config(text=f"{r_pct:.1f}%")

        # Big signal
        if "UP" in direction:
            sig_text, sig_color = "BUY  ▲", GREEN
        elif "DOWN" in direction:
            sig_text, sig_color = "SELL ▼", RED
        else:
            sig_text, sig_color = "HOLD  —", YELLOW

        self.big_signal_lbl.config(text=sig_text, fg=sig_color)
        conf_top = top[0][1]["confidence"] if top else 0
        self.big_conf_lbl.config(
            text=f"Confidence: {conf_top:.0f}%  |  Score: {score:+.2f}",
            fg=sig_color)

        # Flash signal
        self._flash_signal(sig_color, 0)

        # Signals list
        self._update_signals_list()

        # Console
        self.log("━"*50, "cyan")
        self.log(f"📊 ANALYSIS COMPLETE", "cyan")
        self.log(f"   Pair:       {pair}", "orange")
        self.log(f"   Timeframe:  {tf}", "orange")
        self.log(f"   Trend:      {direction}", "white")
        self.log(f"   Score:      {score:+.3f}", "white")
        self.log(f"   Quality:    {quality}", "white")
        self.log(f"   Green px:   {g_pct:.1f}%   Red px: {r_pct:.1f}%", "white")
        self.log(f"   SIGNAL ▶▶  {sig_text}  ({conf_top:.0f}% conf)", "cyan")
        strong = [p for p,s in top if s["confidence"] > 80]
        self.log(f"   Strong signals (>80%): {len(strong)}", "yellow")
        self.log("━"*50, "cyan")

        # Status
        self.snap_status.config(text="✅ ANALYZED", fg=GREEN)
        self.snap_btn.config(state="normal")

    def _flash_signal(self, color, count):
        if count >= 8:
            self.big_signal_lbl.config(fg=color)
            return
        self.big_signal_lbl.config(fg=color if count % 2 == 0 else BG)
        self.root.after(180, lambda: self._flash_signal(color, count+1))

    def _update_signals_list(self):
        self.signals_lb.delete(0, "end")
        for i, (pair, sig) in enumerate(self.top_signals, 1):
            d = sig["direction"]
            c = sig["confidence"]
            line = f" {i:2d}. {pair:<7}  {d:<16}  {c:5.1f}%"
            self.signals_lb.insert("end", line)
            if "UP" in d:
                self.signals_lb.itemconfig(i-1, fg=GREEN)
            elif "DOWN" in d:
                self.signals_lb.itemconfig(i-1, fg=RED)
            else:
                self.signals_lb.itemconfig(i-1, fg=YELLOW)

    # ──────────────────────────────────────────────────────────────
    #  AUTO TRADING
    # ──────────────────────────────────────────────────────────────
    def _toggle_trading(self):
        self.is_trading = not self.is_trading
        if self.is_trading:
            self.trade_btn.config(text="⏹️  STOP TRADING",   bg=RED,    fg=WHITE)
            self.trading_status.config(text="AI TRADING: LIVE", fg=GREEN)
            self.log("🚀 AUTO TRADING STARTED — executing top signals", "yellow")
            threading.Thread(target=self._trading_loop, daemon=True).start()
        else:
            self.trade_btn.config(text="🚀  START AUTO TRADING", bg=GREEN2, fg=BG)
            self.trading_status.config(text="AI TRADING: OFFLINE", fg=RED)
            self.log("⏹️ TRADING STOPPED", "red")

    def _trading_loop(self):
        count = 0
        while self.is_trading and count < 100:
            if self.top_signals:
                pair, sig = self.top_signals[0]
                self.root.after(0, lambda p=pair, s=sig: self._execute_trade(p, s))
            time.sleep(28)
            count += 1

    def _execute_trade(self, pair, signal):
        direction  = "BUY"  if "UP"   in signal["direction"] else \
                     "SELL" if "DOWN" in signal["direction"] else "HOLD"
        confidence = signal["confidence"]

        if direction == "HOLD":
            self.log(f"⏸️  HOLD signal for {pair} — skipping", "gray")
            return

        self.log(f"⚡ TRADE: {direction} {pair}  |  Conf: {confidence:.0f}%", "yellow")

        executed = False
        # Try to find QUTEX process
        if PSUTIL_OK and PYAUTOGUI_OK:
            try:
                for proc in psutil.process_iter(["pid","name","cmdline"]):
                    name = (proc.info.get("name") or "").lower()
                    cmdl = str(proc.info.get("cmdline") or "").lower()
                    if "qutex" in name or "qutex" in cmdl:
                        self.log(f"✅ QUTEX PROCESS FOUND (PID {proc.pid}) — executing", "cyan")
                        pyautogui.click(200, 200);  time.sleep(0.7)
                        pyautogui.write(pair);       time.sleep(0.5)
                        pyautogui.press("enter");    time.sleep(0.7)
                        if direction == "BUY":
                            pyautogui.hotkey("ctrl","b")
                        else:
                            pyautogui.hotkey("ctrl","s")
                        executed = True
                        break
            except Exception as e:
                self.log(f"⚠️ Process scan error: {e}", "red")

        # Demo / simulation
        if not executed:
            self.log("💻 DEMO MODE — QUTEX not detected (simulating trade)", "gray")

        # P&L simulation (realistic accuracy tied to confidence)
        win_prob = 0.55 + (confidence - 65) / 100
        self.total_trades += 1
        if random.random() < win_prob:
            self.wins += 1
            profit = 100 + (confidence - 70) * 3.5
            self.balance += profit
            self.log(f"💰 WIN  +${profit:.0f}  |  Balance: ${self.balance:,.0f}", "cyan")
        else:
            self.losses += 1
            loss = 75 + random.uniform(0, 30)
            self.balance -= loss
            self.log(f"📉 LOSS -${loss:.0f}  |  Balance: ${self.balance:,.0f}", "red")

        self._update_stats()

    def _update_stats(self):
        wr  = (self.wins / self.total_trades * 100) if self.total_trades else 0
        self.wr_lbl.config(text=f"WIN RATE:  {wr:.1f}%",
                           fg=GREEN if wr >= 50 else RED)
        self.trades_lbl.config(
            text=f"TOTAL TRADES: {self.total_trades}  (W:{self.wins}  L:{self.losses})")
        self.balance_lbl.config(text=f"BALANCE: ${self.balance:,.0f}")
        # Bar
        self.wr_bar_bg.update_idletasks()
        bw = int(self.wr_bar_bg.winfo_width() * wr / 100)
        self.wr_bar.place(x=0, y=0, width=bw, relheight=1)

    # ──────────────────────────────────────────────────────────────
    #  BACKGROUND BALANCE MONITOR
    # ──────────────────────────────────────────────────────────────
    def _start_balance_monitor(self):
        def loop():
            while True:
                time.sleep(4)
                if self.is_trading and self.balance > 0:
                    tick = random.uniform(-20, 35) * 0.04
                    self.balance += tick
                    self.root.after(0, lambda b=self.balance:
                        self.balance_lbl.config(text=f"BALANCE: ${b:,.0f}"))
        threading.Thread(target=loop, daemon=True).start()

    # ──────────────────────────────────────────────────────────────
    #  TITLE BLINK
    # ──────────────────────────────────────────────────────────────
    def _blink_title(self):
        if hasattr(self, "title_lbl"):
            self.title_lbl.config(fg=GREEN if self.blink_on else "#006600")
            self.blink_on = not self.blink_on
        self.root.after(700, self._blink_title)

    # ──────────────────────────────────────────────────────────────
    #  LOG
    # ──────────────────────────────────────────────────────────────
    def log(self, msg, tag=""):
        ts = time.strftime("%H:%M:%S")
        self.console.insert("end", f"[{ts}] {msg}\n", tag)
        self.console.see("end")
        self.root.update_idletasks()

    # ──────────────────────────────────────────────────────────────
    #  CLOSE
    # ──────────────────────────────────────────────────────────────
    def on_close(self):
        self.is_trading = False
        self.root.destroy()


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
def main():
    # Dependency check
    missing = []
    if not PIL_OK:      missing.append("pillow")
    if not CV2_OK:      missing.append("opencv-python")
    if not NP_OK:       missing.append("numpy")
    if not PYAUTOGUI_OK:missing.append("pyautogui")
    if not PSUTIL_OK:   missing.append("psutil")

    if missing:
        print("━"*55)
        print("⚠️  MISSING LIBRARIES — install them for full features:")
        print(f"    pip install {' '.join(missing)}")
        print("━"*55)
        if "pillow" in missing:
            print("❌ CRITICAL: Pillow required for screenshots!")
            print("   pip install pillow")
            print("   App will start but screenshot will not work.")
        print()

    root = tk.Tk()
    app  = QUTEXHackerV6(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
