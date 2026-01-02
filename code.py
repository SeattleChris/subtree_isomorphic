#!/bin/python3

import os
import sys
from collections import defaultdict
from itertools import combinations
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
        self._degree: dict[int, int] = None
        self._centers: tuple[int] = None
        self._labels: tuple[str] = None

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
        # errors = cls.find_loop(child, parent, set((parent,)))
        # if errors:
        #     print(f"Loops at {errors}")
        # else:
        #     print("No loops detected")


    @classmethod
    def find_loop(cls, curr, parent, visited):
        if curr in visited:
            return [curr]
        visited.add(curr)
        children = cls.graph[curr] - {parent, }
        if children:
            return sum((cls.find_loop(child, curr, visited) for child in children), [])
        return []

    @classmethod
    def _get_path(cls, curr: int, end: int, parent: int, members: set[int]) -> list[int] | None:
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

    def get_paths(self, ends: set[int]) -> list[list[int]]:
        if self.radius == 0:
            return [[self.index], ]
        allowed = self.members - ends
        starts = {start: e for e in ends for start in self.graph[e] & allowed}
        # overwrite of earlier start: leaf pair is acceptable; All leafs excluded from allowed
        paths = (self._get_path(a, b, starts[a], allowed) for a, b in combinations(starts, 2))
        return list(filter(None, paths))

    def ahu_height(self, curr, parent) -> tuple[str, int]:
        children = self.graph[curr] & self.members - {parent, }
        if not children:
            return '10', 1
        heights = sorted(self.ahu_height(child, curr) for child in children)
        return '1' + ''.join(s for s, h in heights) + '0', max(h for s, h in heights) + 1

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

    def center_connections(self, mids: set[int], display: bool = False) -> tuple[tuple[int]]:
        if len(mids) < 2:
            return tuple()
        adj = (self._get_path(a, b, None, mids) for a, b in combinations(mids, 2))
        paths = tuple(tuple(p) for p in self.get_paths(mids) + list(filter(None, adj)))
        if len(paths) == 1 and set(paths[0]) == mids:
            return tuple()
        if display:
            print(f"Prune Paths: {paths} for centers {tuple(mids)}")
        return paths

    def get_center_labels(self) -> (tuple[int], tuple[str]):
        """Using the pruning method to find centers and labels."""
        visited = children = set(self.leafs)
        parents = set(p for c in children for p in self.graph[c] & self.members - visited)
        while parents:
            children = parents
            visited |= children
            parents = set(
                p
                for c in children
                for p in self.graph[c] & self.members - visited
                if len(self.graph[p] & self.members - visited) == 1
                )
        # self.display_center_paths(children, True)
        ah_mids = [(self.ahu_height(mid, None), mid) for mid in children]
        lo = min(ah[1] for ah, c in ah_mids)
        ahu_centers = sorted((ah[0], c) for ah, c in ah_mids if ah[1] == lo)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        _centers = tuple(c for ahu, c in ahu_centers)
        if len(_centers) > 2:
            paths = self.center_connections(set(_centers), False)
            OVERCENTER.add((self.index, _centers, paths))
        return [_centers, _labels]

    def path_centers(self) -> (tuple[int], tuple[str]):
        paths = self.get_paths(self.leafs)
        size = max(len(p) for p in paths)
        end = 1 + size // 2
        beg = end - 2 + size % 2
        mids = set(d for p in paths for d in p[beg:end] if len(p) == size)
        ah_mids = [(self.ahu_height(mid, None), mid) for mid in mids]
        lo = min(ah[1] for ah, c in ah_mids)
        ahu_centers = sorted((ah[0], c) for ah, c in ah_mids if ah[1] == lo)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        _centers = tuple(c for ahu, c in ahu_centers)
        if len(_centers) > 2:
            def _summary(p): return tuple(p[:2] + ['x'] + p[beg-1:end+1] + ['x'] + p[-2:])
            OVERCENTER.add((
                self.index,
                tuple(_centers),
                tuple(_summary(p) for p in paths if len(p) == size)
                ))
        return [_centers, _labels]

    @property
    def centers(self) -> tuple[int]:
        if not self._centers:
            self._centers, self._labels = self.get_center_labels()
        return self._centers

    @property
    def labels(self) -> tuple[str]:
        if not self._labels:
            self._centers, self._labels = self.get_center_labels()
        return self._labels

    def build(self, root: int) -> set[int]:
        visited = set()
        nxt = {root, }
        dist = -1
        while (curr := nxt - visited) and dist < self.radius:
            visited.update(curr)
            nxt = set(d for c in curr for d in self.graph[c])
            dist += 1
        return visited

    def __eq__(self, other):
        if not isinstance(other, Tree):
            return NotImplemented
        if None in (self._labels, other._labels):
            if len(self.members) != len(other.members):
                return False
            if self.degree['size'] != other.degree['size']:
                return False
        for desc in self.labels:
            if desc in other.labels:
                return True
        if not self._labels:
            NOLABEL.add((str(self), len(self.members)))
        elif (slb := len(self.members) - (len(self.labels[0]) // 2)):
            MISMATCH.add((str(self), slb))
        if not other._labels:
            NOLABEL.add((str(other), len(other.members)))
        elif (olb := len(other.members) - (len(other.labels[0]) // 2)):
            MISMATCH.add((str(other), olb))
        return False

    def __repr__(self):
        info = f"{len(self.members)}_count" if self._labels is None else self._labels[0]
        return f"<T:{info}>"

    # def __hash__(self):
    #     return hash(bin(int(self.labels[0], base=2)))


def jennysSubtrees(n, r, edges):
    """
    Pass tests 0-12, 18; Fail test 21; Timeout but correct Correct on 17. Timeout on 6 remaining of 22 tests.
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
    for tree, missing in MISMATCH:
        print(f"{missing=} {tree}")
    return len(uniq)

if __name__ == '__main__':
    # fptr = open(os.environ['OUTPUT_PATH'], 'w')
    first_multiple_input = input().rstrip().split()
    n = int(first_multiple_input[0])
    r = int(first_multiple_input[1])
    edges = []
    for _ in range(n - 1):
        edges.append(list(map(int, input().rstrip().split())))
    result = jennysSubtrees(n, r, edges)
    # fptr.write(str(result) + '\n')
    # fptr.close()
    print(result)