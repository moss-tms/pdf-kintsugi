from pdfplumber.page import Page

from pdf_kintsugi.line.extractor import LineExtractor
from pdf_kintsugi.line.merger import LineMerger
from pdf_kintsugi.table.detector import TableDetector
from pdf_kintsugi.table.merger import TableMerger
from pdf_kintsugi.table.table import Table
from pdf_kintsugi.text.char_extractor import CharExtractor


class PageParser:
    def __init__(self, page: Page, docling_tables: list[dict], tolerance) -> None:
        self.page: Page = page
        self.page_number: int = page.page_number
        self.doclings: list[dict] = docling_tables
        self.tol: float = tolerance

        char_extractor = CharExtractor(page)
        self.chars: list[dict] = char_extractor.extract()

        line_extractor = LineExtractor(self.page, tolerance=self.tol)
        self.lines: list[dict] = line_extractor.extract()

        self.build(counter=0)

    def build(self, counter: int = 1) -> list[list[Table]]:
        if counter == 1:
            line_extractor = LineExtractor(None, self.lines, tolerance=self.tol)
            self.lines = line_extractor.extract()

        my_tables: list[Table] = self._detect_tables()
        links: list[list[int]] = self._link_docling(my_tables)

        # doclingとtableが1対1対応しているやつを解析する, それ以外のmy tableは不要
        valid_indices = [i for i in range(len(my_tables)) if len(links[i]) == 1]
        my_tables = [my_tables[i] for i in valid_indices]
        links = [links[i] for i in valid_indices]
        build_success_tables: list[Table] = []

        # build
        for i, table in enumerate(my_tables):
            docling = self.doclings[links[i][0]]
            success = table.build(self.chars, docling)

            if success:
                build_success_tables.append(table)

        my_tables = build_success_tables
        links = self._link_docling(my_tables)

        if counter == 0:
            self._merge_tables(my_tables, links)
            return []

        rev_links: list[list[Table]] = [[] for _ in range(len(self.doclings))]
        for my_idx, doc_idx in enumerate(links):
            rev_links[doc_idx[0]].append(my_tables[my_idx])

        return rev_links

    def _merge_tables(self, my_tables: list[Table], links: list[list[int]]) -> None:
        same_cluster: dict[int, list[Table]] = {}
        for i, table in enumerate(my_tables):
            idx = links[i][0]
            if idx not in same_cluster:
                same_cluster[idx] = []
            same_cluster[idx].append(table)

        table_merger = TableMerger()
        for tables in same_cluster.values():
            sz = len(tables)
            for i in range(sz):
                for j in range(i + 1, sz):
                    table_merger.merge(tables[i], tables[j])

    def _link_docling(self, tables: list[Table]) -> list[list[int]]:
        """
        docling_table内にあるmy_tableを紐づける, my_tableがkeyでdoclingのindexがvalue
        """
        links: list[list[int]] = [
            [
                i
                for i, doc_table in enumerate(self.doclings)
                if max(doc_table["bbox"][0], table.bbox[0])
                < min(doc_table["bbox"][2], table.bbox[2])
                and max(doc_table["bbox"][1], table.bbox[1])
                < min(doc_table["bbox"][3], table.bbox[3])
            ]
            for table in tables
        ]

        return links

    def _detect_tables(self) -> list[Table]:
        line_groups = self._merge_lines()

        table_detector = TableDetector(line_groups, self.page_number, self.tol)
        tables: list[Table] = table_detector.detect()
        return tables

    def _merge_lines(self) -> list[list[dict]]:
        line_merger = LineMerger(self.lines, self.tol)
        line_groups: list[list[dict]] = line_merger.merge()
        return line_groups
