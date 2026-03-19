#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         PROFESSOR IS WATCHING — Trading Signal Bot           ║
║         Python Tkinter Desktop App  |  v3.0                  ║
║         Run: python professor_trading.py                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
import math
import time
import threading
import json
from datetime import datetime

# ══════════════════════════════════════════════════════════════
#  COLORS & FONTS
# ══════════════════════════════════════════════════════════════
BG          = "#0a0000"
BG2         = "#110000"
BG3         = "#1a0000"
RED         = "#ff1a1a"
RED2        = "#cc0000"
RED_DIM     = "#660000"
RED_BRIGHT  = "#ff4444"
GREEN       = "#00ff44"
GREEN_DIM   = "#004422"
YELLOW      = "#ffcc00"
WHITE       = "#ffffff"
GRAY        = "#888888"
GRAY_DIM    = "#333333"
BORDER_RED  = "#aa0000"

FONT_TITLE  = ("Courier New", 18, "bold")
FONT_BIG    = ("Courier New", 14, "bold")
FONT_MED    = ("Courier New", 12, "bold")
FONT_SM     = ("Courier New", 10)
FONT_XSM    = ("Courier New", 9)
FONT_SIGNAL = ("Courier New", 32, "bold")
FONT_AGENT  = ("Courier New", 9)

# ══════════════════════════════════════════════════════════════
#  PAIRS DATA
# ══════════════════════════════════════════════════════════════
PAIRS = [
    "EUR/USD (OTC)", "GBP/USD (OTC)", "USD/JPY (OTC)",
    "AUD/USD (OTC)", "USD/BRL (OTC)", "USD/CAD (OTC)",
    "EUR/GBP (OTC)", "EUR/JPY (OTC)", "GBP/JPY (OTC)",
    "USD/CHF (OTC)", "NZD/USD (OTC)", "EUR/AUD (OTC)",
    "BTC/USD (OTC)", "ETH/USD (OTC)", "XAU/USD (OTC)",
    "EUR/USD",       "GBP/USD",       "USD/JPY",
    "AUD/USD",       "XAU/USD",
]

TIMEFRAMES = ["5s","10s","15s","30s","1m","2m","3m","5m","10m","15m","30m","1h","4h"]

PAIR_BASES = {
    "EUR/USD": 1.0850, "GBP/USD": 1.2650, "USD/JPY": 149.50,
    "AUD/USD": 0.6540, "USD/BRL": 5.0200, "USD/CAD": 1.3620,
    "EUR/GBP": 0.8580, "EUR/JPY": 162.50, "GBP/JPY": 189.20,
    "USD/CHF": 0.8980, "NZD/USD": 0.6120, "EUR/AUD": 1.6580,
    "BTC/USD": 67500,  "ETH/USD": 3450,   "XAU/USD": 2320,
}

