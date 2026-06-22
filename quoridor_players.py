import random
import math
import time
from collections import deque, OrderedDict

from quoridor_core import Quoridor, SIZE

#用户接口，包括人类与AI（AI实现为主，人类的控制实现主要在quoridor.py中）

def _bfs_distance(state, start_cell, goal_row):
    sx, sy = start_cell
    if sy == goal_row:
        return 0
    visited = [[False] * SIZE for _ in range(SIZE)]
    visited[sy][sx] = True
    q = deque([(sx, sy, 0)])
    while q:
        x, y, d = q.popleft()
        neighbors = []
        if y > 0 and not state.is_h_wall_between(x, y - 1):
            neighbors.append((x, y - 1))
        if y < SIZE - 1 and not state.is_h_wall_between(x, y):
            neighbors.append((x, y + 1))
        if x > 0 and not state.is_v_wall_between(x - 1, y):
            neighbors.append((x - 1, y))
        if x < SIZE - 1 and not state.is_v_wall_between(x, y):
            neighbors.append((x + 1, y))
        for nx, ny in neighbors:
            if ny == goal_row:
                return d + 1
            if not visited[ny][nx]:
                visited[ny][nx] = True
                q.append((nx, ny, d + 1))
    return SIZE * 2


def _bfs_distance_and_path(state, start_cell, goal_row):
    sx, sy = start_cell
    if sy == goal_row:
        return 0, None
    visited = [[False] * SIZE for _ in range(SIZE)]
    parent = [[None] * SIZE for _ in range(SIZE)]
    visited[sy][sx] = True
    q = deque([(sx, sy, 0)])
    found = None
    while q and found is None:
        x, y, d = q.popleft()
        neighbors = []
        if y > 0 and not state.is_h_wall_between(x, y - 1):
            neighbors.append((x, y - 1))
        if y < SIZE - 1 and not state.is_h_wall_between(x, y):
            neighbors.append((x, y + 1))
        if x > 0 and not state.is_v_wall_between(x - 1, y):
            neighbors.append((x - 1, y))
        if x < SIZE - 1 and not state.is_v_wall_between(x, y):
            neighbors.append((x + 1, y))
        for nx, ny in neighbors:
            if visited[ny][nx]:
                continue
            visited[ny][nx] = True
            parent[ny][nx] = (x, y)
            if ny == goal_row:
                found = (nx, ny)
                break
            q.append((nx, ny, d + 1))
    if found is None:
        return SIZE * 2, None
    cur = found
    nxt = None
    while cur is not None and parent[cur[1]][cur[0]] is not None:
        nxt = cur
        cur = parent[cur[1]][cur[0]]
    dist = 0
    cur = found
    while parent[cur[1]][cur[0]] is not None:
        dist += 1
        cur = parent[cur[1]][cur[0]]
    return dist, nxt


class Player:
    display_name = "Player"
    is_human = False

    def choose_action(self, game: Quoridor):
        raise NotImplementedError


class HumanPlayer(Player):
    display_name = "人类玩家"
    is_human = True

    def choose_action(self, game: Quoridor):
        raise RuntimeError("HumanPlayer.choose_action 不应被调用。")


