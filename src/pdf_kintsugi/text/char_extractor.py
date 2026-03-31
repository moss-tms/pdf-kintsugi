import re


class CharExtractor:
    def __init__(self, page) -> None:
        self.chars = page.chars
        self.chars = self._remove_overlapping_chars()
        self.chars = self._remove_only_space()
        self._add_represent_coords()

    def _remove_overlapping_chars(self, tolerance=1.5) -> list[dict]:
        """merge characters with nearly identical coordinates"""
        cleaned = []
        skip = set()
        self.chars.sort(key=lambda ch: (ch["top"], ch["x0"]))

        for i, ch1 in enumerate(self.chars):
            if i in skip:
                continue

            x1, y1 = ch1["x0"], ch1["top"]

            for j in range(i + 1, len(self.chars)):
                ch2 = self.chars[j]
                x2, y2 = ch2["x0"], ch2["top"]
                if (
                    abs(x1 - x2) < tolerance
                    and abs(y1 - y2) < tolerance
                    and ch1["text"] == ch2["text"]
                ):
                    skip.add(j)
                else:
                    break

            cleaned.append(ch1)

        return cleaned

    def _remove_only_space(self) -> list[dict]:
        """exclude empty texts"""
        return [ch for ch in self.chars if not re.fullmatch(r"\s*", ch["text"])]

    def _add_represent_coords(self) -> None:
        for ch in self.chars:
            ch["x"] = (ch["x0"] + ch["x1"]) / 2
            ch["y"] = (ch["top"] + ch["bottom"]) / 2

    def extract(self) -> list[dict]:
        return self.chars
