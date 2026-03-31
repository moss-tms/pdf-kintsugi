import bisect


class CharAssigner:
    def __init__(
        self, chars: list[dict], x_coords: list[float], y_coords: list[float]
    ) -> None:
        self.chars = chars
        self.x_coords = x_coords
        self.y_coords = y_coords
        self.column_num = len(x_coords) - 1
        self.row_num = len(y_coords) - 1

    def assign(self) -> dict[int, list[dict]]:
        assigned_chars: dict[int, list[dict]] = {
            i: [] for i in range(self.row_num * self.column_num)
        }

        for ch in self.chars:
            cx = ch.get("x")
            cy = ch.get("y")

            if cx is None or cy is None:
                continue

            cx_float = float(cx)
            cy_float = float(cy)

            # 使用するx_coords, y_coordsは重複なしのソート済みであることを前提とする
            col_idx = bisect.bisect_right(self.x_coords, cx_float) - 1
            row_idx = bisect.bisect_right(self.y_coords, cy_float) - 1

            # セル境界（外側）の判定
            # bisect_right の結果が 0 になった場合は最小値より左
            # column_num以上になったら最大値より右
            if 0 <= col_idx < self.column_num and 0 <= row_idx < self.row_num:
                cell_id = row_idx * self.column_num + col_idx
                assigned_chars[cell_id].append(ch)

        return assigned_chars