# ══════════════════════════════════════════════════════════════
#  SIGNAL ENGINE
# ══════════════════════════════════════════════════════════════
class SignalEngine:
    def __init__(self):
        self.candle_history = {}
        self._init_candles()

    def _init_candles(self):
        for pair, base in PAIR_BASES.items():
            candles = []
            price = base
            for _ in range(100):
                o = price
                c = o + (random.random() - 0.495) * base * 0.002
                h = max(o, c) + random.random() * abs(c - o) * 0.5
                l = min(o, c) - random.random() * abs(c - o) * 0.5
                vol = random.randint(200, 1500)
                candles.append({"o": o, "h": h, "l": l, "c": c, "v": vol})
                price = c
            self.candle_history[pair] = candles

    def _get_base_pair(self, pair_str):
        """Extract base pair name (remove OTC suffix)"""
        name = pair_str.replace(" (OTC)", "").strip()
        return name

    def _update_candle(self, base):
        cs = self.candle_history.get(base)
        if not cs:
            return
        last = cs[-1]
        drift = (random.random() - 0.497) * last["c"] * 0.001
        new_c = last["c"] + drift
        last["c"] = new_c
        last["h"] = max(last["h"], new_c)
        last["l"] = min(last["l"], new_c)

    def _ema(self, prices, period):
        if len(prices) < period:
            return [prices[-1]] if prices else [0]
        k = 2 / (period + 1)
        ema = prices[0]
        arr = [ema]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
            arr.append(ema)
        return arr

    def _rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50.0
        gains, losses = 0, 0
        for i in range(1, period + 1):
            d = prices[i] - prices[i - 1]
            if d > 0: gains += d
            else: losses -= d
        ag, al = gains / period, losses / period
        for i in range(period + 1, len(prices)):
            d = prices[i] - prices[i - 1]
            if d > 0:
                ag = (ag * (period - 1) + d) / period
                al = al * (period - 1) / period
            else:
                al = (al * (period - 1) - d) / period
                ag = ag * (period - 1) / period
        return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)

    def _macd(self, prices):
        if len(prices) < 26:
            return 0, 0, 0
        e12 = self._ema(prices, 12)
        e26 = self._ema(prices, 26)
        ml  = [a - b for a, b in zip(e12, e26)]
        sig = self._ema(ml[25:], 9)
        m   = ml[-1]
        s   = sig[-1] if sig else 0
        return m, s, m - s

    def _bb(self, prices, period=20):
        if len(prices) < period:
            p = prices[-1] if prices else 0
            return p, p, p
        sl  = prices[-period:]
        mid = sum(sl) / period
        std = math.sqrt(sum((x - mid) ** 2 for x in sl) / period)
        return mid + 2 * std, mid, mid - 2 * std

    def _stoch_rsi(self, prices, period=14):
        if len(prices) < period * 2:
            return 50.0
        rsi_arr = [self._rsi(prices[:i+1], period) for i in range(period, len(prices))]
        if len(rsi_arr) < period:
            return 50.0
        last14 = rsi_arr[-period:]
        mn, mx = min(last14), max(last14)
        if mx == mn:
            return 50.0
        return (rsi_arr[-1] - mn) / (mx - mn) * 100

    def analyze(self, pair_str):
        base = self._get_base_pair(pair_str)
        self._update_candle(base)
        cs = self.candle_history.get(base, [])
        if not cs:
            return {"dir": "WAIT", "pct": 50, "signals": {}, "price": 0}

        closes = [c["c"] for c in cs]
        price  = closes[-1]

        rsi   = self._rsi(closes)
        macd_m, macd_s, macd_h = self._macd(closes)
        bb_u, bb_m, bb_l = self._bb(closes)
        stoch = self._stoch_rsi(closes)
        ema9  = self._ema(closes, 9)[-1]
        ema20 = self._ema(closes, 20)[-1]
        ema50 = self._ema(closes, 50)[-1]

        up, dn = 0, 0

        # RSI
        if   rsi < 25: up += 3
        elif rsi < 35: up += 2
        elif rsi < 40: up += 1
        elif rsi > 75: dn += 3
        elif rsi > 65: dn += 2
        elif rsi > 60: dn += 1

        # MACD
        if   macd_h > 0 and macd_m > 0: up += 2
        elif macd_h > 0:                 up += 1
        elif macd_h < 0 and macd_m < 0: dn += 2
        elif macd_h < 0:                 dn += 1

        # EMA
        if   ema9 > ema20: up += 2
        elif ema9 < ema20: dn += 2
        if   ema20 > ema50: up += 1
        elif ema20 < ema50: dn += 1

        # BB
        if   price < bb_l: up += 2
        elif price > bb_u: dn += 2

        # Stoch RSI
        if   stoch < 15: up += 3
        elif stoch < 25: up += 2
        elif stoch < 40: up += 1
        elif stoch > 85: dn += 3
        elif stoch > 75: dn += 2
        elif stoch > 65: dn += 1

        total = up + dn or 1
        pct   = round(max(up, dn) / total * 100)
        direction = "BUY" if up > dn else "SELL" if dn > up else "WAIT"

        return {
            "dir":    direction,
            "pct":    pct,
            "price":  price,
            "up":     up,
            "dn":     dn,
            "rsi":    rsi,
            "macd_h": macd_h,
            "stoch":  stoch,
            "ema9":   ema9,
            "ema20":  ema20,
            "bb_u":   bb_u,
            "bb_l":   bb_l,
        }

