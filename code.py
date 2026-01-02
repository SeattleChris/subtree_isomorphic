#!/bin/python3

import os
from collections import defaultdict
from itertools import combinations, chain
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
        self.members, self.far = self.build(root)
        self.dead: set[tuple[int, int]] = set()
        self._degree: dict[int, int] = None
        self._centers: tuple[int] = None
        self._labels: tuple[str] = None

    @classmethod
    def set_graph(cls, adjacency: list[set[int]]):
        if hasattr(cls, 'graph') or not adjacency:
            return None
        cls.graph = list(adjacency)
        cls.PATHS: dict[tuple[int, int], list[int]] = {}
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
    def _get_path(cls, curr: int, end: int, prev: int, allowed: set[int], dead: set) -> list[int]:
        if curr == end:
            return [curr]
        if (curr, end) in dead:
            return []
        if (found := cls.PATHS.get((curr, end), None)) and not set(found) - allowed:
            return found
        nxt = (cls.graph[curr] & allowed) - {prev, }
        for found in filter(None, (cls._get_path(d, end, curr, allowed, dead) for d in nxt)):
            # Either None, or max one possible 'found' path in a valid tree
            cls.PATHS[(curr, end)] = (path := [curr] + found)
            cls.PATHS[(end, curr)] = path[::-1]
            return path
        dead.add((curr, end))
        dead.add((end, curr))
        return []

    def get_paths(self, ends: set[int]) -> list[list[int]]:
        if self.radius == 0:
            return [[self.index], ]
        allowed = self.members - ends
        starts = {start: e for e in ends for start in self.graph[e] & allowed}
        # overwrite of earlier start: leaf pair is acceptable; All leafs excluded from allowed
        paths = (self._get_path(a, b, starts[a], allowed, self.dead) for a, b in combinations(starts, 2))
        return list(filter(None, paths))

    def ahu_height(self, curr, parent) -> tuple[str, int, int]:
        children = self.graph[curr] & self.members - {parent, }
        if not children:
            return '10', 1, curr
        heights = sorted(self.ahu_height(child, curr) for child in children)
        return '1' + ''.join(s for s, h, c in heights) + '0', max(h for s, h, c in heights) + 1, curr

    @property
    def degree(self) -> dict:
        if not self._degree:
            degree = defaultdict(set)
            for d in self.members:
                degree[len(self.graph[d] & self.members)].add(d)
            degree['size'] = {k: len(degree[k]) for k in degree}
            self._degree = degree
        return self._degree

    @property
    def leafs(self) -> set[int]:
        return self.degree[1]

    def center_connections(self, mids: set[int], display: bool = False) -> tuple[tuple[int]]:
        if len(mids) < 2:
            return tuple()
        adj = (self._get_path(a, b, None, mids, set()) for a, b in combinations(mids, 2))
        paths = tuple(tuple(p) for p in chain(self.get_paths(mids), adj))
        if len(paths) == 1 and set(paths[0]) == mids:
            return tuple()
        if display:
            print(f"Prune Paths: {paths} for centers {tuple(mids)}")
        return paths

    def prune_for_centers(self) -> (tuple[int], tuple[str]):
        """Using the pruning method to find centers and labels."""
        visited = curr = self.leafs
        nxt = set(p for c in curr for p in (self.graph[c] & self.members) - visited)
        while nxt:
            curr = nxt
            visited |= curr
            nxt = set(
                x
                for c in curr
                for x in (self.graph[c] & self.members) - visited
                if len(self.graph[x] & self.members - visited) == 1
                )
        # self.center_connections(curr, True)
        ah_mids = [self.ahu_height(mid, None) for mid in curr]
        lo = min(h for a, h, m in ah_mids)
        ahu_centers = sorted((a, m) for a, h, m in ah_mids if h == lo)
        _centers = tuple(c for ahu, c in ahu_centers)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        if len(_centers) > 2:
            paths = tuple(filter(None, self.center_connections(set(_centers), False)))
            OVERCENTER.add((self.index, _centers, paths))
        return [_centers, _labels]

    def all_path_centers(self) -> (tuple[int], tuple[str]):
        paths = self.get_paths(self.leafs)
        size = max(len(p) for p in paths)
        end = 1 + size // 2
        beg = end - 2 + size % 2
        mids = set(d for p in paths for d in p[beg:end] if len(p) == size)
        ah_mids = [self.ahu_height(mid, None) for mid in mids]
        lo = min(h for a, h, m in ah_mids)
        ahu_centers = sorted((a, m) for a, h, m in ah_mids if h == lo)
        _centers = tuple(c for ahu, c in ahu_centers)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        if len(_centers) > 2:
            def _summary(p): return tuple(p[:2] + ['x'] + p[beg-1:end+1] + ['x'] + p[-2:])
            OVERCENTER.add((
                self.index,
                tuple(_centers),
                tuple(_summary(p) for p in paths if len(p) == size)
                ))
        return [_centers, _labels]

    def furthest_leaf(self, start: int) -> (int, int, set[int]):
        visited = set()
        nxt = last = {start, }
        dist = -1
        while (curr := nxt - visited):
            last = curr
            visited.update(curr)
            nxt = set(d for c in curr for d in self.graph[c] & self.members)
            dist += 1
        if len(last) > 1:
            print(f"Multiple furthest leafs from {start}: {last}")
        return last.pop(), dist, visited

    def diameter_centers(self) -> (tuple[int], tuple[str]):
        far = tuple(self.far)[-1]
        a, _, _ = self.furthest_leaf(far)
        b, dia, visited = self.furthest_leaf(a)
        path: list[int] = self._get_path(a, b, None, visited, set())
        end = 1 + dia // 2
        beg = end - 2 + dia % 2
        # print(f"Diameter Path: {a} {b} {dia=} {path[beg:end] if path else path}")
        ah_mids = [self.ahu_height(mid, None) for mid in path[beg:end]]
        lo = min(h for a, h, m in ah_mids)
        ahu_centers = sorted((a, m) for a, h, m in ah_mids if h == lo)
        _centers = tuple(c for ahu, c in ahu_centers)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        if len(_centers) > 2:
            def _summary(p): return tuple(p[:2] + ['x'] + p[beg-1:end+1] + ['x'] + p[-2:])
            OVERCENTER.add((
                self.index,
                tuple(_centers),
                tuple(_summary(p) for p in path)
                ))
        return [_centers, _labels]

    @property
    def centers(self) -> tuple[int]:
        if not self._centers:
            self._centers, self._labels = self.prune_for_centers()
            # self._centers, self._labels = self.all_path_centers()
            # self._centers, self._labels = self.diameter_centers()
        return self._centers

    @property
    def labels(self) -> tuple[str]:
        if not self._labels:
            self._centers, self._labels = self.prune_for_centers()
            # self._centers, self._labels = self.all_path_centers()
            # self._centers, self._labels = self.diameter_centers()
        return self._labels

    def build(self, root: int) -> set[int]:
        visited = set()
        nxt = furthest = {root, }
        dist = -1
        while (curr := nxt - visited) and dist < self.radius:
            furthest = curr
            visited.update(curr)
            nxt = set(d for c in curr for d in self.graph[c])
            dist += 1
        return visited, furthest

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
    Pass tests 0-12, 18; Fail test 21; Timeout on 7 remaining of 22 tests.
    Correct answer for test 17, despite timeout.
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
    first_multiple_input = input().rstrip().split()
    n = int(first_multiple_input[0])
    r = int(first_multiple_input[1])
    edges = []
    for _ in range(n - 1):
        edges.append(list(map(int, input().rstrip().split())))
    result = jennysSubtrees(n, r, edges)
    # fptr = open(os.environ['OUTPUT_PATH'], 'w')
    # fptr.write(str(result) + '\n')
    # fptr.close()
    print(result)