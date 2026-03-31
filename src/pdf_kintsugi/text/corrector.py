from __future__ import annotations

from docling_core.types.doc.base import BoundingBox, CoordOrigin
from docling_core.types.doc.document import DoclingDocument, TextItem


class TextCorrector:
    def __init__(
        self,
        doc: DoclingDocument,
        page_chars: dict[int, list[dict]],
        page_heights: dict[int, float],
    ) -> None:
        """
        Args:
            doc: DoclingDocument
            page_chars: {page_no: [pdfplumber chars]} ※page_noは1-indexed
            page_heights: {page_no: page_height}
        """
        self.doc = doc
        self.page_chars = page_chars
        self.page_heights = page_heights

    def correct_all(self, doc_tables: list[list[dict]] | None = None) -> None:
        """execute all fixing functions"""
        self.correct_text_items()
        self.correct_table_items()
        if doc_tables is not None:
            self.correct_doc_table_dicts(doc_tables)

    def correct_text_items(self) -> None:
        """fix docling TextItem.text"""
        for item, _ in self.doc.iterate_items():
            if not isinstance(item, TextItem):
                continue
            if not item.prov:
                continue

            prov = item.prov[0]
            page_no = prov.page_no
            chars = self.page_chars.get(page_no, [])

            if not chars:
                continue

            pdf_bbox = self._to_pdfplumber_bbox(prov.bbox, page_no)
            corrected = self._replace_text_with_gaps(pdf_bbox, chars)
            if corrected is not None:
                item.text = corrected

    def correct_table_items(self) -> None:
        """fix table cell texts in docling document"""
        for table in self.doc.tables:
            if not table.data or not table.data.grid or not table.prov:
                continue

            page_no = table.prov[0].page_no
            chars = self.page_chars.get(page_no, [])

            if not chars:
                continue

            for row in table.data.grid:
                for cell in row:
                    if not cell.text or not cell.bbox:
                        continue
                    pdf_bbox = self._to_pdfplumber_bbox(cell.bbox, page_no)
                    corrected = self._replace_text_with_gaps(pdf_bbox, chars)
                    if corrected is not None:
                        cell.text = corrected

    def correct_doc_table_dicts(self, doc_tables: list[list[dict]]) -> None:
        """fix cell texts in doc_tables for DoclingIntegrator"""
        for page_tables in doc_tables:
            for table_data in page_tables:
                page_no: int = table_data["page_no"]
                chars = self.page_chars.get(page_no, [])

                if not chars:
                    continue

                for cell in table_data["cells"]:
                    if not cell["text"] or not cell["bbox"]:
                        continue

                    # cell["bbox"]は (l, t, r, b) — raw docling BoundingBox値
                    # TextItem.prov.bboxと同じ座標系なのでBoundingBoxを再構築して変換
                    cell_bbox = BoundingBox(
                        l=cell["bbox"][0],
                        t=cell["bbox"][1],
                        r=cell["bbox"][2],
                        b=cell["bbox"][3],
                    )
                    pdf_bbox = self._to_pdfplumber_bbox(cell_bbox, page_no)
                    chars = self.page_chars.get(page_no, [])
                    corrected = self._replace_text_with_gaps(pdf_bbox, chars)
                    if corrected is not None:
                        cell["text"] = corrected

    def _to_pdfplumber_bbox(
        self, bbox: BoundingBox, page_no: int
    ) -> tuple[float, float, float, float]:
        """
        convert docling BoundingBox into pdfplumber's coordinate system
        pdfplumber: origin=top-left
        """
        hgt = self.page_heights[page_no]

        if bbox.coord_origin == CoordOrigin.BOTTOMLEFT:
            tl_bbox = bbox.to_top_left_origin(hgt)
        else:
            tl_bbox = bbox

        return (tl_bbox.l, tl_bbox.t, tl_bbox.r, tl_bbox.b)

    def _replace_text_with_gaps(
        self,
        pdf_bbox: tuple[float, float, float, float],
        chars: list[dict],
        margin: float = 2.0,
        line_tolerance: float = 3.0,
        space_ratio: float = 0.3,
    ) -> str | None:
        """insert gaps and line break into replaced text"""
        x0, top, x1, bottom = pdf_bbox

        target_chars = [
            ch
            for ch in chars
            if (x0 - margin) <= ch["x"] <= (x1 + margin)
            and (top - margin) <= ch["y"] <= (bottom + margin)
        ]

        if not target_chars:
            return None

        target_chars.sort(key=lambda c: (c["top"], c["x0"]))

        result: list[str] = []
        prev = None

        for ch in target_chars:
            if prev is not None:
                row_change = abs(ch["top"] - prev["top"]) > line_tolerance
                if row_change:
                    # result.append("\n")
                    result.append(" ")
                else:
                    gap = ch["x0"] - prev["x1"]
                    avg_width = ((prev["x1"] - prev["x0"]) + (ch["x1"] - ch["x0"])) / 2
                    if avg_width > 0 and gap > avg_width * space_ratio:
                        result.append(" ")
            result.append(ch["text"])
            prev = ch

        return "".join(result)

    def _replace_chars(
        self,
        text: str,
        pdf_bbox: tuple[float, float, float, float],
        chars: list[dict],
        margin: float = 2.0,
    ) -> str | None:
        """replace docling chars with pdfplumber chars"""
        x0, top, x1, bottom = pdf_bbox

        # bbox内のcharsを抽出（中心座標でマッチング）
        target_chars = [
            ch
            for ch in chars
            if (x0 - margin) <= ch["x"] <= (x1 + margin)
            and (top - margin) <= ch["y"] <= (bottom + margin)
        ]

        if not target_chars:
            return None

        # reading order でソート（上→下、左→右）
        target_chars.sort(key=lambda c: (c["top"], c["x0"]))

        # 方式B: 非空白文字を順次置換
        result: list[str] = []
        char_idx = 0

        for c in text:
            if c in (" ", "\n", "\t", "\r", "\u3000"):
                # 空白文字はdoclingのレイアウト構造を保持
                result.append(c)
            else:
                if char_idx < len(target_chars):
                    result.append(target_chars[char_idx]["text"])
                    char_idx += 1
                else:
                    # pdfplumber charが足りない場合は元の文字を保持
                    result.append(c)

        return "".join(result)