# ══════════════════════════════════════════════════════════════
#  CANDLE CANVAS WIDGET
# ══════════════════════════════════════════════════════════════
class CandleCanvas(tk.Canvas):
    def __init__(self, parent, engine, **kw):
        super().__init__(parent, bg=BG, highlightthickness=0, **kw)
        self.engine = engine
        self.pair   = "EUR/USD"
        self.after(100, self._redraw_loop)

    def set_pair(self, pair_str):
        self.pair = pair_str.replace(" (OTC)", "")

    def _redraw_loop(self):
        self._draw()
        self.after(600, self._redraw_loop)

    def _draw(self):
        self.delete("all")
        W = self.winfo_width()
        H = self.winfo_height()
        if W < 10 or H < 10:
            return

        cs = self.engine.candle_history.get(self.pair, [])
        if not cs:
            return

        n   = min(len(cs), max(20, W // 8))
        vis = cs[-n:]

        prices = [v for c in vis for v in (c["h"], c["l"])]
        mn, mx = min(prices), max(prices)
        rng = mx - mn or 0.001
        mn -= rng * 0.08
        mx += rng * 0.08
        rng = mx - mn

        pad_l, pad_r, pad_t, pad_b = 4, 48, 8, 16
        cw  = W - pad_l - pad_r
        ch  = H - pad_t - pad_b
        bw  = max(2, cw / n * 0.65)

        toY = lambda v: pad_t + ch - (v - mn) / rng * ch
        toX = lambda i: pad_l + (i + 0.5) * (cw / n)

        # Grid lines
        for i in range(5):
            y = pad_t + ch * i / 4
            self.create_line(pad_l, y, W - pad_r, y, fill="#1a0000", width=1)
            price = mx - rng * i / 4
            base  = PAIR_BASES.get(self.pair, 1)
            d     = 0 if base > 100 else (3 if base < 2 else 2)
            self.create_text(W - pad_r + 2, y, text=f"{price:.{d}f}",
                             anchor="w", font=("Courier New", 7), fill=RED_DIM)

        # EMA line
        closes = [c["c"] for c in vis]
        if len(closes) >= 9:
            k = 2 / 10; ema = closes[0]; pts = []
            for idx, v in enumerate(closes):
                ema = v * k + ema * (1 - k)
                pts.append((toX(idx), toY(ema)))
            for i in range(len(pts) - 1):
                self.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                                 fill=YELLOW, width=1)

        # Candles
        for i, c in enumerate(vis):
            x   = toX(i)
            up  = c["c"] >= c["o"]
            col = GREEN if up else RED

            hy = toY(c["h"]); ly = toY(c["l"])
            oy = toY(c["o"]); cy = toY(c["c"])

            self.create_line(x, hy, x, ly, fill=col, width=1)

            body_top = min(oy, cy)
            body_bot = max(oy, cy)
            body_h   = max(body_bot - body_top, 1)

            self.create_rectangle(x - bw/2, body_top, x + bw/2, body_top + body_h,
                                  fill=col, outline=col)

        # Current price line
        cp = cs[-1]["c"]
        py = toY(cp)
        self.create_line(pad_l, py, W - pad_r, py, fill=YELLOW, dash=(4, 4), width=1)
        d = 0 if PAIR_BASES.get(self.pair, 1) > 100 else (3 if PAIR_BASES.get(self.pair, 1) < 2 else 5)
        tag_text = f"{cp:.{d}f}"
        self.create_rectangle(W - pad_r + 1, py - 7, W, py + 7, fill=YELLOW, outline="")
        self.create_text(W - pad_r + 2, py, text=tag_text, anchor="w",
                         font=("Courier New", 7, "bold"), fill="#000000")

# ══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════
class ProfessorApp:
    def __init__(self, root):
        self.root    = root
        self.engine  = SignalEngine()
        self.agent   = tk.StringVar(value="professor@gmail.com")
        self.pair    = tk.StringVar(value="USD/BRL (OTC)")
        self.tf      = tk.StringVar(value="5s")
        self.balance = tk.DoubleVar(value=10000.0)
        self.pnl     = tk.DoubleVar(value=0.0)
        self.wins    = 0
        self.losses  = 0
        self.active_trades = []
        self.analyzing     = False
        self.analysis_step = 0
        self.current_result = None
        self._setup_window()
        self._build_ui()
        self._start_loops()

    # ── Window setup ──────────────────────────────────────────
    def _setup_window(self):
        self.root.title("PROFESSOR IS WATCHING — Trading Bot")
        self.root.configure(bg=BG)
        self.root.geometry("480x900")
        self.root.minsize(440, 800)
        self.root.resizable(True, True)
        try:
            self.root.attributes("-topmost", False)
        except:
            pass

    # ── Full UI Build ─────────────────────────────────────────
    def _build_ui(self):
        # Outer glowing border frame
        outer = tk.Frame(self.root, bg=BORDER_RED, padx=2, pady=2)
        outer.pack(fill="both", expand=True, padx=6, pady=6)

        main = tk.Frame(outer, bg=BG)
        main.pack(fill="both", expand=True)

        self._build_topbar(main)
        self._build_professor_header(main)
        self._build_pair_selector(main)
        self._build_timeframe(main)
        self._build_chart(main)
        self._build_analyze_btn(main)
        self._build_signal_box(main)
        self._build_stats(main)
        self._build_history(main)

    # ── Top bar ───────────────────────────────────────────────
    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=BG2, pady=5)
        bar.pack(fill="x")
        tk.Label(bar, text="AGENT:", bg=BG2, fg=GRAY, font=FONT_AGENT).pack(side="left", padx=(10,2))
        tk.Label(bar, textvariable=self.agent, bg=BG2, fg=RED_BRIGHT, font=FONT_AGENT).pack(side="left")
        tk.Button(bar, text="LOGOUT", bg=BG2, fg=GRAY, font=FONT_AGENT,
                  relief="flat", cursor="hand2", command=self._logout).pack(side="right", padx=10)
        # Balance
        bal_frame = tk.Frame(bar, bg=BG2)
        bal_frame.pack(side="right", padx=8)
        tk.Label(bal_frame, text="LIVE ACCOUNT", bg=BG2, fg=GRAY, font=FONT_AGENT).pack()
        self.bal_label = tk.Label(bal_frame, text="$10,000.00", bg=BG2, fg=GREEN, font=("Courier New", 9, "bold"))
        self.bal_label.pack()

    # ── Professor Header ──────────────────────────────────────
    def _build_professor_header(self, parent):
        hdr = tk.Frame(parent, bg=BG, pady=10)
        hdr.pack(fill="x")

        # ASCII Professor mask (text art)
        mask_art = (
            "    ╔══╦══╗    \n"
            "   ║  ◉  ◉  ║   \n"
            "   ║   ▼▲   ║   \n"
            "    ╚══╩══╝    "
        )
        self.mask_canvas = tk.Canvas(hdr, width=80, height=80, bg=BG,
                                      highlightthickness=0)
        self.mask_canvas.pack()
        self._draw_mask()

        self.title_label = tk.Label(
            hdr,
            text="PROFESSOR IS WATCHING",
            bg=BG, fg=RED,
            font=("Courier New", 16, "bold"),
        )
        self.title_label.pack(pady=(4, 0))
        # Glow animation
        self._glow_phase = 0
        self._animate_title()

    def _draw_mask(self):
        c = self.mask_canvas
        c.delete("all")
        # Hood (red)
        c.create_oval(8, 2, 72, 78, fill="#440000", outline=RED, width=2)
        # Face
        c.create_oval(16, 18, 64, 72, fill="#1a0800", outline=RED2, width=1)
        # Eyes
        c.create_oval(22, 28, 34, 38, fill=RED, outline="")
        c.create_oval(46, 28, 58, 38, fill=RED, outline="")
        c.create_oval(25, 30, 31, 36, fill="#000", outline="")
        c.create_oval(49, 30, 55, 36, fill="#000", outline="")
        # Nose
        c.create_polygon(38, 40, 34, 54, 46, 54, fill="#2a0a00", outline=RED2)
        # Mouth (mustache)
        c.create_arc(22, 52, 58, 68, start=200, extent=140,
                     style="arc", outline=RED2, width=2)
        # Collar
        c.create_polygon(28, 72, 20, 80, 60, 80, 52, 72,
                         fill="#330000", outline=RED2)

    def _animate_title(self):
        self._glow_phase += 1
        colors = [RED, "#ff4444", "#ff6666", "#ff4444", RED, "#cc0000"]
        col = colors[self._glow_phase % len(colors)]
        self.title_label.config(fg=col)
        self.root.after(180, self._animate_title)

    # ── Pair Selector ─────────────────────────────────────────
    def _build_pair_selector(self, parent):
        frm = tk.Frame(parent, bg=BG, padx=14)
        frm.pack(fill="x", pady=(4, 2))
        tk.Label(frm, text="TARGET ASSET", bg=BG, fg=RED,
                 font=("Courier New", 10, "bold")).pack(anchor="w")

        self.pair_combo = ttk.Combobox(
            frm, textvariable=self.pair,
            values=PAIRS, state="readonly",
            font=("Courier New", 12, "bold"),
            width=26
        )
        self.pair_combo.pack(fill="x", pady=(4, 0))
        self.pair_combo.bind("<<ComboboxSelected>>", self._on_pair_change)

        # Style the combobox
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TCombobox",
                         fieldbackground=BG3,
                         background=BG3,
                         foreground=WHITE,
                         selectbackground=RED2,
                         selectforeground=WHITE,
                         arrowcolor=RED,
                         bordercolor=BORDER_RED)
        style.map("TCombobox", fieldbackground=[("readonly", BG3)])

    # ── Timeframe Buttons ─────────────────────────────────────
    def _build_timeframe(self, parent):
        frm = tk.Frame(parent, bg=BG, padx=14)
        frm.pack(fill="x", pady=(8, 2))
        tk.Label(frm, text="TIMEFRAME", bg=BG, fg=RED,
                 font=("Courier New", 10, "bold")).pack(anchor="w", pady=(0, 4))

        self.tf_buttons = {}
        grid = tk.Frame(frm, bg=BG)
        grid.pack(fill="x")

        tfs = TIMEFRAMES
        cols = 5
        for i, tf in enumerate(tfs):
            row = i // cols
            col = i % cols
            is_active = (tf == self.tf.get())
            btn = tk.Button(
                grid, text=tf,
                bg=RED2 if is_active else BG3,
                fg=WHITE if is_active else GRAY,
                font=("Courier New", 10, "bold"),
                relief="flat", cursor="hand2",
                padx=6, pady=4, width=4,
                command=lambda t=tf: self._set_tf(t)
            )
            btn.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
            grid.columnconfigure(col, weight=1)
            self.tf_buttons[tf] = btn

    def _set_tf(self, tf):
        old = self.tf.get()
        self.tf.set(tf)
        if old in self.tf_buttons:
            self.tf_buttons[old].config(bg=BG3, fg=GRAY)
        self.tf_buttons[tf].config(bg=RED2, fg=WHITE)

    # ── Candle Chart ──────────────────────────────────────────
    def _build_chart(self, parent):
        frm = tk.Frame(parent, bg=BORDER_RED, padx=1, pady=1)
        frm.pack(fill="x", padx=14, pady=(8, 4))
        inner = tk.Frame(frm, bg=BG)
        inner.pack(fill="both")
        self.chart = CandleCanvas(inner, self.engine, height=130)
        self.chart.pack(fill="both", expand=True)

    # ── Analyze Button ────────────────────────────────────────
    def _build_analyze_btn(self, parent):
        frm = tk.Frame(parent, bg=BG, padx=14)
        frm.pack(fill="x", pady=(6, 4))
        self.analyze_btn = tk.Button(
            frm,
            text="CHECK PROFESSOR'S PLAN",
            bg=RED2, fg=WHITE,
            font=("Courier New", 12, "bold"),
            relief="flat", cursor="hand2",
            pady=10, width=28,
            activebackground="#880000",
            activeforeground=WHITE,
            command=self._start_analysis
        )
        self.analyze_btn.pack(fill="x")
        self._pulse_btn()

    def _pulse_btn(self):
        colors = [RED2, "#990000", RED2, RED2, "#990000"]
        idx = int(time.time() * 2) % len(colors)
        try:
            self.analyze_btn.config(bg=colors[idx])
        except:
            pass
        self.root.after(500, self._pulse_btn)

    # ── Signal Box ────────────────────────────────────────────
    def _build_signal_box(self, parent):
        frm = tk.Frame(parent, bg=BORDER_RED, padx=1, pady=1)
        frm.pack(fill="x", padx=14, pady=(4, 4))
        self.signal_inner = tk.Frame(frm, bg=BG3)
        self.signal_inner.pack(fill="both")

        # Status message (EVERYTHING IS PLANNED / analyzing dots)
        self.status_label = tk.Label(
            self.signal_inner,
            text="IDLE",
            bg=BG3, fg=GRAY,
            font=("Courier New", 13, "bold"),
            pady=6
        )
        self.status_label.pack(pady=(8, 4))

        # Main signal display
        self.signal_label = tk.Label(
            self.signal_inner,
            text="",
            bg=BG3, fg=GREEN,
            font=("Courier New", 36, "bold"),
            pady=4
        )
        self.signal_label.pack()

        # Confidence bar
        self.conf_frame = tk.Frame(self.signal_inner, bg=BG3)
        self.conf_frame.pack(fill="x", padx=20, pady=(4, 2))

        self.conf_bar_bg = tk.Frame(self.conf_frame, bg=GRAY_DIM, height=8)
        self.conf_bar_bg.pack(fill="x")
        self.conf_bar    = tk.Frame(self.conf_bar_bg, bg=GREEN, height=8)
        self.conf_bar.place(x=0, y=0, relheight=1.0, relwidth=0.87)

        self.conf_label = tk.Label(
            self.signal_inner,
            text="",
            bg=BG3, fg=GRAY,
            font=FONT_SM, pady=2
        )
        self.conf_label.pack(pady=(2, 6))

        # Indicator breakdown
        self.ind_frame = tk.Frame(self.signal_inner, bg=BG3)
        self.ind_frame.pack(fill="x", padx=14, pady=(0, 8))

    # ── Stats row ─────────────────────────────────────────────
    def _build_stats(self, parent):
        frm = tk.Frame(parent, bg=BG2, padx=14, pady=6)
        frm.pack(fill="x")

        stats = [
            ("BALANCE",  lambda: f"${self.balance.get():,.2f}", GREEN),
            ("P&L",      lambda: f"{'+' if self.pnl.get() >= 0 else ''}${self.pnl.get():,.2f}", GREEN),
            ("WIN RATE", lambda: f"{int(self.wins/(self.wins+self.losses)*100) if (self.wins+self.losses) else 0}%", YELLOW),
            ("W/L",      lambda: f"{self.wins}/{self.losses}", WHITE),
        ]
        self.stat_labels = {}
        for col, (name, valfn, col_) in enumerate(stats):
            sf = tk.Frame(frm, bg=BG2)
            sf.grid(row=0, column=col, padx=6, sticky="ew")
            frm.columnconfigure(col, weight=1)
            tk.Label(sf, text=name, bg=BG2, fg=GRAY, font=FONT_XSM).pack()
            lbl = tk.Label(sf, text=valfn(), bg=BG2, fg=col_,
                           font=("Courier New", 10, "bold"))
            lbl.pack()
            self.stat_labels[name] = (lbl, valfn, col_)

    # ── Trade History ─────────────────────────────────────────
    def _build_history(self, parent):
        frm = tk.Frame(parent, bg=BG2, padx=14, pady=6)
        frm.pack(fill="x", pady=(2, 0))
        tk.Label(frm, text="RECENT TRADES", bg=BG2, fg=RED,
                 font=("Courier New", 9, "bold")).pack(anchor="w")

        cols = tk.Frame(frm, bg=BG2)
        cols.pack(fill="x")
        for txt, width in [("PAIR",10),("DIR",6),("RESULT",8),("P&L",8)]:
            tk.Label(cols, text=txt, bg=BG2, fg=GRAY_DIM,
                     font=FONT_XSM, width=width, anchor="w").pack(side="left")

        self.hist_frame = tk.Frame(frm, bg=BG2, height=80)
        self.hist_frame.pack(fill="x")
        self.hist_frame.pack_propagate(False)
        self.hist_rows = []

    # ── Event Handlers ────────────────────────────────────────
    def _on_pair_change(self, event=None):
        pair_str = self.pair.get()
        base = pair_str.replace(" (OTC)", "")
        self.chart.set_pair(pair_str)
        self.status_label.config(text="IDLE", fg=GRAY)
        self.signal_label.config(text="")
        self.conf_label.config(text="")

    def _start_analysis(self):
        if self.analyzing:
            return
        self.analyzing     = True
        self.analysis_step = 0
        self.current_result = None
        self.analyze_btn.config(state="disabled", bg=GRAY_DIM)
        self.signal_label.config(text="")
        self._run_analysis_animation()

    def _run_analysis_animation(self):
        messages = [
            "SCANNING CANDLES...",
            "CALCULATING RSI...",
            "CHECKING MACD...",
            "BOLLINGER BANDS...",
            "STOCH RSI CHECK...",
            "EMA CONFLUENCE...",
            "COMPUTING SIGNAL...",
            "EVERYTHING IS PLANNED..",
        ]

        if self.analysis_step < len(messages):
            dots = "." * ((self.analysis_step % 3) + 1)
            self.status_label.config(
                text=messages[self.analysis_step] + dots,
                fg=YELLOW
            )
            self.analysis_step += 1
            self.root.after(320, self._run_analysis_animation)
        else:
            # Done analyzing
            result = self.engine.analyze(self.pair.get())
            self.current_result = result
            self._show_signal(result)
            self.analyze_btn.config(state="normal", bg=RED2)
            self.analyzing = False

    def _show_signal(self, result):
        direction = result["dir"]
        pct       = result["pct"]

        # Signal text
        if direction == "BUY":
            self.signal_label.config(text="BUY", fg=GREEN)
            self.signal_inner.config(bg="#001a0a")
            self.status_label.config(
                text="EVERYTHING IS PLANNED..", fg=YELLOW,
                bg="#001a0a"
            )
            self.conf_label.config(bg="#001a0a")
            self.conf_frame.config(bg="#001a0a")
            self.conf_bar_bg.config(bg="#002210")
            self.conf_bar.config(bg=GREEN)
            self.ind_frame.config(bg="#001a0a")
        elif direction == "SELL":
            self.signal_label.config(text="SELL", fg=RED)
            self.signal_inner.config(bg="#1a0000")
            self.status_label.config(
                text="EVERYTHING IS PLANNED..", fg=YELLOW,
                bg="#1a0000"
            )
            self.conf_label.config(bg="#1a0000")
            self.conf_frame.config(bg="#1a0000")
            self.conf_bar_bg.config(bg="#2a0000")
            self.conf_bar.config(bg=RED)
            self.ind_frame.config(bg="#1a0000")
        else:
            self.signal_label.config(text="WAIT", fg=YELLOW)
            self.signal_inner.config(bg=BG3)
            self.status_label.config(
                text="MARKET IS UNDECIDED..", fg=YELLOW, bg=BG3
            )
            self.conf_label.config(bg=BG3)
            self.conf_frame.config(bg=BG3)
            self.conf_bar_bg.config(bg=GRAY_DIM)
            self.conf_bar.config(bg=YELLOW)
            self.ind_frame.config(bg=BG3)

        # Confidence bar width
        self.conf_bar.place(relwidth=pct / 100)
        self.conf_label.config(text=f"CONFIDENCE: {pct}%  |  ↑{result['up']} signals  ↓{result['dn']} signals")

        # Indicator breakdown
        for w in self.ind_frame.winfo_children():
            w.destroy()

        bg = self.signal_inner.cget("bg")
        ind_data = [
            ("RSI",    f"{result['rsi']:.1f}",   "BUY" if result['rsi'] < 40 else "SELL" if result['rsi'] > 60 else "NEUT"),
            ("MACD",   f"{result['macd_h']:.5f}", "BUY" if result['macd_h'] > 0 else "SELL"),
            ("Stoch",  f"{result['stoch']:.1f}",  "BUY" if result['stoch'] < 30 else "SELL" if result['stoch'] > 70 else "NEUT"),
            ("EMA",    f"{result['ema9']:.5f}",   "BUY" if result['ema9'] > result['ema20'] else "SELL"),
        ]
        for i, (name, val, sig) in enumerate(ind_data):
            col = GREEN if sig == "BUY" else RED if sig == "SELL" else YELLOW
            row = tk.Frame(self.ind_frame, bg=bg)
            row.pack(fill="x")
            tk.Label(row, text=f"  {name}:", bg=bg, fg=GRAY, font=FONT_XSM, width=7, anchor="w").pack(side="left")
            tk.Label(row, text=val, bg=bg, fg=col,  font=("Courier New", 9, "bold"), width=12).pack(side="left")
            tk.Label(row, text=f"[{sig}]", bg=bg, fg=col, font=FONT_XSM).pack(side="left")

    # ── Loop updates ──────────────────────────────────────────
    def _start_loops(self):
        self._price_loop()
        self._stats_loop()
        self._trades_loop()
        self._clock_loop()

    def _price_loop(self):
        # Update candles for current pair
        base = self.pair.get().replace(" (OTC)", "")
        self.engine._update_candle(base)
        self.root.after(600, self._price_loop)

    def _stats_loop(self):
        bal = self.balance.get()
        pnl = self.pnl.get()
        self.bal_label.config(text=f"${bal:,.2f}",
                               fg=GREEN if bal >= 10000 else RED)
        for name, (lbl, valfn, col_) in self.stat_labels.items():
            val = valfn()
            c   = col_
            if name == "P&L":
                c = GREEN if pnl >= 0 else RED
            elif name == "WIN RATE":
                total = self.wins + self.losses
                wr = self.wins / total * 100 if total else 0
                c = GREEN if wr >= 50 else YELLOW
            lbl.config(text=val, fg=c)
        self.root.after(1000, self._stats_loop)

    def _trades_loop(self):
        now = time.time()
        settled = []
        for trade in self.active_trades:
            if now >= trade["expiry"]:
                settled.append(trade)
        for trade in settled:
            self.active_trades.remove(trade)
            self._settle_trade(trade)
        # Update active trade countdown
        self.root.after(500, self._trades_loop)

    def _settle_trade(self, trade):
        cs = self.engine.candle_history.get(trade["base"], [])
        if not cs:
            return
        exit_price = cs[-1]["c"]
        won = (trade["dir"] == "BUY"  and exit_price > trade["entry"]) or \
              (trade["dir"] == "SELL" and exit_price < trade["entry"])
        payout = trade["amount"] * 0.87
        if won:
            self.balance.set(round(self.balance.get() + trade["amount"] + payout, 2))
            self.pnl.set(round(self.pnl.get() + payout, 2))
            self.wins += 1
            result = f"+${payout:.2f}"
            col = GREEN
        else:
            self.pnl.set(round(self.pnl.get() - trade["amount"], 2))
            self.losses += 1
            result = f"-${trade['amount']:.2f}"
            col = RED
        self._add_history_row(trade["pair_name"], trade["dir"], result, col)

    def _add_history_row(self, pair, direction, result, col):
        row = tk.Frame(self.hist_frame, bg=BG2)
        row.pack(fill="x")
        pair_short = pair.replace(" (OTC)", "")[:10]
        tk.Label(row, text=pair_short, bg=BG2, fg=WHITE, font=FONT_XSM, width=10, anchor="w").pack(side="left")
        dc = GREEN if direction == "BUY" else RED
        tk.Label(row, text=direction, bg=BG2, fg=dc, font=("Courier New", 9, "bold"), width=6, anchor="w").pack(side="left")
        rc = GREEN if result.startswith("+") else RED
        tk.Label(row, text="WIN" if rc==GREEN else "LOSS", bg=BG2, fg=rc, font=FONT_XSM, width=8, anchor="w").pack(side="left")
        tk.Label(row, text=result, bg=BG2, fg=rc, font=("Courier New", 9, "bold"), width=9, anchor="w").pack(side="left")
        self.hist_rows.append(row)
        if len(self.hist_rows) > 4:
            self.hist_rows[0].destroy()
            self.hist_rows.pop(0)

    def _clock_loop(self):
        now = datetime.now().strftime("%H:%M:%S")
        try:
            self.root.title(f"PROFESSOR IS WATCHING  —  {now}")
        except:
            pass
        self.root.after(1000, self._clock_loop)

    def _logout(self):
        if messagebox.askyesno("Logout", "Logout from Professor's system?"):
            self.root.destroy()

