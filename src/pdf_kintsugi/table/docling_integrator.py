from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdf_kintsugi.table.table import Table
from pdf_kintsugi.table.omitted_line_detector import OmittedLineDetector


class DoclingIntegrator:
    def __init__(self, table: Table, docling: dict, chars: list[dict]) -> None:
        self.table: Table = table
        self.header: list[str] = table.data[0]
        self.num_cols = len(self.header)
        self.separater: list[float] = table.x_coords
        self.detector = OmittedLineDetector(table, chars)

        col_header: float = table.y_coords[table.col_header_boundary]
        self.cells: list[dict] = [
            cell
            for cell in docling["cells"]
            if cell["bbox"] is not None
            and col_header < cell["y"] < table.bbox[3]
            and table.bbox[0] < cell["x"] < table.bbox[2]
        ]

    def _extract_docling_rows(self, top_idx: int, bottom_idx: int) -> list[list[dict]]:
        top: float = self.table.y_coords[top_idx]
        bottom: float = self.table.y_coords[bottom_idx]

        target_cells: list[dict] = [
            cell for cell in self.cells if top < cell["y"] < bottom
        ]

        if not target_cells:
            return []

        row_indices = [cell["row_idx"] for cell in target_cells]
        min_idx = min(row_indices)
        num_rows = max(row_indices) - min_idx + 1

        rows: list[list[dict]] = [
            [cell for cell in target_cells if cell["row_idx"] - min_idx == idx]
            for idx in range(num_rows)
        ]

        return [row for row in rows if row]

    def _extract_my_rows(self, top: int, bottom: int) -> list[list[str]]:
        top -= self.table.compressed_row_nums
        bottom -= self.table.compressed_row_nums
        return self.table.data[top:bottom]

    def _separete_by_lines(self, rows: list[list[dict]]) -> list[list[list[dict]]]:
        x_centroids: list[list[float]] = [[cell["x"] for cell in row] for row in rows]

        cells: list[list[list[dict]]] = [
            [
                [
                    rows[rid][cid]
                    for cid, col in enumerate(row)
                    if self.separater[i] < col < self.separater[i + 1]
                ]
                for i in range(self.num_cols)
            ]
            for rid, row in enumerate(x_centroids)
        ]

        return cells

    def _combine_cells(self, cells: list[list[list[dict]]]) -> list[list[str]]:
        combined_cells: list[list[str]] = [
            [" ".join([cell["text"] for cell in col]) for col in row] for row in cells
        ]

        return combined_cells

    def _get_rows_between_lines(self, top: int, bottom: int) -> list[list[str]]:
        is_omitted: bool = self.detector.detect(top, bottom)

        if not is_omitted:
            return self._extract_my_rows(top, bottom)

        dict_rows = self._extract_docling_rows(top, bottom)
        cells = self._separete_by_lines(dict_rows)
        rows = self._combine_cells(cells)
        return rows

    def integrate(self) -> list[list[str]]:
        table: list[list[str]] = [self.header]
        indices: list[int] = [
            line_idx
            for line_idx in self.table.main_horizons
            if line_idx >= self.table.col_header_boundary
        ]

        for y1, y2 in zip(indices[:-1], indices[1:]):
            rows = self._get_rows_between_lines(y1, y2)
            table.extend(rows)

        return table