class MinimaxAI(Player):
    display_name = "Minimax AI"
    is_human = False

    def __init__(self, time_budget_s=3.0, max_depth=5,
                 top_moves=4, top_walls=5):
        self.time_budget = time_budget_s
        self.max_depth = max_depth
        self.top_moves = top_moves
        self.top_walls = top_walls
        self._last_pos = None

    def choose_action(self, game: Quoridor):
        self._me = game.turn
        self._goal = {0: SIZE - 1, 1: 0}[self._me]
        self._opp_goal = SIZE - 1 if self._me == 1 else 0

        self._start_time = time.time()
        best_action = self._default_action(game)

        for depth in range(1, self.max_depth + 1):
            try:
                score, action = self._search(
                    game, depth, alpha=-math.inf, beta=math.inf,
                    maximizing=True, deadline=self._start_time + self.time_budget,
                )
            except TimeoutError:
                break
            if action is not None:
                best_action = action
            if time.time() - self._start_time > self.time_budget:
                break

        if best_action and best_action[0] == 'move':
            self._last_pos = (best_action[1], best_action[2])
        return best_action

    def _default_action(self, game):
        legal = game.get_legal_actions()
        goal = SIZE - 1 if game.turn == 0 else 0
        my_cur_d = _bfs_distance(game, game.current_player_pos(), goal)
        moves = [a for a in legal if a[0] == 'move']
        if moves:
            scored = []
            for a in moves:
                d = _bfs_distance(game, (a[1], a[2]), goal)
                progress = my_cur_d - d
                scored.append((-progress, d, a))
            scored.sort()
            _, _, best = scored[0]
            return best
        return legal[0] if legal else None

    def _candidate_actions(self, game, top_moves=None, top_walls=None):
        tm = top_moves if top_moves is not None else self.top_moves
        tw = top_walls if top_walls is not None else self.top_walls
        me = game.turn
        my_goal = SIZE - 1 if me == 0 else 0
        opp_goal = 0 if me == 0 else SIZE - 1

        my_cur = game.black if me == 0 else game.white
        opp_cur = game.white if me == 0 else game.black
        my_cur_d = _bfs_distance(game, my_cur, my_goal)
        opp_cur_d = _bfs_distance(game, opp_cur, opp_goal)

        actions = []
        moves = game.get_legal_moves()
        if moves:
            scored = []
            for (x, y) in moves:
                d = _bfs_distance(game, (x, y), my_goal)
                progress = my_cur_d - d
                scored.append((-progress, d, x, y))
            scored.sort()
            for _, d, x, y in scored[:tm]:
                actions.append(('move', x, y))

        if game.walls_remaining[me] > 0:
            opp_positions_to_consider = [opp_cur]
            _, nxt = _bfs_distance_and_path(game, opp_cur, opp_goal)
            if nxt is not None:
                opp_positions_to_consider.append(nxt)
            my_positions_for_defense = [my_cur]
            _, my_nxt = _bfs_distance_and_path(game, my_cur, my_goal)
            if my_nxt is not None:
                my_positions_for_defense.append(my_nxt)

            candidates_walls = set()
            for px, py in opp_positions_to_consider + my_positions_for_defense:
                for r in range(max(0, py - 2), min(SIZE - 1, py + 2)):
                    for c in range(max(0, px - 2), min(SIZE - 1, px + 2)):
                        for orient in ('h', 'v'):
                            if game.can_place_wall(orient, r, c):
                                candidates_walls.add((orient, r, c))
            wall_scores = []
            for orient, r, c in candidates_walls:
                if orient == 'h':
                    game.horiz_walls[r][c] = True
                else:
                    game.vert_walls[r][c] = True
                new_opp_d = _bfs_distance(game, opp_cur, opp_goal)
                new_my_d = _bfs_distance(game, my_cur, my_goal)
                if orient == 'h':
                    game.horiz_walls[r][c] = False
                else:
                    game.vert_walls[r][c] = False
                opp_gain = new_opp_d - opp_cur_d
                my_loss = new_my_d - my_cur_d
                net_gain = opp_gain - my_loss * 0.8
                if net_gain > 0:
                    wall_scores.append((-net_gain, orient, r, c))
            wall_scores.sort()
            for _, orient, r, c in wall_scores[:tw]:
                actions.append(('wall', orient, r, c))
        return actions

    def _action_score(self, game, action):
        child = game.copy()
        ok = child.apply_action(action)
        if not ok:
            return -99999
        child_pos = child.black if self._me == 0 else child.white
        child_opp = child.white if self._me == 0 else child.black
        child_d = _bfs_distance(child, child_pos, self._goal)
        opp_d = _bfs_distance(child, child_opp, self._opp_goal)
        return -child_d * 100 + opp_d * 30

    def _search(self, game, depth, alpha, beta, maximizing, deadline):
        if time.time() > deadline:
            raise TimeoutError()
        if depth == 0 or game.is_terminal():
            return self._evaluate_from_me(game), None

        actions = self._candidate_actions(game)
        if not actions:
            return self._evaluate_from_me(game), None

        best_action = None
        best_tiebreak = -math.inf
        if maximizing:
            best = -math.inf
            for action in actions:
                if time.time() > deadline:
                    raise TimeoutError()
                child = game.copy()
                ok = child.apply_action(action)
                if not ok:
                    continue
                value, _ = self._search(child, depth - 1,
                                        alpha, beta,
                                        not maximizing, deadline)
                tiebreak = self._action_score(game, action)
                if value > best or (value == best and tiebreak > best_tiebreak):
                    best = value
                    best_action = action
                    best_tiebreak = tiebreak
                alpha = max(alpha, best)
                if alpha >= beta:
                    break
            return best, best_action
        else:
            best = math.inf
            for action in actions:
                if time.time() > deadline:
                    raise TimeoutError()
                child = game.copy()
                ok = child.apply_action(action)
                if not ok:
                    continue
                value, _ = self._search(child, depth - 1,
                                        alpha, beta,
                                        not maximizing, deadline)
                tiebreak = -self._action_score(game, action)
                if value < best or (value == best and tiebreak > best_tiebreak):
                    best = value
                    best_action = action
                    best_tiebreak = tiebreak
                beta = min(beta, best)
                if alpha >= beta:
                    break
            return best, best_action

    def _evaluate_from_me(self, game):
        my_pos = game.black if self._me == 0 else game.white
        opp_pos = game.white if self._me == 0 else game.black
        my_goal = self._goal
        opp_goal = self._opp_goal

        if my_pos[1] == my_goal:
            return 10000
        if opp_pos[1] == opp_goal:
            return -10000

        my_d = _bfs_distance(game, my_pos, my_goal)
        opp_d = _bfs_distance(game, opp_pos, opp_goal)
        wall_bonus = game.walls_remaining[self._me] - game.walls_remaining[1 - self._me]
        return opp_d-my_d


AVAILABLE_PLAYERS = OrderedDict([
    ("人类玩家", HumanPlayer),
    ("Minimax AI", MinimaxAI),
])


def load_player(name):
    cls = AVAILABLE_PLAYERS.get(name)
    if cls is None:
        raise ValueError(f"未知玩家类型: {name}")
    return cls()
