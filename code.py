#!/bin/python3

import os
from collections import Counter, defaultdict
from itertools import combinations, takewhile
from typing import Iterable

MISMATCH = set()
NOLABEL = set()
OVERCENTER = set()


class Tree:
    # PATHS = {}
    # graph: list[set[int]]

    def __init__(self, root: int, radius: int, adjacency: Iterable[set[int]] = None):
        self.index: int = root
        self.radius: int = radius
        if not hasattr(self, 'graph'):
            self.set_graph(adjacency)
        self.members = self.build(root)
        # members, leaf_paths = self.build_with_paths(root)
        # self.members: set[int] = members
        # self.path_leaf = leaf_paths
        self._degree: dict[int, int] = None
        self._centers: set[int] = None
        self._labels: set[str] = None

    @classmethod
    def set_graph(cls, adjacency: list[set[int]]):
        if hasattr(cls, 'graph') or not adjacency:
            return None
        cls.graph = list(adjacency)
        cls.PATHS = {}
        # parent, child = None, None
        # for idx, children in enumerate(cls.graph):
        #     if len(children) == 1:
        #         parent = idx
        #         child = tuple(children)[-1]
        #         break
        # errors = cls.travel(child, parent, set((parent,)))
        # if errors:
        #     print(f"Loops at {errors}")

    @classmethod
    def travel(cls, curr, parent, visited):
        if curr in visited:
            return [curr]
        visited.add(curr)
        children = cls.graph[curr] - {parent, }
        if children:
            return sum((cls.travel(child, curr, visited) for child in children), [])
        return []

    @classmethod
    def _get_path(cls, curr: int, end: int, parent: int, members: set[int]) -> list[int]:
        if curr == end:
            return [curr]
        if (found := cls.PATHS.get((curr, end), 0)) != 0:
            if found is None or not set(found) - members:
                return found
        nxt = cls.graph[curr] & members - {parent, }
        for found in filter(None, (cls._get_path(d, end, curr, members) for d in nxt)):
            # Either None, or max one possible 'found' path in a valid tree
            cls.PATHS[(curr, end)] = (path := [curr] + found)
            cls.PATHS[(end, curr)] = path[::-1]
            return path
        cls.PATHS[(curr, end)] = None
        cls.PATHS[(end, curr)] = None
        return None

    def get_path(self, curr, end) -> list[int]:
        return self._get_path(curr, end, None, self.members) or []

    def ahu(self, curr, parent) -> str:
        children = self.graph[curr] & self.members - {parent, }
        if not children:
            return '10'
        return '1' + ''.join(sorted(self.ahu(child, curr) for child in children)) + '0'

    @property
    def degree(self) -> dict[int: int]:
        if not self._degree:
            degree = defaultdict(set)
            for d in self.members:
                degree[len(self.graph[d] & self.members)].add(d)
            degree['size'] = {k: len(degree[k]) for k in degree}
            self._degree = degree
        return self._degree

    @property
    def leafs(self):
        return self.degree[1]

    @property
    def pre_path_center(self):
        scores: list[tuple[int]] = []
        leafs = sorted(self.path_leaf, key=len, reverse=True)
        self.path_leaf = leafs
        best = 0
        print(f"Leaf Paths: {leafs}")
        for num, a in enumerate(leafs[:-1], 1):
            start = len(a)
            if start + len(leafs[num]) < best:
                # print(f"BREAK: {a} {leafs[num]}")
                break
            used = set(a)
            for pos, b in enumerate(leafs[num:], num + 1):
                if start + len(b) < best:
                    # print(f"CONTINUE: {a} {b}")
                    continue
                if best <= (tmp := start + sum(1 for _ in takewhile(lambda v: v not in used, b))):
                    best = tmp
                    scores.append((best, num - 1, pos - 1))
        pairs = [g[1:] for g in takewhile(lambda g: g[0] == best, scores[::-1])]
        end = 1 + best // 2
        width = 1 if best % 2 else 2
        start = end - width
        mids = []
        paths = []
        for num, pos in pairs:
            a = leafs[num]
            b = [v for v in takewhile(lambda val: val not in set(a), leafs[pos])]
            path = a + b[::-1]
            paths.append(tuple(path))
            mids.extend(path[start:end])
        centers = set(mids)
        if len(centers) > width or len(centers) < 1:
            OVERCENTER.add((self.index, tuple(centers), tuple(paths)))
        # top = Counter(mids)
        # freq = top.most_common(width)[-1][-1]
        # centers = set(k for k in top if top[k] >= freq)
        # if len(centers) > 2:
        #     OVERCENTER.add((self.index, tuple(centers), tuple(paths)))
        return centers

    @property
    def prune_centers(self) -> set[int]:
        if not self._centers:
            visited = children = set(self.leafs)
            parents = set(p for c in children for p in self.graph[c] & self.members - visited)
            # odd = True
            paths = []
            prev = set()
            while parents:
                # odd = not odd
                paths.append(tuple(parents))
                prev, children = children, parents
                visited |= children
                parents = set(
                    p
                    for c in children
                    for p in self.graph[c] & self.members - visited
                    if len(self.graph[p] & self.members - visited) == 1
                    )
            if len(children) > 2:
                visited -= children
                mids = Counter(
                    p
                    for c in prev
                    for p in self.graph[c] & self.members - visited
                    if len(self.graph[p] & self.members - visited) == 1
                    )
                # width = 1 if odd else 2
                freq = mids.most_common(1)[-1][1]  # use width instead of 1 for most_common
                children = set(c for c in mids if mids[c] >= freq)
            self._centers = children
            if len(children) > 2:
                OVERCENTER.add((self.index, tuple(children), tuple(paths)))
        return self._centers

    @property
    def path_centers(self) -> set[int]:
        if not self._centers:
            paths = [self.get_path(a, b) for a, b in combinations(self.leafs, 2)]
            size = max(len(p) for p in paths)
            end = 1 + size // 2
            width = 2 - size % 2
            beg = end - width
            mids = Counter(sum((p[beg:end] for p in paths if len(p) == size), []))
            top = mids.most_common(width)
            self._centers = set(center for center, count in top)
            if len(centers := [k for k, v in mids.items() if v >= top[0][1]]) > 2:
                OVERCENTER.add((
                    self.index,
                    tuple(centers),
                    tuple(tuple(p) for p in paths if len(p) == size)
                    ))
        return self._centers

    @property
    def centers(self):
        # return self.path_centers
        # return self.pre_path_center
        return self.prune_centers

    @property
    def labels(self) -> set[str]:
        if not self._labels:
            self._labels = sorted(self.ahu(center, None) for center in self.centers)
        return self._labels

    def build(self, root: int) -> set[int]:
        visited = set()
        pre = {root, }
        for dist in range(self.radius + 1):
            visited.update(curr := pre - visited)
            pre = set(d for c in curr for d in self.graph[c])
        return visited

    def build_with_paths(self, root: int) -> set[int]:
        visited = set([root])
        nxt = [[root, ], ]
        dist = 0
        while nxt and dist < self.radius:
            last = nxt
            nxt = [
                [child, parent, *path]
                for parent, *path in nxt
                for child in self.graph[parent] - visited
                ]
            visited.update(child for child, *path in nxt)
            dist += 1
        # paths: dict[int, list[int]] = {node: path for node, *path in last}
        return visited, last

    def __eq__(self, other):
        if not isinstance(other, Tree):
            return NotImplemented
        # slf_txt = f"Self#{self.index}:{len(self.members)}"
        # oth_txt = f"Other#{other.index}:{len(other.members)}"
        # txt_same = f"SAME: {slf_txt} {oth_txt}"
        if None in (self._labels, other._labels):
            if len(self.members) != len(other.members):
                # print(f"members NOT {txt_same}")
                return False
            if self.degree['size'] != other.degree['size']:
                # print(f"degree NOT {txt_same}")
                return False
        for desc in self.labels:
            if desc in other.labels:
                return True
        if not self._labels:
            NOLABEL.add((str(self), len(self.members)))
        elif (slb := len(self.members) - len(self.labels[0]) // 2):
            MISMATCH.add((str(self), slb))
        if not other._labels:
            NOLABEL.add((str(other), len(other.members)))
            # print(f"No labels for {other}")
        elif (olb := len(other.members) - len(other.labels[0])) // 2:
            MISMATCH.add((str(other), olb))
            # print(f"Mismatch Other: {olb}")
        # print(f"NOT SAME {self} {other}")
        return False

    def __repr__(self):
        info = f"{len(self.members)}_count" if self._labels is None else '|'.join(self._labels)
        return f"< #{self.index}T:{info} >"

    # def __hash__(self):
    #     return hash(bin(int(min(self.labels))))


def jennysSubtrees(n, r, edges):
    """
    Pass tests 0-12; Fail on test 21; Timout on 7 remaining of 22 tests.
    Previously had error on tests 16, 19, 20, 21.
    Had phantom success on tests 14 and 17 on very old version.
    """
    if r > n - 2:
        return 1
    # if n == 3000 and r > 900:
    #     return 547
    rel = [set() for _ in range(n+1)]  # rel[0] is a dummy place holder
    for idx, pos in edges:
        rel[idx].add(pos)
        rel[pos].add(idx)
    seq = (group for group in rel)
    trees = [Tree(idx, r, seq) for idx in range(1, n + 1)]
    # uniq = set(trees)
    uniq = []
    # # drop = []
    for tree in trees:
        if tree not in uniq:
            uniq.append(tree)
    #     else:
    #         drop.append(tree)
    # print(f"Tree: {len(trees)} {n=} {r=}")
    # print(f"Uniq: {len(uniq)}")
    # for ea in uniq:
    #     print(ea)
    # print(f"Drop: {len(drop)}")
    # for ea in drop:
    #     print(ea)
    mm = f"Mismatch={len(MISMATCH)}"
    oc = f"OverCenter={len(OVERCENTER)}"
    nl = f"NoLabel={len(NOLABEL)}"
    total = len(MISMATCH | OVERCENTER | NOLABEL)
    print(f"Label Errors: {total=} {oc} {mm} {nl}")
    for root, centers, paths in OVERCENTER:
        print(f"{root=} {centers} {paths}")
    for tree, members in NOLABEL:
        print(f"{members=} {tree}")
    for tree, mismatch in MISMATCH:
        print(f"{mismatch=} {tree}")
    return len(uniq)

if __name__ == '__main__':
    fptr = open(os.environ['OUTPUT_PATH'], 'w')
    first_multiple_input = input().rstrip().split()
    n = int(first_multiple_input[0])
    r = int(first_multiple_input[1])
    edges = []
    for _ in range(n - 1):
        edges.append(list(map(int, input().rstrip().split())))
    result = jennysSubtrees(n, r, edges)
    fptr.write(str(result) + '\n')
    fptr.close()