# ══════════════════════════════════════════════════════════════
#  TRADE DIALOG (Separate window for placing trades)
# ══════════════════════════════════════════════════════════════
class TradeDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Place Trade")
        self.configure(bg=BG)
        self.geometry("300x280")
        self.resizable(False, False)
        self.grab_set()

        outer = tk.Frame(self, bg=BORDER_RED, padx=2, pady=2)
        outer.pack(fill="both", expand=True, padx=4, pady=4)
        inner = tk.Frame(outer, bg=BG)
        inner.pack(fill="both", expand=True, padx=8, pady=8)

        pair = app.pair.get()
        tf   = app.tf.get()
        direction = app.current_result["dir"] if app.current_result else "BUY"

        col = GREEN if direction == "BUY" else RED

        tk.Label(inner, text=pair, bg=BG, fg=WHITE,
                 font=("Courier New", 13, "bold")).pack(pady=(0,2))
        tk.Label(inner, text=f"Direction: {direction}", bg=BG, fg=col,
                 font=("Courier New", 12, "bold")).pack()
        tk.Label(inner, text=f"Timeframe: {tf}", bg=BG, fg=YELLOW,
                 font=FONT_SM).pack(pady=2)

        tk.Label(inner, text="Amount ($):", bg=BG, fg=GRAY, font=FONT_SM).pack(pady=(10,2))
        self.amount = tk.Entry(inner, font=("Courier New", 14, "bold"),
                               bg=BG3, fg=WHITE, insertbackground=WHITE,
                               justify="center", bd=0, relief="flat")
        self.amount.insert(0, "100")
        self.amount.pack(fill="x", padx=20)

        quick = tk.Frame(inner, bg=BG)
        quick.pack(pady=6)
        for amt in [25, 50, 100, 500]:
            tk.Button(quick, text=f"${amt}", bg=BG3, fg=GRAY, font=FONT_XSM,
                      relief="flat", cursor="hand2", padx=6,
                      command=lambda a=amt: self.amount.delete(0,"end") or self.amount.insert(0,str(a))
                      ).pack(side="left", padx=2)

        btn_col = GREEN if direction == "BUY" else RED
        tk.Button(inner, text=f"CONFIRM {direction}",
                  bg=btn_col, fg="#000" if direction=="BUY" else WHITE,
                  font=("Courier New", 14, "bold"), relief="flat",
                  cursor="hand2", pady=8,
                  command=lambda: self._confirm(direction, pair)
                  ).pack(fill="x", padx=10, pady=(8, 4))

        tk.Button(inner, text="CANCEL", bg=BG3, fg=GRAY,
                  font=FONT_SM, relief="flat", cursor="hand2",
                  command=self.destroy).pack()

    def _confirm(self, direction, pair_name):
        try:
            amount = float(self.amount.get())
        except:
            messagebox.showerror("Error", "Enter valid amount", parent=self)
            return
        if amount < 1:
            messagebox.showerror("Error", "Minimum $1", parent=self)
            return
        if amount > self.app.balance.get():
            messagebox.showerror("Error", "Insufficient balance!", parent=self)
            return

        base = pair_name.replace(" (OTC)", "")
        cs   = self.app.engine.candle_history.get(base, [])
        entry = cs[-1]["c"] if cs else 0
        tf_secs = {"5s":5,"10s":10,"15s":15,"30s":30,"1m":60,
                   "2m":120,"3m":180,"5m":300,"10m":600,"15m":900,
                   "30m":1800,"1h":3600,"4h":14400}
        expiry_sec = tf_secs.get(self.app.tf.get(), 60)

        self.app.balance.set(round(self.app.balance.get() - amount, 2))
        self.app.active_trades.append({
            "pair_name": pair_name,
            "base":      base,
            "dir":       direction,
            "amount":    amount,
            "entry":     entry,
            "expiry":    time.time() + expiry_sec,
        })
        self.destroy()
        messagebox.showinfo("Trade Placed",
                            f"✓ {direction} ${amount:.2f} on {pair_name}\nExpiry: {self.app.tf.get()}",
                            parent=self.app.root)

