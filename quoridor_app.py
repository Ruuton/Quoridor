import tkinter as tk
from tkinter import ttk, messagebox

from quoridor_core import Quoridor, SIZE
from quoridor_players import (
    Player, HumanPlayer,
    MinimaxAI, AVAILABLE_PLAYERS,
)

#GUI实现和入口

CELL = 60
WALL_THICK = 10
MARGIN = 40
AI_PAUSE_MS = 350


# ============ 配置对话框 ============
class ConfigDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("对局配置")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.result_black = None
        self.result_white = None

        tk.Label(self, text="选择双方玩家",
                 font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(12, 8), padx=16)

        names = list(AVAILABLE_PLAYERS.keys())

        tk.Label(self, text="黑方（先手）：").grid(row=1, column=0,
                                                      sticky="e", padx=8,
                                                      pady=4)
        self.var_black = tk.StringVar(value="人类玩家" if "人类玩家"
                                      in names else names[0])
        self.menu_black = ttk.Combobox(self, values=names,
                                       textvariable=self.var_black,
                                       state="readonly", width=18)
        self.menu_black.grid(row=1, column=1, sticky="w", pady=4)

        tk.Label(self, text="白方（后手）：").grid(row=2, column=0,
                                                      sticky="e", padx=8,
                                                      pady=4)
        self.var_white = tk.StringVar(value="人类玩家" if "人类玩家"
                                      in names else names[0])
        self.menu_white = ttk.Combobox(self, values=names,
                                       textvariable=self.var_white,
                                       state="readonly", width=18)
        self.menu_white.grid(row=2, column=1, sticky="w", pady=4)

        btns = tk.Frame(self)
        btns.grid(row=3, column=0, columnspan=2, pady=(12, 12))
        tk.Button(btns, text="开始对局", width=12,
                  command=self._on_start).pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="取消", width=8,
                  command=self._on_cancel).pack(side=tk.LEFT, padx=6)

        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    def _on_start(self):
        self.result_black = self.var_black.get()
        self.result_white = self.var_white.get()
        self.destroy()

    def _on_cancel(self):
        self.result_black = None
        self.result_white = None
        self.destroy()


