class UnionFind:
    def __init__(self, size: int) -> None:
        self.size = size
        self.data: list[int] = [-1 for _ in range(size)]

    def root(self, i: int) -> int:
        if self.data[i] < 0:
            return i
        self.data[i] = self.root(self.data[i])
        return self.data[i]

    def merge(self, i: int, j: int) -> None:
        i, j = self.root(i), self.root(j)
        if i == j:
            return

        if self.data[i] > self.data[j]:
            i, j = j, i

        self.data[i] += self.data[j]
        self.data[j] = i

    def groups(self) -> list[list[int]]:
        groups: dict[int, list] = {}
        for id in range(self.size):
            if self.root(id) not in groups:
                groups[self.root(id)] = []
            groups[self.root(id)].append(id)

        return [group for group in groups.values()]
