from pdf_kintsugi.utils.coord import is_same
from pdf_kintsugi.utils.union_find import UnionFind


class LineMerger:
    def __init__(self, lines: list[dict], tolerance: float) -> None:
        self.lines: list[dict] = lines
        self.tol: float = tolerance

    def merge(self) -> list[list[dict]]:
        line_num = len(self.lines)
        uf = UnionFind(line_num)

        for i in range(line_num):
            for j in range(i + 1, line_num):
                if self._is_crossing_lines(i, j):
                    uf.merge(i, j)

        self.group_ids: list[list[int]] = uf.groups()
        self.groups: list[list[dict]] = [
            [self.lines[id] for id in group] for group in self.group_ids
        ]

        self._interpolate_missing_edges()

        return self.groups

    def _interpolate_missing_edges(self) -> None:
        """edge が存在しないテーブルに仮想 line を補間する"""
        for group in self.groups:
            x_lines = [line for line in group if line["orientation"] == "x"]
            y_lines = [line for line in group if line["orientation"] == "y"]
            if not (x_lines and y_lines):
                continue

            logical_left = min(line["x0"] for line in x_lines)
            logical_right = max(line["x1"] for line in x_lines)
            logical_top = min(line["top"] for line in y_lines)
            logical_bottom = max(line["bottom"] for line in y_lines)

            # Check y-edges (left and right)
            for target_x in (logical_left, logical_right):
                has_edge = any(
                    is_same(line["x0"], target_x, self.tol) for line in y_lines
                )
                if not has_edge:
                    group.append(
                        {
                            "orientation": "y",
                            "x0": target_x,
                            "x1": target_x,
                            "top": logical_top,
                            "bottom": logical_bottom,
                        }
                    )

            # Check x-edges (top and bottom)
            for target_y in (logical_top, logical_bottom):
                has_edge = any(
                    is_same(line["top"], target_y, self.tol) for line in x_lines
                )
                if not has_edge:
                    group.append(
                        {
                            "orientation": "x",
                            "x0": logical_left,
                            "x1": logical_right,
                            "top": target_y,
                            "bottom": target_y,
                        }
                    )

    def _is_crossing_lines(self, id1: int, id2: int) -> bool:
        if self.lines[id1]["orientation"] == self.lines[id2]["orientation"]:
            return False

        if self.lines[id1]["orientation"] == "y":
            id1, id2 = id2, id1

        x_line = self.lines[id1]
        y_line = self.lines[id2]

        return (
            x_line["x0"] - self.tol <= y_line["x0"] <= x_line["x1"] + self.tol
            and y_line["top"] - self.tol <= x_line["top"] <= y_line["bottom"] + self.tol
        )

    def extract_independent_horizontal_lines(self) -> list[dict]:
        independent_horizontal_lines = [
            self.lines[group[0]]
            for group in self.group_ids
            if len(group) == 1 and self.lines[group[0]]["orientation"] == "x"
        ]

        return independent_horizontal_lines
