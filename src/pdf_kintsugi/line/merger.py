from pdf_kintsugi.utils.coord import is_same
from pdf_kintsugi.utils.union_find import UnionFind


class LineMerger:
    def __init__(self, lines: list[dict], tolerance: float) -> None:
        self.lines: list[dict] = lines
        self.tolerance: float = tolerance

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

        self._infer_table_edges()

        return self.groups

    def _infer_table_edges(self) -> None:
        core_groups = []
        loose_lines = []

        for group in self.groups:
            has_x = any(line["orientation"] == "x" for line in group)
            has_y = any(line["orientation"] == "y" for line in group)
            if has_x and has_y and len(group) > 4:
                core_groups.append(group)
            elif len(group) == 1:
                loose_lines.extend(group)

        for group in core_groups:
            x_lines = [line for line in group if line["orientation"] == "x"]
            y_lines = [line for line in group if line["orientation"] == "y"]

            logical_left = min(line["x0"] for line in x_lines)
            logical_right = max(line["x1"] for line in x_lines)
            logical_top = min(line["top"] for line in y_lines)
            logical_bottom = max(line["bottom"] for line in y_lines)

            # Check y-edges (left and right)
            for target_x in (logical_left, logical_right):
                has_edge = any(is_same(line["x0"], target_x, 1.5) for line in y_lines)

                if not has_edge:
                    found = False
                    for i, loose in enumerate(loose_lines):
                        if loose["orientation"] == "y" and is_same(
                            loose["x0"], target_x, self.tolerance
                        ):
                            overlap = min(loose["bottom"], logical_bottom) - max(
                                loose["top"], logical_top
                            )
                            if overlap > 0:
                                group.append(loose)
                                y_lines.append(loose)
                                loose_lines.pop(i)
                                found = True
                                break
                    if not found:
                        interpolated = {
                            "orientation": "y",
                            "x0": target_x,
                            "x1": target_x,
                            "top": logical_top,
                            "bottom": logical_bottom,
                        }
                        group.append(interpolated)
                        y_lines.append(interpolated)

            # Check x-edges (top and bottom)
            for target_y in (logical_top, logical_bottom):
                has_edge = any(is_same(line["top"], target_y, 1.5) for line in x_lines)
                if not has_edge:
                    found = False
                    for i, loose in enumerate(loose_lines):
                        if loose["orientation"] == "x" and is_same(
                            loose["top"], target_y, self.tolerance
                        ):
                            overlap = min(loose["x1"], logical_right) - max(
                                loose["x0"], logical_left
                            )
                            if overlap > 0:
                                group.append(loose)
                                x_lines.append(loose)
                                loose_lines.pop(i)
                                found = True
                                break
                    if not found:
                        interpolated = {
                            "orientation": "x",
                            "x0": logical_left,
                            "x1": logical_right,
                            "top": target_y,
                            "bottom": target_y,
                        }
                        group.append(interpolated)
                        x_lines.append(interpolated)

        self.groups = core_groups
        if loose_lines:
            self.groups.extend([[line] for line in loose_lines])

    def _is_crossing_lines(self, id1: int, id2: int, tolerance: float = 1.5) -> bool:
        if self.lines[id1]["orientation"] == self.lines[id2]["orientation"]:
            return False

        if self.lines[id1]["orientation"] == "y":
            id1, id2 = id2, id1

        x_line = self.lines[id1]
        y_line = self.lines[id2]

        return (
            x_line["x0"] - tolerance <= y_line["x0"] <= x_line["x1"] + tolerance
            and y_line["top"] - tolerance
            <= x_line["top"]
            <= y_line["bottom"] + tolerance
        )

    def extract_independent_horizontal_lines(self) -> list[dict]:
        independent_horizontal_lines = [
            self.lines[group[0]]
            for group in self.group_ids
            if len(group) == 1 and self.lines[group[0]]["orientation"] == "x"
        ]

        return independent_horizontal_lines
