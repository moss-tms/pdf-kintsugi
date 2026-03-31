import pdfplumber
from docling.datamodel.document import ConversionResult
from docling_core.types.doc.document import RefItem, TableCell, TableData, TableItem
from pdfplumber.page import Page

from pdf_kintsugi.page_parser import PageParser
from pdf_kintsugi.table.table import Table
from pdf_kintsugi.text.char_extractor import CharExtractor
from pdf_kintsugi.text.corrector import TextCorrector


class PDFKintsugi:
    def __init__(
        self,
        source: str,
        docling_result: ConversionResult,
        tolerance: float = 3.0,
        replace_text: bool = False,
        replace_table: bool = True,
    ) -> None:
        self.source: str = source
        self.docling: ConversionResult = docling_result
        self.tol: float = tolerance
        self.replace_text: bool = replace_text
        self.replace_table: bool = replace_table
        self.num_pages: int = len(docling_result.document.pages)
        self.heights = {
            page_no: page_obj.size.height
            for page_no, page_obj in self.docling.document.pages.items()
        }

        self._extract_tables_from_docling()
        self._extract_table_refs()

    def parse(self) -> ConversionResult:
        """we will add arugments for parsing options"""
        with pdfplumber.open(self.source) as pdf:
            if self.replace_text:
                page_chars: dict[int, list[dict]] = {}
                for idx, page in enumerate(pdf.pages):
                    char_extractor = CharExtractor(page)
                    page_chars[idx + 1] = char_extractor.extract()

                corrector = TextCorrector(
                    self.docling.document, page_chars, self.heights
                )
                corrector.correct_all(self.doc_tables)

            if self.replace_table:
                for idx, page in enumerate(pdf.pages):
                    self._parse_page(page, idx)

        return self.docling

    def _parse_page(self, page: Page, page_idx: int) -> None:
        parser = PageParser(page, self.doc_tables[page_idx], self.tol)
        tables: list[list[Table]] = parser.build()

        for idx, my_tables in enumerate(tables):
            if len(my_tables) == 0:
                continue

            new_tables = [self._convert_table_type(table) for table in my_tables]
            self._update_tables(new_tables, page_idx, idx)

    def _convert_table_type(self, table: Table) -> TableData:
        new_cells: list[TableCell] = [
            TableCell(
                text=table.data[i][j],
                start_row_offset_idx=i,
                end_row_offset_idx=i + 1,
                start_col_offset_idx=j,
                end_col_offset_idx=j + 1,
            )
            for i in range(table.row_num)
            for j in range(table.column_num)
        ]

        new_table = TableData(
            num_rows=table.row_num, num_cols=table.column_num, table_cells=new_cells
        )

        return new_table

    def _update_tables(
        self, tables: list[TableData], page_idx: int, table_idx: int
    ) -> None:
        target_ref_str: str = self.table_refs[page_idx][table_idx]
        idx: int = -1

        for i, item in enumerate(self.docling.document.body.children):
            if str(item.get_ref()) == target_ref_str:
                idx = i
                break

        if idx == -1:
            return

        insert_idx: int = idx + 1

        for table in reversed(tables):
            self.docling.document.add_table(table)
            new_table_ref: RefItem = self.docling.document.body.children.pop(-1)
            self.docling.document.body.children.insert(insert_idx, new_table_ref)

        self.docling.document.body.children.pop(idx)

    def _extract_tables_from_docling(self) -> None:
        self.doc_tables: list[list[dict]] = [[] for _ in range(self.num_pages)]

        for table in self.docling.document.tables:
            if not table.prov:
                continue

            table_data: None | dict = self._get_table_data(table)
            if table_data:
                page_idx = table.prov[0].page_no - 1
                self.doc_tables[page_idx].append(table_data)

    def _extract_table_refs(self) -> None:
        self.table_refs: list[list[str]] = [[] for _ in range(self.num_pages)]
        ref_to_table = {str(t.get_ref()): t for t in self.docling.document.tables}

        for i, item in enumerate(self.docling.document.body.children):
            ref_str = str(item.get_ref())

            if ref_str in ref_to_table:
                target_table = ref_to_table[ref_str]
                page_no = target_table.prov[0].page_no - 1 if target_table.prov else 0
                self.table_refs[page_no].append(ref_str)

    def _get_table_data(self, table: TableItem) -> None | dict:
        if not (table.prov and table.data and table.data.grid):
            return None

        page_no: int = table.prov[0].page_no
        hgt: float = self.heights[page_no]

        bbox_obj = table.prov[0].bbox
        bbox = (bbox_obj.l, hgt - bbox_obj.t, bbox_obj.r, hgt - bbox_obj.b)

        table_data = {"page_no": page_no, "bbox": bbox, "cells": []}

        for row_idx, row in enumerate(table.data.grid):
            for col_idx, cell in enumerate(row):
                cell_data = self._get_cell_data(row_idx, col_idx, cell)
                table_data["cells"].append(cell_data)

        return table_data

    def _get_cell_data(self, rid: int, cid: int, cell: TableCell) -> dict:
        cell_data = {
            "text": cell.text,
            "row_idx": rid,
            "col_idx": cid,
            "bbox": None,
        }

        if cell.bbox:
            cell_data["bbox"] = (
                cell.bbox.l,
                cell.bbox.t,
                cell.bbox.r,
                cell.bbox.b,
            )

            cell_data["x"] = (cell.bbox.l + cell.bbox.r) / 2
            cell_data["y"] = (cell.bbox.t + cell.bbox.b) / 2

        return cell_data
