from collections import deque

#基础规则实现

SIZE = 9
MAX_WALLS = 10


class Quoridor:
    def __init__(self):
        self.horiz_walls = [[False] * (SIZE - 1) for _ in range(SIZE - 1)]
        self.vert_walls = [[False] * (SIZE - 1) for _ in range(SIZE - 1)]
        self.black = (SIZE // 2, 0)
        self.white = (SIZE // 2, SIZE - 1)
        self.walls_remaining = {0: MAX_WALLS, 1: MAX_WALLS}
        self.turn = 0
        self.game_over = False
        self.winner = None
        self.last_action = None

    def copy(self):
        new = Quoridor.__new__(Quoridor)
        new.horiz_walls = [row[:] for row in self.horiz_walls]
        new.vert_walls = [row[:] for row in self.vert_walls]
        new.black = self.black
        new.white = self.white
        new.walls_remaining = dict(self.walls_remaining)
        new.turn = self.turn
        new.game_over = self.game_over
        new.winner = self.winner
        new.last_action = self.last_action
        return new

    def is_h_wall_between(self, x, y):
        if y < 0 or y >= SIZE - 1:
            return False
        if x < 0 or x >= SIZE:
            return False
        if x - 1 >= 0 and self.horiz_walls[y][x - 1]:
            return True
        if x <= SIZE - 2 and self.horiz_walls[y][x]:
            return True
        return False

    def is_v_wall_between(self, x, y):
        if x < 0 or x >= SIZE - 1:
            return False
        if y < 0 or y >= SIZE:
            return False
        if y - 1 >= 0 and self.vert_walls[y - 1][x]:
            return True
        if y <= SIZE - 2 and self.vert_walls[y][x]:
            return True
        return False

    def _wall_present(self, orientation, row, col):
        if orientation == 'h':
            return self.horiz_walls[row][col]
        return self.vert_walls[row][col]

    def can_place_wall(self, orientation, row, col):
        if self.walls_remaining[self.turn] <= 0:
            return False
        if not (0 <= row < SIZE - 1 and 0 <= col < SIZE - 1):
            return False
        if orientation == 'h':
            if self.horiz_walls[row][col]:
                return False
            if (col - 1 >= 0 and self.horiz_walls[row][col - 1]):
                return False
            if (col + 1 < SIZE - 1 and self.horiz_walls[row][col + 1]):
                return False
            if self.vert_walls[row][col]:
                return False
            self.horiz_walls[row][col] = True
            ok = self._both_have_path()
            self.horiz_walls[row][col] = False
            return ok
        else:
            if self.vert_walls[row][col]:
                return False
            if (row - 1 >= 0 and self.vert_walls[row - 1][col]):
                return False
            if (row + 1 < SIZE - 1 and self.vert_walls[row + 1][col]):
                return False
            if self.horiz_walls[row][col]:
                return False
            self.vert_walls[row][col] = True
            ok = self._both_have_path()
            self.vert_walls[row][col] = False
            return ok

    def place_wall(self, orientation, row, col):
        if not self.can_place_wall(orientation, row, col):
            return False
        if orientation == 'h':
            self.horiz_walls[row][col] = True
        else:
            self.vert_walls[row][col] = True
        self.walls_remaining[self.turn] -= 1
        self.last_action = ('wall', orientation, row, col)
        self.switch_turn()
        return True

    def switch_turn(self):
        self.turn = 1 - self.turn

    def current_player_pos(self):
        return self.black if self.turn == 0 else self.white

    def other_player_pos(self):
        return self.white if self.turn == 0 else self.black

    def _set_current(self, pos):
        if self.turn == 0:
            self.black = pos
        else:
            self.white = pos

    def get_legal_moves(self):
        me = self.current_player_pos()
        other = self.other_player_pos()
        results = []
        directions = [('up', 0, -1), ('down', 0, 1),
                      ('left', -1, 0), ('right', 1, 0)]
        for _, dx, dy in directions:
            nx, ny = me[0] + dx, me[1] + dy
            if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                continue
            if dy == 1 and self.is_h_wall_between(me[0], me[1]):
                continue
            if dy == -1 and self.is_h_wall_between(me[0], me[1] - 1):
                continue
            if dx == 1 and self.is_v_wall_between(me[0], me[1]):
                continue
            if dx == -1 and self.is_v_wall_between(me[0] - 1, me[1]):
                continue
            if (nx, ny) == other:
                jx, jy = me[0] + 2 * dx, me[1] + 2 * dy
                jump_ok = False
                if 0 <= jx < SIZE and 0 <= jy < SIZE:
                    blocked = False
                    if dy == 1 and self.is_h_wall_between(other[0], other[1]):
                        blocked = True
                    if dy == -1 and self.is_h_wall_between(other[0],
                                                           other[1] - 1):
                        blocked = True
                    if dx == 1 and self.is_v_wall_between(other[0], other[1]):
                        blocked = True
                    if dx == -1 and self.is_v_wall_between(other[0] - 1,
                                                           other[1]):
                        blocked = True
                    if not blocked:
                        jump_ok = True
                if jump_ok:
                    results.append((jx, jy))
                else:
                    if dx != 0:
                        side_cands = [(0, -1), (0, 1)]
                    else:
                        side_cands = [(-1, 0), (1, 0)]
                    for sx, sy in side_cands:
                        tx, ty = other[0] + sx, other[1] + sy
                        if not (0 <= tx < SIZE and 0 <= ty < SIZE):
                            continue
                        blocked = False
                        if sy == 1 and self.is_h_wall_between(other[0],
                                                              other[1]):
                            blocked = True
                        if sy == -1 and self.is_h_wall_between(other[0],
                                                                other[1] - 1):
                            blocked = True
                        if sx == 1 and self.is_v_wall_between(other[0],
                                                              other[1]):
                            blocked = True
                        if sx == -1 and self.is_v_wall_between(other[0] - 1,
                                                               other[1]):
                            blocked = True
                        if blocked:
                            continue
                        results.append((tx, ty))
            else:
                results.append((nx, ny))
        return results

    def move(self, dest):
        if self.game_over:
            return False
        if dest not in self.get_legal_moves():
            return False
        self._set_current(dest)
        self.last_action = ('move', dest[0], dest[1])
        if self.turn == 0 and self.black[1] == SIZE - 1:
            self.game_over = True
            self.winner = 0
        elif self.turn == 1 and self.white[1] == 0:
            self.game_over = True
            self.winner = 1
        else:
            self.switch_turn()
        return True

    def apply_action(self, action):
        if self.game_over:
            return False
        kind = action[0]
        if kind == 'move':
            _, x, y = action
            return self.move((x, y))
        if kind == 'wall':
            _, orientation, row, col = action
            return self.place_wall(orientation, row, col)
        return False

    def get_legal_walls(self, orientation):
        res = []
        for r in range(SIZE - 1):
            for c in range(SIZE - 1):
                if self.can_place_wall(orientation, r, c):
                    res.append((r, c))
        return res

    def get_legal_actions(self):
        actions = [('move', x, y) for (x, y) in self.get_legal_moves()]
        for r in range(SIZE - 1):
            for c in range(SIZE - 1):
                if self.can_place_wall('h', r, c):
                    actions.append(('wall', 'h', r, c))
                if self.can_place_wall('v', r, c):
                    actions.append(('wall', 'v', r, c))
        return actions

    def is_terminal(self):
        return self.game_over

    def get_winner(self):
        return self.winner

    def get_turn_name(self):
        return '黑方' if self.turn == 0 else '白方'

    def _both_have_path(self):
        return (self._has_path_to_goal(self.black, SIZE - 1)
                and self._has_path_to_goal(self.white, 0))

    def _has_path_to_goal(self, start, goal_row):
        sx, sy = start
        if sy == goal_row:
            return True
        visited = [[False] * SIZE for _ in range(SIZE)]
        q = deque()
        q.append((sx, sy))
        visited[sy][sx] = True
        while q:
            x, y = q.popleft()
            neighbors = []
            if y > 0 and not self.is_h_wall_between(x, y - 1):
                neighbors.append((x, y - 1))
            if y < SIZE - 1 and not self.is_h_wall_between(x, y):
                neighbors.append((x, y + 1))
            if x > 0 and not self.is_v_wall_between(x - 1, y):
                neighbors.append((x - 1, y))
            if x < SIZE - 1 and not self.is_v_wall_between(x, y):
                neighbors.append((x + 1, y))
            for nx, ny in neighbors:
                if ny == goal_row:
                    return True
                if not visited[ny][nx]:
                    visited[ny][nx] = True
                    q.append((nx, ny))
        return False
