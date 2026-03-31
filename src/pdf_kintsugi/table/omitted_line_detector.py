from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdf_kintsugi.table.table import Table
from pdf_kintsugi.text.row_builder import RowBuilder


class OmittedLineDetector:
    def __init__(self, table: Table, chars: list[dict]) -> None:
        self.table: Table = table
        self.chars: list[dict] = chars
        self.col_num = table.column_num
        self.x_coords: list[float] = table.x_coords

    def detect(self, top_idx: int, bottom_idx: int) -> bool:
        top_coord: float = self.table.y_coords[top_idx]
        bottom_coord: float = self.table.y_coords[bottom_idx]
        cells: list[list[list[dict]]] = self._build_cells(top_coord, bottom_coord)
        col_anchors: list[bool] = self._get_anchor_columns(cells)

        for cid in range(self.col_num):
            if not col_anchors[cid]:
                continue

            if self._is_line_omitted_in_column(cid, cells):
                return True

        return False

    def _is_line_omitted_in_column(
        self, cid: int, cells: list[list[list[dict]]]
    ) -> bool:
        column_lines_y: list[float] = [
            line["top"]
            for line in self.table.lattice["x"]
            if line["index"][0] <= cid < line["index"][2]
        ]

        cells_y: list[float] = [self._get_cell_y(row[cid]) for row in cells if row[cid]]

        for y1, y2 in zip(cells_y[:-1], cells_y[1:]):
            has_separating_line = any(y1 < line_y <= y2 for line_y in column_lines_y)
            if not has_separating_line:
                return True

        return False

    def _get_cell_y(self, cell: list[dict]) -> float:
        rep_y = sum(ch["y"] for ch in cell) / len(cell)
        return rep_y

    def _build_cells(self, top: float, bottom: float) -> list[list[list[dict]]]:
        rows: list[list[dict]] = self._build_rows(top, bottom)
        cells: list[list[list[dict]]] = [
            [
                [ch for ch in row if self.x_coords[i] <= ch["x"] < self.x_coords[i + 1]]
                for i in range(self.col_num)
            ]
            for row in rows
        ]

        return cells

    def _build_rows(self, top: float, bottom: float) -> list[list[dict]]:
        bbox = (self.table.bbox[0], top, self.table.bbox[2], bottom)
        chars = self._extract_chars_within_bbox(bbox)

        row_builder = RowBuilder(chars, "single")
        rows: list[list[dict]] = row_builder.build()
        return rows

    def _extract_chars_within_bbox(self, bbox: tuple) -> list[dict]:
        x0, top, x1, bottom = bbox

        extracted_chars = [
            ch for ch in self.chars if x0 <= ch["x"] <= x1 and top <= ch["y"] <= bottom
        ]

        return extracted_chars

    def _get_anchor_columns(self, cells: list[list[list[dict]]]) -> list[bool]:
        columns: list[list[list[dict]]] = [
            [cells[i][j] for i in range(len(cells))] for j in range(self.col_num)
        ]

        col_anchors: list[bool] = [self._is_anchor_column(column) for column in columns]
        return col_anchors

    def _is_anchor_column(self, column: list[list[dict]]) -> bool:
        """
        For an anchor column, at least 70% of the text in the column must be anchor
        """
        cells = [cell for cell in column if cell]
        if not cells:
            return False

        anchor_count = sum(1 for cell in cells if self._is_anchor_text(cell))
        return anchor_count / len(cells) >= 0.7

    def _is_anchor_text(self, chars: list[dict], max_unit_length: int = 4) -> bool:
        if not chars:
            return False

        text = "".join(ch["text"] for ch in chars).strip()
        if not text:
            return False

        letter_count = sum(1 for c in text if unicodedata.category(c).startswith("L"))
        has_digit = any(unicodedata.category(c).startswith("N") for c in text)

        if letter_count > max_unit_length:
            return False

        return has_digit or letter_count == 0
