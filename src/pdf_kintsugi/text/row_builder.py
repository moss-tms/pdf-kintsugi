class RowBuilder:
    def __init__(self, chars: list[dict], strategy: str = "multi"):
        self.chars: list[dict] = chars
        self.rows: list[list[dict]] = []
        self.strategy: str = strategy

    def row_clustering(self, y_tolerance: float = 3) -> None:
        """convert chars into rows"""
        if not self.chars:
            return

        current = [self.chars[0]]
        for ch in self.chars[1:]:
            if abs(ch["top"] - current[-1]["top"]) <= y_tolerance:
                current.append(ch)
            else:
                self.rows.append(current)
                current = [ch]
        self.rows.append(current)

        for row in self.rows:
            row.sort(key=lambda ch: ch["x0"])

    def row_clustering_4single(self) -> None:
        """the latest version of row_cluster method"""
        if not self.chars:
            return

        # 最初の行を作成
        # 行の基準として「現在の行のバウンディングボックス」を保持する
        current_row: list[dict] = [self.chars[0]]
        row_top: float = self.chars[0]["top"]
        row_bottom: float = self.chars[0]["bottom"]

        for char in self.chars[1:]:
            char_top = char["top"]
            char_bottom = char["bottom"]
            char_height = char_bottom - char_top

            # --- 判定ロジックの変更点 ---

            # 現在の行と、対象文字の「共通する高さ(Intersection)」を計算
            intersection_top = max(row_top, char_top)
            intersection_bottom = min(row_bottom, char_bottom)
            overlap_height = max(0, intersection_bottom - intersection_top)

            # オーバーラップ率を計算 (文字の高さに対して、どれだけ行に食い込んでいるか)
            # 文字自身の高さの50%以上が行と重なっていれば「同じ行」とみなす
            if char_height > 0 and (overlap_height / char_height) > 0.5:
                current_row.append(char)

                # 行の範囲を少し広げる（更新する）
                # これにより、並んでいる文字の平均的な位置に行定義が補正されていく
                row_top = min(row_top, char_top)
                row_bottom = max(row_bottom, char_bottom)

            else:
                # 重なりがなければ新しい行へ
                # 行内の文字をx座標順にソートして確定
                current_row.sort(key=lambda c: c["x0"])
                self.rows.append(current_row)

                # new line is started
                current_row = [char]
                row_top = char_top
                row_bottom = char_bottom

        # add the final line
        if current_row:
            current_row.sort(key=lambda c: c["x0"])
            self.rows.append(current_row)

    def recognizeing_space(self) -> None:
        """recognizing spaces between words, and append"""
        for row in self.rows:
            for i in range(1, len(row)):
                prev, curr = row[i - 1], row[i]
                gap = abs(curr["x0"] - prev["x1"])
                threshold = float(prev["size"]) * 0.15
                if gap > threshold:
                    row[i - 1]["text"] += " "

    def build(self) -> list[list[dict]]:
        """extract rows"""
        if self.strategy == "multi":
            self.row_clustering()
        if self.strategy == "single":
            self.row_clustering_4single()

        self.recognizeing_space()
        return self.rows
