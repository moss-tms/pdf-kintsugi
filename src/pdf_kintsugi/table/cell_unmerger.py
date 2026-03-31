from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdf_kintsugi.table.table import Table
from pdf_kintsugi.table.char_assigner import CharAssigner
from pdf_kintsugi.text.row_builder import RowBuilder
from pdf_kintsugi.utils.union_find import UnionFind


class CellUnmerger:
    def __init__(self, table: Table, chars: list[dict]) -> None:
        self.table = table
        self.chars = chars

        self.column_num = table.column_num
        self.row_num = table.row_num
        self.cell_num = table.cell_num

    def extract_piller_lines(self, orientation: str, bbox: tuple) -> list[dict]:
        """bbox isn't coordinates, but indices. orientation : line["orientation"]"""
        main = 0 if orientation == "x" else 1
        sub = 1 if orientation == "x" else 0

        extracted: list[dict] = [
            line
            for line in self.table.lattice[orientation]
            if (
                bbox[sub] <= line["index"][sub] <= bbox[sub + 2]
                and line["index"][main] <= bbox[main]
                and bbox[main + 2] <= line["index"][main + 2]
            )
        ]

        return extracted

    def extract_non_piller_lines(self, orientation: str, bbox: tuple):
        """bbox isn't coordinates, but indices. orientation : line["orientation"]"""
        main = 0 if orientation == "x" else 1
        sub = 1 if orientation == "x" else 0

        extracted: list[dict] = [
            line
            for line in self.table.lattice[orientation]
            if (
                bbox[sub] <= line["index"][sub] <= bbox[sub + 2]
                and bbox[main] <= line["index"][main]
                and line["index"][main + 2] <= bbox[main + 2]
            )
        ]

        return extracted

    def build_table_structure(self) -> None:
        """process merged cells"""
        # 1. tableの各rowをsplitするvertical lineの、x座標のindexを管理
        row_split = [set() for _ in range(self.row_num)]
        for y_line in self.table.lattice["y"]:
            x0, top, x1, bottom = y_line["index"]
            for y in range(top, bottom):
                row_split[y].add(x0)

        # 2. tableの各columnをsplitするyのindexを管理
        column_split = [set() for _ in range(self.column_num)]
        for x_line in self.table.lattice["x"]:
            x0, top, x1, bottom = x_line["index"]
            for x in range(x0, x1):
                column_split[x].add(top)

        # 3. セル(y,x)を見て、(y+1, x), (y, x+1)が連結しているかを判定してmerge
        self.uf = UnionFind(self.cell_num)
        for y in range(self.row_num):
            for x in range(self.column_num):
                now_id = y * self.column_num + x
                if x + 1 not in row_split[y] and x + 1 < self.column_num:
                    nex_id = y * self.column_num + (x + 1)
                    self.uf.merge(now_id, nex_id)
                if y + 1 not in column_split[x] and y + 1 < self.row_num:
                    nex_id = (y + 1) * self.column_num + x
                    self.uf.merge(now_id, nex_id)

    def row_clustering(self, chars: list[dict]) -> list[list[dict]]:
        """convert chars into rows"""
        row_builder = RowBuilder(chars)
        return row_builder.build()

    def get_divided_chars(self) -> list[list[dict]]:
        """return chars contained in each merged cells"""
        groups: list[list[int]] = self.uf.groups()
        divided_chars: list[list[dict]] = [[] for _ in range(len(groups))]

        # Atomic cell ごとに Char をアサイン (O(N log M))
        assigner = CharAssigner(self.chars, self.table.x_coords, self.table.y_coords)
        atomic_assigned: dict[int, list[dict]] = assigner.assign()

        # 各 Atomic cell ID がどのグループに属しているかを事前マッピング
        atomic_to_group = {}
        for group_idx, group in enumerate(groups):
            for cell_id in group:
                atomic_to_group[cell_id] = group_idx

        # アサイン結果から統合グループへ文字を振り分け
        for cell_id, chars_in_cell in atomic_assigned.items():
            if not chars_in_cell:
                continue
            group_idx = atomic_to_group.get(cell_id)
            if group_idx is not None:
                divided_chars[group_idx].extend(chars_in_cell)

        return divided_chars

    def _convert_into_str(self, merged_cell_texts: list[list[list[dict]]]) -> list[str]:
        texts: list[str] = [
            # "\n".join(["".join([ch["text"] for ch in row]) for row in cell])
            " ".join(["".join([ch["text"] for ch in row]) for row in cell])
            for cell in merged_cell_texts
        ]

        return texts

    def build(self) -> list[list[str]]:
        # 1. セル結合情報の取得
        self.build_table_structure()
        groups: list[list[int]] = self.uf.groups()

        # 2. 各merged cellに含まれるcharを二次元リストで管理
        divided_chars: list[list[dict]] = self.get_divided_chars()

        # 3. 各セルに含まれるtextに対し、row_clusteringを実行
        texts_in_merged_cell = [self.row_clustering(chars) for chars in divided_chars]
        texts_in_merged_cell = self._convert_into_str(texts_in_merged_cell)

        # 4. セル結合している他のセルにtextを共有
        texts_in_cell: list[list[str]] = [
            ["" for __ in range(self.column_num)] for _ in range(self.row_num)
        ]
        for i, cells in enumerate(groups):
            for cell in cells:
                y: int = cell // self.column_num
                x: int = cell % self.column_num
                texts_in_cell[y][x] = texts_in_merged_cell[i]

        return texts_in_cell