# ============ 主应用 ============
class QuoridorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quoridor")

        # 顶部状态条
        self.top = tk.Frame(root)
        self.top.pack(pady=(10, 4), fill=tk.X, padx=12)
        self.lbl_turn = tk.Label(self.top, text="", font=("Arial", 13, "bold"))
        self.lbl_turn.pack(side=tk.LEFT, padx=8)
        self.lbl_info = tk.Label(self.top, text="", font=("Arial", 11))
        self.lbl_info.pack(side=tk.LEFT, padx=16)
        tk.Button(self.top, text="重置 / 新对局",
                  command=self.reset_game).pack(side=tk.RIGHT)

        # 模式面板
        self.mode_panel = tk.Frame(root)
        self.mode_panel.pack(pady=2)
        tk.Label(self.mode_panel, text="输入模式：",
                 font=("Arial", 11)).pack(side=tk.LEFT, padx=4)
        self.mode = tk.StringVar(value="move")
        for label, value in [("移动", "move"),
                             ("水平墙", "wall_h"),
                             ("垂直墙", "wall_v")]:
            tk.Radiobutton(self.mode_panel, text=label,
                           variable=self.mode, value=value,
                           command=self._on_mode_change).pack(side=tk.LEFT)

        # 画布
        dim = MARGIN * 2 + CELL * SIZE
        self.canvas = tk.Canvas(root, width=dim, height=dim,
                                bg="#f0e6d2", highlightthickness=0)
        self.canvas.pack(pady=(4, 2))

        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # 状态栏
        self.status = tk.Label(root, text="", font=("Arial", 10),
                               anchor="w")
        self.status.pack(fill=tk.X, pady=(0, 10), padx=16)

        # 游戏运行状态
        self.game = None
        self._players = [None, None]
        self._player_names = ["", ""]
        self._ai_pending = False
        self._ai_stopped = False
        self._pending_after_id = None
        self.ghost_cell = None
        self.ghost_wall = None

        self.root.after(100, self.reset_game)

    # -------- 生命周期 --------
    def reset_game(self):
        self._ai_stopped = True
        if self._pending_after_id is not None:
            try:
                self.root.after_cancel(self._pending_after_id)
            except Exception:
                pass
            self._pending_after_id = None

        dlg = ConfigDialog(self.root)
        if dlg.result_black is None or dlg.result_white is None:
            self.game = Quoridor()
            self._players = [HumanPlayer(), HumanPlayer()]
            self._player_names = ["人类玩家", "人类玩家"]
            self._ai_pending = False
            self._ai_stopped = False
            self.draw_static()
            self.draw_game()
            self.update_status("已取消配置 — 使用默认（人人对局）。")
            return

        black_cls = AVAILABLE_PLAYERS[dlg.result_black]
        white_cls = AVAILABLE_PLAYERS[dlg.result_white]
        self._players = [black_cls(), white_cls()]
        self._player_names = [dlg.result_black, dlg.result_white]

        self.game = Quoridor()
        self._ai_pending = False
        self._ai_stopped = False
        self.ghost_cell = None
        self.ghost_wall = None

        self.draw_static()
        self.draw_game()
        self.update_status("对局开始：黑方=%s，白方=%s" %
                            tuple(self._player_names))
        self._pending_after_id = self.root.after(50,
                                                  self.process_current_turn)

    # -------- 主回合处理 --------
    def process_current_turn(self):
        if self._ai_stopped:
            return
        if self.game is None or self.game.is_terminal():
            self._show_game_over()
            return
        player = self._players[self.game.turn]

        if player.is_human:
            self.ghost_cell = None
            self.ghost_wall = None
            self.draw_game()
            return

        if self._ai_pending:
            return
        self._ai_pending = True
        self.update_status("%s 正在思考…" % player.display_name)
        self.root.update_idletasks()

        try:
            action = player.choose_action(self.game.copy())
        except Exception as exc:
            self._ai_pending = False
            self.update_status("AI 抛出异常: %s" % exc)
            return

        if self._ai_stopped:
            self._ai_pending = False
            return

        if action is None:
            self._ai_pending = False
            self.update_status("AI 未返回动作（跳过）。")
            return

        ok = self.game.apply_action(action)
        self._ai_pending = False
        if not ok:
            self.update_status("AI 返回的动作不合法，已跳过: %r" % (action,))
        else:
            self.update_status("%s：%s" % (player.display_name,
                                           self._describe_action(action)))
        self.draw_game()

        if self._ai_stopped:
            return
        if self.game.is_terminal():
            self._pending_after_id = self.root.after(
                AI_PAUSE_MS, self._show_game_over)
        else:
            self._pending_after_id = self.root.after(
                AI_PAUSE_MS, self.process_current_turn)

    # -------- 绘制：分层 --------
    def draw_static(self):
        self.canvas.delete("all")
        for y in range(SIZE):
            for x in range(SIZE):
                px = MARGIN + x * CELL
                py = MARGIN + y * CELL
                self.canvas.create_rectangle(
                    px, py, px + CELL, py + CELL,
                    fill="#f5ecd9", outline="#6b4a2b", width=1,
                    tags=("static",))

        for x in range(SIZE):
            px, py = MARGIN + x * CELL, MARGIN + 0 * CELL
            self.canvas.create_rectangle(
                px + 3, py + 3, px + CELL - 3, py + CELL - 3,
                fill="#eadfbf", outline="", tags=("static",))
            px, py = MARGIN + x * CELL, MARGIN + (SIZE - 1) * CELL
            self.canvas.create_rectangle(
                px + 3, py + 3, px + CELL - 3, py + CELL - 3,
                fill="#cfe0cf", outline="", tags=("static",))

        self.canvas.tag_lower("static")

    def draw_game(self):
        if self.game is None:
            return

        self.canvas.delete("walls")
        self.canvas.delete("pieces")

        for r in range(SIZE - 1):
            for c in range(SIZE - 1):
                if self.game.horiz_walls[r][c]:
                    x1 = MARGIN + c * CELL
                    y1 = MARGIN + (r + 1) * CELL - WALL_THICK // 2
                    x2 = MARGIN + (c + 2) * CELL
                    y2 = MARGIN + (r + 1) * CELL + WALL_THICK // 2
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#4a2e12",
                        outline="#4a2e12", tags=("walls",))
                if self.game.vert_walls[r][c]:
                    x1 = MARGIN + (c + 1) * CELL - WALL_THICK // 2
                    y1 = MARGIN + r * CELL
                    x2 = MARGIN + (c + 1) * CELL + WALL_THICK // 2
                    y2 = MARGIN + (r + 2) * CELL
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#4a2e12",
                        outline="#4a2e12", tags=("walls",))

        player = self._players[self.game.turn]
        if player.is_human and self.mode.get() == "move" \
                and not self._ai_pending:
            for (x, y) in self.game.get_legal_moves():
                px, py = MARGIN + x * CELL, MARGIN + y * CELL
                self.canvas.create_rectangle(
                    px + 6, py + 6, px + CELL - 6, py + CELL - 6,
                    outline="#2a7a2a", width=2, dash=(4, 3),
                    tags=("pieces", "hint"))

        for pos, label in [(self.game.black, "黑"),
                           (self.game.white, "白")]:
            px, py = pos
            cx = MARGIN + px * CELL + CELL // 2
            cy = MARGIN + py * CELL + CELL // 2
            r = CELL // 2 - 6
            fill = "#222" if label == "黑" else "#fafafa"
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=fill, outline="#222", width=2, tags=("pieces",))
            text_col = "white" if label == "黑" else "black"
            self.canvas.create_text(cx, cy, text=label,
                                    fill=text_col,
                                    font=("Arial", 15, "bold"),
                                    tags=("pieces",))

        if self.game.is_terminal():
            winner = "黑方" if self.game.get_winner() == 0 else "白方"
            self.lbl_turn.config(text="对局结束：%s 获胜" % winner)
        else:
            side = "黑方" if self.game.turn == 0 else "白方"
            who = self._player_names[self.game.turn]
            self.lbl_turn.config(text="当前回合：%s（%s）" % (side, who))
        self.lbl_info.config(
            text="剩余墙壁：黑方 %d，白方 %d"
                 % (self.game.walls_remaining[0],
                    self.game.walls_remaining[1]))

    def draw_ghost(self):
        self.canvas.delete("ghost")
        if self.game is None or self.game.is_terminal() or self._ai_pending:
            return
        player = self._players[self.game.turn]
        if not player.is_human:
            return

        mode = self.mode.get()
        if mode == "move" and self.ghost_cell is not None:
            if self.ghost_cell in self.game.get_legal_moves():
                color = "#78d678"
            else:
                color = "#e08a8a"
            x, y = self.ghost_cell
            px = MARGIN + x * CELL
            py = MARGIN + y * CELL
            self.canvas.create_oval(
                px + 10, py + 10, px + CELL - 10, py + CELL - 10,
                fill=color, outline="", stipple="gray50", tags=("ghost",))
        elif mode in ("wall_h", "wall_v") and self.ghost_wall is not None:
            orient = "h" if mode == "wall_h" else "v"
            row, col = self.ghost_wall
            ok = self.game.can_place_wall(orient, row, col)
            color = "#78d678" if ok else "#e08a8a"
            if orient == "h":
                x1 = MARGIN + col * CELL
                y1 = MARGIN + (row + 1) * CELL - WALL_THICK // 2
                x2 = MARGIN + (col + 2) * CELL
                y2 = MARGIN + (row + 1) * CELL + WALL_THICK // 2
            else:
                x1 = MARGIN + (col + 1) * CELL - WALL_THICK // 2
                y1 = MARGIN + row * CELL
                x2 = MARGIN + (col + 1) * CELL + WALL_THICK // 2
                y2 = MARGIN + (row + 2) * CELL
            self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=color, outline="",
                stipple="gray50", tags=("ghost",))

    # -------- 鼠标事件 --------
    def _pixel_to_cell(self, px, py):
        x = (px - MARGIN) // CELL
        y = (py - MARGIN) // CELL
        if 0 <= x < SIZE and 0 <= y < SIZE:
            return x, y
        return None

    def _pixel_to_wall_slot(self, px, py):
        col = int(round((px - MARGIN) / CELL - 0.5))
        row = int(round((py - MARGIN) / CELL - 0.5))
        if 0 <= row < SIZE - 1 and 0 <= col < SIZE - 1:
            return row, col
        return None

    def _on_mode_change(self):
        self.ghost_cell = None
        self.ghost_wall = None
        self.draw_game()

    def on_leave(self, _event):
        if self.game is None or self.game.is_terminal() or self._ai_pending:
            return
        self.ghost_cell = None
        self.ghost_wall = None
        self.draw_ghost()

    def on_mouse_move(self, event):
        if self.game is None or self.game.is_terminal() or self._ai_pending:
            return
        player = self._players[self.game.turn]
        if not player.is_human:
            return

        mode = self.mode.get()
        if mode == "move":
            cell = self._pixel_to_cell(event.x, event.y)
            if cell != self.ghost_cell:
                self.ghost_cell = cell
                self.ghost_wall = None
                self.draw_ghost()
        else:
            slot = self._pixel_to_wall_slot(event.x, event.y)
            if slot != self.ghost_wall:
                self.ghost_wall = slot
                self.ghost_cell = None
                self.draw_ghost()

    def on_canvas_click(self, event):
        if self.game is None or self.game.is_terminal() or self._ai_pending:
            return
        player = self._players[self.game.turn]
        if not player.is_human:
            self.update_status("现在是 %s 的回合，点击无效。"
                                % player.display_name)
            return

        mode = self.mode.get()
        if mode == "move":
            cell = self._pixel_to_cell(event.x, event.y)
            if cell is None:
                return
            if cell not in self.game.get_legal_moves():
                self.update_status("该格不是合法移动目标。")
                return
            action = ("move", cell[0], cell[1])
        else:
            slot = self._pixel_to_wall_slot(event.x, event.y)
            if slot is None:
                return
            orient = "h" if mode == "wall_h" else "v"
            if self.game.walls_remaining[self.game.turn] <= 0:
                self.update_status("墙壁已用完。")
                return
            if not self.game.can_place_wall(orient, slot[0], slot[1]):
                self.update_status("该位置无法放墙（重叠或会堵死路径）。")
                return
            action = ("wall", orient, slot[0], slot[1])

        ok = self.game.apply_action(action)
        if ok:
            self.update_status("%s：%s" % (player.display_name,
                                           self._describe_action(action)))
        self.ghost_cell = None
        self.ghost_wall = None
        self.draw_game()
        self.process_current_turn()

    # -------- 工具 --------
    def update_status(self, msg):
        self.status.config(text=msg)

    def _show_game_over(self):
        winner = "黑方" if self.game.get_winner() == 0 else "白方"
        self.draw_game()
        messagebox.showinfo("游戏结束", "%s 获胜！" % winner)

    def _describe_action(self, action):
        if action[0] == "move":
            return "移动到 (%d, %d)" % (action[1], action[2])
        orient_s = "水平" if action[1] == "h" else "垂直"
        return "放%s墙于 (row=%d, col=%d)" % (orient_s, action[2], action[3])


# ============ 入口 ============
def main():
    root = tk.Tk()
    QuoridorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
