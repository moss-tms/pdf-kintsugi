from operator import itemgetter

from pdfplumber.page import Page


class LineExtractor:
    def __init__(
        self, page: Page | None, lines: list[dict] | None = None, tolerance: float = 3.0
    ) -> None:
        self.lines: list[dict] = []
        self.horizontal_lines: list[dict] = []
        self.vertical_lines: list[dict] = []
        self.tol: float = tolerance

        if page:
            self.init_from_page(page)
        if lines:
            self.init_from_lines(lines)

    def init_from_page(self, page: Page) -> None:
        self.extract_lines(page.lines + page.rects + page.curves + page.images)
        self.extract_rects(page.rects)

    def init_from_lines(self, lines: list[dict]) -> None:
        self.extract_lines(lines)

    def get_orientation(self, line: dict) -> str:
        width = abs(line["x1"] - line["x0"])
        height = abs(line["bottom"] - line["top"])

        ratio = 1.5
        max_thickness = 5.0

        if width > height * ratio and height < max_thickness:
            return "x"
        if height > width * ratio and width < max_thickness:
            return "y"

        return "none"

    def extract_lines(self, lines: list[dict]) -> None:
        """we process page.lines, page.rects, page.curves, page.images in bulk"""
        for line in lines:
            orientation = self.get_orientation(line)
            if orientation == "x":
                rep_y = (line["top"] + line["bottom"]) / 2
                self.horizontal_lines.append(
                    {
                        "x0": line["x0"],
                        "x1": line["x1"],
                        "top": rep_y,
                        "bottom": rep_y,
                        "orientation": orientation,
                    }
                )
            if orientation == "y":
                rep_x = (line["x0"] + line["x1"]) / 2
                self.vertical_lines.append(
                    {
                        "x0": rep_x,
                        "x1": rep_x,
                        "top": line["top"],
                        "bottom": line["bottom"],
                        "orientation": orientation,
                    }
                )

    def extract_rects(self, rects: list[dict]) -> None:
        """we extract page.rects which can be disassembled to 4 lines"""
        for rect in rects:
            if self.get_orientation(rect) != "none" or (
                rect["width"] < 5.0 and rect["height"] < 5.0
            ):
                continue

            # 枠線がない or 色付けのためのrectならばcontinue
            if rect["stroking_color"] is None or rect["fill"] is True:
                continue

            for y_key in ["top", "bottom"]:
                self.horizontal_lines.append(
                    {
                        "x0": rect["x0"],
                        "x1": rect["x1"],
                        "top": rect[y_key],
                        "bottom": rect[y_key],
                        "orientation": "x",
                    }
                )

            for x_key in ["x0", "x1"]:
                self.vertical_lines.append(
                    {
                        "x0": rect[x_key],
                        "x1": rect[x_key],
                        "top": rect["top"],
                        "bottom": rect["bottom"],
                        "orientation": "y",
                    }
                )

    def can_merge(
        self, line1_: dict, line2_: dict, main_coord, sub_start, sub_end
    ) -> bool:
        """whether two lines can be merged"""
        if line1_[sub_start] < line2_[sub_start]:
            line1, line2 = line1_, line2_
        else:
            line1, line2 = line2_, line1_

        is_collinear = abs(line1[main_coord] - line2[main_coord]) <= self.tol
        is_connected = line2[sub_start] <= line1[sub_end] + self.tol

        return is_collinear and is_connected

    def merge_lines(self, lines: list[dict], orientation: str) -> list[dict]:
        """merge collinear line segments"""
        if not lines:
            return []

        # 1. lineを座標でsort
        if orientation == "y":
            # 1. y座標方向のlineをmergeしたい。x座標が等しいものを寄せる、y座標でsrot
            lines.sort(key=itemgetter("x0", "top"))
            main_coord = "x0"
            sub_start = "top"
            sub_end = "bottom"
        else:
            # 2. x座標方向のlineをmergeしたい。y座標が等しいものを寄せる、x座標でsrot
            lines.sort(key=itemgetter("top", "x0"))
            main_coord = "top"
            sub_start = "x0"
            sub_end = "x1"

        merged = []
        current = lines[0]

        for next_line in lines[1:]:
            if self.can_merge(current, next_line, main_coord, sub_start, sub_end):
                current[sub_start] = min(current[sub_start], next_line[sub_start])
                current[sub_end] = max(current[sub_end], next_line[sub_end])
            else:
                merged.append(current)
                current = next_line

        merged.append(current)
        return merged

    def remove_included_lines(self, lines: list[dict], orientation: str) -> list[dict]:
        if orientation == "y":
            # 1. y座標方向のlineをmergeしたい。x座標が等しいものを寄せる
            main_coord = "x0"
            sub_start = "top"
            sub_end = "bottom"
        else:
            # 2. x座標方向のlineをmergeしたい。y座標が等しいものを寄せる
            main_coord = "top"
            sub_start = "x0"
            sub_end = "x1"

        skip = set()
        for i, long in enumerate(lines):
            for j, short in enumerate(lines):
                if i in skip or j in skip or i == j:
                    continue

                is_collinear = abs(long[main_coord] - short[main_coord]) <= self.tol
                include_start = long[sub_start] - self.tol <= short[sub_start]
                include_end = short[sub_end] <= long[sub_end] + self.tol

                if is_collinear and include_start and include_end:
                    skip.add(j)

        extracted = [line for i, line in enumerate(lines) if i not in skip]
        return extracted

    def extract_by_length(self, min_line_length=3.0) -> list[dict]:
        """exclude the lines whose length is shorter than min_line_lenght"""
        extract_lines: list[dict] = []
        for line in self.lines:
            orientation = line["orientation"]
            length = (
                line["x1"] - line["x0"]
                if orientation == "x"
                else line["bottom"] - line["top"]
            )
            if length >= min_line_length:
                extract_lines.append(line)

        return extract_lines

    def extract(self) -> list[dict]:
        """extract the lines contained in the page"""
        merged_horizontal = self.merge_lines(self.horizontal_lines, "x")
        merged_vertical = self.merge_lines(self.vertical_lines, "y")

        self.lines = merged_horizontal + merged_vertical
        self.lines = self.extract_by_length()

        return self.lines