# ══════════════════════════════════════════════════════════════
#  ADD BUY/SELL BUTTONS TO MAIN APP
# ══════════════════════════════════════════════════════════════
def _add_trade_buttons(app):
    frm = tk.Frame(app.root.winfo_children()[0].winfo_children()[0],
                   bg=BG, padx=14)
    # We'll rebuild — inject after signal box
    pass

# ══════════════════════════════════════════════════════════════
#  ENHANCED APP WITH BUY/SELL
# ══════════════════════════════════════════════════════════════
class ProfessorAppFull(ProfessorApp):
    def _build_ui(self):
        outer = tk.Frame(self.root, bg=BORDER_RED, padx=2, pady=2)
        outer.pack(fill="both", expand=True, padx=6, pady=6)
        main = tk.Frame(outer, bg=BG)
        main.pack(fill="both", expand=True)
        self._main = main

        # Scrollable canvas
        canvas = tk.Canvas(main, bg=BG, highlightthickness=0)
        vsb    = tk.Scrollbar(main, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self._scroll_frame = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())
        self._scroll_frame.bind("<Configure>", _resize)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        # Mouse wheel scroll
        def _scroll(e):
            canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _scroll)

        p = self._scroll_frame
        self._build_topbar(p)
        self._build_professor_header(p)
        self._build_pair_selector(p)
        self._build_timeframe(p)
        self._build_chart(p)
        self._build_analyze_btn(p)
        self._build_signal_box(p)
        self._build_buy_sell(p)
        self._build_stats(p)
        self._build_history(p)

    def _build_buy_sell(self, parent):
        frm = tk.Frame(parent, bg=BG, padx=14, pady=6)
        frm.pack(fill="x")

        # BUY button
        self.buy_btn = tk.Button(
            frm, text="BUY",
            bg=GREEN_DIM, fg=GREEN,
            font=("Courier New", 28, "bold"),
            relief="flat", cursor="hand2",
            pady=12, bd=2,
            activebackground="#003a15",
            activeforeground=GREEN,
            highlightthickness=2,
            highlightbackground=GREEN,
            command=self._place_buy
        )
        self.buy_btn.pack(fill="x", pady=(0, 6))

        # SELL button
        self.sell_btn = tk.Button(
            frm, text="SELL",
            bg="#2a0000", fg=RED,
            font=("Courier New", 28, "bold"),
            relief="flat", cursor="hand2",
            pady=12, bd=2,
            activebackground="#3a0000",
            activeforeground=RED_BRIGHT,
            highlightthickness=2,
            highlightbackground=RED,
            command=self._place_sell
        )
        self.sell_btn.pack(fill="x")

        # Animate BUY/SELL glows
        self._animate_buy_sell()

    def _animate_buy_sell(self):
        phase = int(time.time() * 2) % 4
        if phase < 2:
            try:
                self.buy_btn.config(bg="#004422" if phase == 0 else GREEN_DIM)
                self.sell_btn.config(bg="#2a0000" if phase == 0 else "#1a0000")
            except:
                pass
        self.root.after(500, self._animate_buy_sell)

    def _place_buy(self):
        if not self.current_result:
            messagebox.showinfo("Info", "Click 'CHECK PROFESSOR'S PLAN' first!", parent=self.root)
            return
        self.current_result["dir"] = "BUY"
        TradeDialog(self.root, self)

    def _place_sell(self):
        if not self.current_result:
            messagebox.showinfo("Info", "Click 'CHECK PROFESSOR'S PLAN' first!", parent=self.root)
            return
        self.current_result["dir"] = "SELL"
        TradeDialog(self.root, self)

# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
def main():
    root = tk.Tk()
    app  = ProfessorAppFull(root)
    root.mainloop()

if __name__ == "__main__":
    main()
