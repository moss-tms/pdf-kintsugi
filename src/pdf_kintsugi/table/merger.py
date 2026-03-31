from pdf_kintsugi.table.table import Table
from pdf_kintsugi.utils.coord import is_same


class TableMerger:
    def __init__(self) -> None:
        pass

    def merge(self, table1: Table, table2: Table) -> bool:
        self.table1: Table = table1
        self.table2: Table = table2

        self._preprocess()
        if not self.can_merge:
            return False

        self._adjust_lines()
        return True

    def _preprocess(self) -> None:
        self._can_merge_by_range()
        self._get_merge_direction()
        self._can_merge_by_lines()
        self._swap_tables()
        self._can_merge_by_header()

    def _adjust_lines(self) -> None:
        idx = 0 if self.merge_dire == "x" else 1
        orthogonal_key = "y" if self.merge_dire == "x" else "x"

        plines1, plines2 = self._get_target_lines(self.merge_dire)
        olines1, olines2 = self._get_target_lines(orthogonal_key)

        # replaces[0] overwrite replaces[1]
        replaces = [self.table1.bbox[idx + 2], self.table2.bbox[idx]]
        if len(plines1) < len(plines2):
            replaces[0], replaces[1] = replaces[1], replaces[0]
            plines1, plines2 = plines2, plines1
            olines1, olines2 = olines2, olines1

        keys = ["x0", "x1"] if self.merge_dire == "x" else ["top", "bottom"]

        # extend the lines parallel to the direction of the joint
        for line in plines2:
            for key in keys:
                if is_same(line[key], replaces[1]):
                    line[key] = replaces[0]

        # move the lines orhogonal to the direction of the joint
        for line in olines2:
            for key in keys:
                if is_same(line[key], replaces[1]):
                    line[key] = replaces[0]

    def _is_range_duplicate(self, orientation: str) -> bool:
        idx = 0 if orientation == "x" else 1

        r1: tuple = (self.table1.bbox[idx], self.table1.bbox[idx + 2])
        r2: tuple = (self.table2.bbox[idx], self.table2.bbox[idx + 2])
        r1, r2 = min(r1, r2), max(r1, r2)

        return r2[0] < r1[1]

    def _can_merge_by_range(self) -> None:
        same_x = self._is_range_duplicate("x")
        same_y = self._is_range_duplicate("y")

        self.can_merge = same_x ^ same_y

    def _get_merge_direction(self) -> None:
        if not self.can_merge:
            return

        same_x = self._is_range_duplicate("x")
        self.merge_dire = "y" if same_x else "x"

    def _get_target_coords(self) -> tuple[list[float], list[float]]:
        if self.merge_dire == "y":
            lines1: list[float] = self.table1.x_coords
            lines2: list[float] = self.table2.x_coords
        else:
            lines1 = self.table1.y_coords
            lines2 = self.table2.y_coords

        return (lines1, lines2)

    def _get_target_lines(self, dire: str) -> tuple[list[dict], list[dict]]:
        lines1: list[dict] = self.table1.lattice[dire]
        lines2: list[dict] = self.table2.lattice[dire]
        return (lines1, lines2)

    def _can_merge_by_lines(self) -> None:
        if not self.can_merge:
            return

        lines1, lines2 = self._get_target_coords()

        if len(lines1) > len(lines2):
            lines1, lines2 = lines2, lines1

        is_exist = [any(is_same(c1, c2) for c2 in lines2) for c1 in lines1]
        all_exist = all(is_exist)

        self.can_merge &= all_exist

    def _swap_tables(self) -> None:
        if not self.can_merge:
            return

        idx = 0 if self.merge_dire == "x" else 1

        if self.table1.bbox[idx] > self.table2.bbox[idx]:
            self.table1, self.table2 = self.table2, self.table1

    def _can_merge_by_header(self) -> None:
        if not self.can_merge or self.merge_dire == "x":
            return

        if self.table2.header_confidence:
            self.can_merge = False
