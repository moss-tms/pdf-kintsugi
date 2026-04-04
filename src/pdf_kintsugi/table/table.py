from pdf_kintsugi.table.cell_unmerger import CellUnmerger
from pdf_kintsugi.table.docling_integrator import DoclingIntegrator
from pdf_kintsugi.text.extract_target_chars import extract_target_chars
from pdf_kintsugi.utils.coord import is_same


class Table:
    def __init__(self, bbox, lines, page_number, tolerance) -> None:
        self.bbox: tuple[float, float, float, float] = bbox
        self.lines: list[dict] = lines
        self.page_number: int = page_number
        self.tol: float = tolerance
        self.lattice: dict[str, list[dict]] = {
            "x": [line for line in self.lines if line["orientation"] == "x"],
            "y": [line for line in self.lines if line["orientation"] == "y"],
        }

    def _extract_line_coords(self, orientation: str) -> list[float]:
        """そのtableにおいて、orientation方向のlineが存在する座標を全て列挙"""
        coords: list[float] = []
        lines: list[dict] = self.lattice[orientation]
        main_coords = "top" if orientation == "x" else "x0"

        for line in lines:
            is_only = True
            for coord in coords:
                if is_same(coord, line[main_coords], self.tol):
                    is_only = False
                    break
            if is_only:
                coords.append(line[main_coords])

        return coords

    def _extract_axis_coords(self, orientation: str) -> list[float]:
        """edgeも含め、そのtableにおいて、orientation方向のlineが存在する座標を全て列挙"""
        x0, top, x1, bottom = self.bbox
        min_coord = x0 if orientation == "x" else top
        max_coord = x1 if orientation == "x" else bottom

        line_orientation = "y" if orientation == "x" else "x"
        coords = self._extract_line_coords(line_orientation)

        if not is_same(min_coord, coords[0], self.tol):
            coords = [min_coord] + coords
        if not is_same(max_coord, coords[-1], self.tol):
            coords.append(max_coord)

        return coords

    def _extract_xy_coords(self) -> None:
        """get x,y coords"""
        self.y_coords = self._extract_axis_coords("y")
        self.x_coords = self._extract_axis_coords("x")

    def _add_grid_point_index(self) -> bool:
        """indexing coords of line"""
        for line in self.lines:
            x0, top, x1, bottom = line["x0"], line["top"], line["x1"], line["bottom"]

            same_x0 = [is_same(x, x0, self.tol) for x in self.x_coords]
            same_x1 = [is_same(x, x1, self.tol) for x in self.x_coords]
            same_top = [is_same(y, top, self.tol) for y in self.y_coords]
            same_bottom = [is_same(y, bottom, self.tol) for y in self.y_coords]

            if not (
                any(same_x0) and any(same_x1) and any(same_top) and any(same_bottom)
            ):
                return False

            x0_idx, x1_idx = same_x0.index(True), same_x1.index(True)
            top_idx, bottom_idx = same_top.index(True), same_bottom.index(True)

            line["index"] = (x0_idx, top_idx, x1_idx, bottom_idx)

        return True

    def _get_basic_structure(self) -> None:
        self.row_num = len(self.y_coords) - 1
        self.column_num = len(self.x_coords) - 1
        self.cell_num = self.row_num * self.column_num

    def _extract_main_horizons(self) -> None:
        self.main_horizons: list[int] = []

        for line in self.lattice["x"]:
            y_idx = line["index"][1]

            if any(
                is_same(self.y_coords[y_idx], self.y_coords[existing], self.tol)
                for existing in self.main_horizons
            ):
                continue

            # このy座標を通過する縦線のx座標を収集
            spanning_verticals = [
                v for v in self.lattice["y"] if v["index"][1] <= y_idx <= v["index"][3]
            ]

            if not spanning_verticals:
                continue

            local_x0 = min(v["x0"] for v in spanning_verticals)
            local_x1 = max(v["x1"] for v in spanning_verticals)

            if is_same(line["x0"], local_x0, self.tol) and is_same(
                line["x1"], local_x1, self.tol
            ):
                self.main_horizons.append(y_idx)

    def _define_column_header_boundary(self) -> None:
        top = self.bbox[1]
        is_top_line: list[bool] = [
            is_same(line["top"], top, self.tol) for line in self.lattice["x"]
        ]

        exist_top = is_top_line[0] is True
        self.col_header_boundary: int = 0

        if not exist_top or len(self.main_horizons) < 2:
            self.exist_header: bool = False
            return

        idx = 1 if self.main_horizons[0] == 0 else 0
        self.exist_header = not (idx == 1 and len(self.main_horizons) < 3)
        self.col_header_boundary = self.main_horizons[idx] if self.exist_header else 0

    def _compress_column_header(self) -> list[str]:
        """compress column header into 1 column"""
        if not self.exist_header:
            col_header: list[str] = [f"column_{i + 1}" for i in range(self.column_num)]
            return col_header

        merged_list: list[list[str]] = [[] for _ in range(self.column_num)]
        for j in range(self.column_num):
            for i in range(self.col_header_boundary):
                exist = len(merged_list[j]) > 0
                if exist and merged_list[j][-1] == self.data[i][j]:
                    continue

                merged_list[j].append(self.data[i][j])

        col_header = ["_".join(texts) for texts in merged_list]
        return col_header

    def process_column_header(self) -> None:
        header = self._compress_column_header()
        contens: list[list[str]] = self.data[self.col_header_boundary :]
        contens.insert(0, header)
        self.data = contens
        self.compressed_row_nums: int = self.row_num - len(self.data)
        self.row_num = len(self.data)

    def _extract_main_verticals(self) -> None:
        # 直線x = x_coords[i]と垂直に交わるhorizonsの、y_indexを得る
        intersecting_horizon_ys: list[list[int]] = [
            [
                line["index"][3]
                for line in self.lattice["x"]
                if line["index"][0] <= x_idx <= line["index"][2]
            ]
            for x_idx in range(len(self.x_coords))
        ]

        # 各x_coord[i]における、最も低いhorizonのbottom index
        x_bottoms: list[int] = [max(y_indices) for y_indices in intersecting_horizon_ys]

        verticals_at_x: list[list[dict]] = [
            [line for line in self.lattice["y"] if line["index"][0] == x_idx]
            for x_idx in range(len(self.x_coords))
        ]

        self.main_verticals: list[int] = [
            i
            for i, lines in enumerate(verticals_at_x)
            if len(lines) == 1
            and x_bottoms[i] <= lines[0]["index"][3]
            and (
                self.col_header_boundary > lines[0]["index"][1]
                or lines[0]["index"][0] == 0
            )
        ]

    def _define_row_header_boundary(self) -> None:
        x0 = self.bbox[0]
        is_x0_line: list[bool] = [
            is_same(line["x0"], x0, self.tol) for line in self.lattice["y"]
        ]

        exist_x0 = is_x0_line[0] is True
        self.row_header_boundary: int = 0

        if exist_x0 and len(self.main_verticals) > 2:
            self.row_header_boundary = self.main_verticals[1]
        if not exist_x0 and len(self.main_verticals) > 1:
            self.row_header_boundary = self.main_verticals[0]

    def _compress_row_header(self) -> list[str]:
        merged_list: list[list[str]] = [[] for _ in range(self.row_num)]
        for i in range(self.row_num):
            for j in range(self.row_header_boundary):
                exist = len(merged_list[i]) > 0
                if exist and merged_list[i][-1] == self.data[i][j]:
                    continue

                merged_list[i].append(self.data[i][j])

        header: list[str] = [" > ".join(texts) for texts in merged_list]
        return header

    def process_row_header(self) -> None:
        if not self.exist_header or self.row_header_boundary == 0:
            return

        header = self._compress_row_header()
        remain: list[list[str]] = [
            [header[i]] + row[self.row_header_boundary :]
            for i, row in enumerate(self.data)
        ]

        self.data = remain
        self.column_num = len(self.data[0])

    def _is_complex_table(self) -> None:
        """It may be better to ignore the incomplete verticals in the first row"""
        self.is_complex: bool = len(self.main_verticals) != len(self.lattice["y"])

    def calc_centroid(self) -> tuple[float, float]:
        centroid_x = (self.bbox[0] + self.bbox[2]) / 2
        centroid_y = (self.bbox[1] + self.bbox[3]) / 2
        return (centroid_x, centroid_y)

    def _build_complex_table(self, chars: list[dict]) -> None:
        cell_ummerger = CellUnmerger(self, chars)
        self.data: list[list[str]] = cell_ummerger.build()

        self._extract_main_horizons()
        self._define_column_header_boundary()
        self.process_column_header()

        self._extract_main_verticals()
        self._define_row_header_boundary()
        self.process_row_header()

        self._is_complex_table()

    def _define_header_confidence(self):
        """confidence of existence of header"""
        self.header_confidence: bool = False

        if self.is_complex or not self.exist_header:
            return

        empty_top_left = self.data[0][0] == ""
        is_compressed = self.col_header_boundary > 1

        self.header_confidence = empty_top_left or is_compressed

    def _extract_chars(self, chars: list[dict]) -> list[dict]:
        extracted_chras = extract_target_chars(chars, self.bbox)
        return extracted_chras

    def build(self, chars: list[dict], docling: dict) -> bool:
        extracted_chars = self._extract_chars(chars)

        self._extract_xy_coords()
        sucess = self._add_grid_point_index()

        if not sucess:
            return False

        self._get_basic_structure()
        self._build_complex_table(extracted_chars)
        self._define_header_confidence()

        if self.is_complex or not self.exist_header:
            return True

        integrator = DoclingIntegrator(self, docling, extracted_chars)
        self.data = integrator.integrate()

        self.row_num = len(self.data)
        self.column_num = len(self.data[0])

        return True
