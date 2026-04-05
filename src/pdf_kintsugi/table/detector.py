from pdf_kintsugi.table.table import Table


class TableDetector:
    def __init__(self, lines: list[list[dict]], page_number: int, tolerance) -> None:
        self.lines: list[list[dict]] = lines
        self.page_number: int = page_number
        self.tol: float = tolerance

    def calc_table_bbox(self, lines: list[dict]) -> dict:
        x0 = min(line["x0"] for line in lines)
        x1 = max(line["x1"] for line in lines)
        top = min(line["top"] for line in lines)
        bottom = max(line["bottom"] for line in lines)

        bbox = {"x0": x0, "top": top, "x1": x1, "bottom": bottom}
        return bbox

    def is_table(self, lines: list[dict], bbox: dict) -> bool:
        """
        whether the lines are part of the table
        also, the method will be unnecessary due to docling
        """
        if len(lines) <= 4:
            return False

        x_size = bbox["x1"] - bbox["x0"]
        y_size = bbox["bottom"] - bbox["top"]

        x_lines = [line for line in lines if line["orientation"] == "x"]
        y_lines = [line for line in lines if line["orientation"] == "y"]

        # テーブルには水平線と垂直線の両方が必要
        if not x_lines or not y_lines:
            return False

        core_x, core_y = 0, 0
        for x_line in x_lines:
            length = x_line["x1"] - x_line["x0"]
            if x_size * 0.5 <= length:
                core_x += 1

        for y_line in y_lines:
            length = y_line["bottom"] - y_line["top"]
            if y_size * 0.5 <= length:
                core_y += 1

        return core_x >= 2 and core_y >= 2

    def detect(self) -> list[Table]:
        bboxes = [self.calc_table_bbox(group) for group in self.lines]

        detected = [
            i for i in range(len(self.lines)) if self.is_table(self.lines[i], bboxes[i])
        ]
        tables: list[Table] = []

        for i in detected:
            bbox = bboxes[i]
            x0, top, x1, bottom = bbox["x0"], bbox["top"], bbox["x1"], bbox["bottom"]
            tables.append(
                Table((x0, top, x1, bottom), self.lines[i], self.page_number, self.tol)
            )

        return tables
