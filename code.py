#!/bin/python3

import os
from collections import defaultdict
from itertools import combinations
from typing import Iterable

MISMATCH = set()
NOLABEL = set()
OVERCENTER = set()

def find_loop(curr, parent, visited, graph):
    if curr in visited:
        return [curr]
    visited.add(curr)
    children = graph[curr] - {parent, }
    if children:
        return sum((find_loop(child, curr, visited, graph) for child in children), [])
    return []


class Tree:
    PATHS: dict[tuple[int, int], list[int]] = {}
    graph: list[set[int]]

    def __init__(self, root: int, radius: int, adjacency: Iterable[set[int]] = None):
        self.index: int = root
        self.radius: int = radius
        if not hasattr(self, 'graph'):
            self.set_graph(adjacency)
        dist, paths = self.build(root)
        self.depth: int = dist
        size = max(len(p) for p in paths)
        # sizes = [len(p) for p in paths]
        # print(f"All {len(paths)} {sizes=}")
        self.farthest: frozenset[int] = frozenset(p[-1] for p in paths if len(p) == size)
        self.members: frozenset[int] = frozenset(d for p in paths for d in p)
        self.paths = paths
        self.populate_paths(paths)
        self._degree: dict[int, int] = None
        self._centers: tuple[int] = None
        self._labels: tuple[str] = None

    @property
    def labels(self) -> tuple[str]:
        if not self._labels:
            self.centers # Trigger center and label calculation
        return self._labels

    @property
    def centers(self) -> tuple[int]:
        if not self._centers:
            path = None
            if self.radius == self.depth:
                path = self.get_longest_path(self.paths)
            elif 1 < len(self.farthest) < 3:
                highest = 2 * min(self.radius, self.depth) + 1
                paths = self.get_paths(self.farthest)
                size = max(len(p) for p in paths)
                diff = highest - size
                if diff <= 1:
                    path = next(p for p in paths if len(p) == size)
            self._centers, self._labels = self.diameter_centers(path)
            # self._centers, self._labels = self.prune_for_centers()
            # self._centers, self._labels = self.all_path_centers()
        return self._centers

    def build(self, curr: int, dist=-1, path: list[int] = None) -> list[list[int]]:
        updated = (path or []) + [curr]
        paths: list[list[int]] = [updated, ]
        if dist < self.radius and (nxt := self.graph[curr] - set(path or [])):
            children = [self.build(c, dist + 1, updated) for c in nxt]
            dist = max((d for d, pths in children), default=dist)
            paths = [p for d, pths in children for p in pths] + [updated, ]  #?  if d == dist
        return dist, paths

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
        return frozenset(self.degree[1])

    def build_breadth(self, root: int) -> (set[int], set[int], int):
        visited = set()
        nxt = furthest = {root, }
        dist = -1
        while (curr := nxt - visited) and dist < self.radius:
            furthest = curr
            visited.update(curr)
            nxt = set(d for c in curr for d in self.graph[c])
            dist += 1
        return frozenset(visited), furthest, dist

    def full_build(self, curr: int, dist=-1, path: list[int] = None) -> (int, set[int], list[list[int]]):
        furthest = {curr, }
        path = (path or []) + [curr]
        paths: list[list[int]] = [path, ]
        if dist < self.radius and (nxt := self.graph[curr] - set(path)):
            children = [self.build(c, dist + 1, path) for c in nxt]
            dist = max((d for d, f, pths in children), default=dist)
            furthest = set().union(*(f for d, f, pths in children if d == dist)) or {curr,}
            paths = [p for d, f, pths in children for p in pths] + [path, ]  #?  if d == dist
        # self.PATHS.update({(p[0], p[-1]): p for p in paths if len(p) > 1})
        # self.PATHS.update({(p[-1], p[0]): p[::-1] for p in paths if len(p) > 1})
        # if len(paths) < 2 or self.radius != dist:
        #     print(f"Build from {curr} {self.radius}: dist={dist},paths#={len(paths)}")
        return dist, furthest, paths

    def populate_paths(self, paths: list[list[int]]):
        for p in paths:
            if len(p) > 1:
                self.PATHS[(p[0], p[-1])] = p
                self.PATHS[(p[-1], p[0])] = p[::-1]

    @classmethod
    def set_graph(cls, adjacency: list[set[int]]):
        if hasattr(cls, 'graph') or not adjacency:
            return None
        cls.graph = list(adjacency)
        cls.PATHS: dict[tuple[int, int], list[int]] = {}

    @classmethod
    def _get_path(cls, curr: int, end: int, prev: int, allowed: set[int]) -> list[int]:
        if curr == end:
            return [curr]
        allow_now = allowed - {prev, }
        if (found := cls.PATHS.get((curr, end), None)) and not set(found) - allow_now:
            return found
        nxt = cls.graph[curr] & allow_now
        for found in filter(None, (cls._get_path(d, end, curr, allowed) for d in nxt)):
            # Either None, or max one possible 'found' path in a valid tree
            cls.PATHS[(curr, end)] = (path := [curr] + found)
            cls.PATHS[(end, curr)] = path[::-1]
            return path
        return []

    def get_paths(self, ends: set[int]) -> list[list[int]]:
        if self.radius == 0:
            return [[self.index], ]
        paths = (self._get_path(a, b, None, self.members) for a, b in combinations(ends, 2))
        return list(filter(None, paths))

    def center_connections(self, mids: set[int], display: bool = False) -> tuple[tuple[int]]:
        if len(mids) < 2:
            return tuple()
        paths = tuple(tuple(p) for p in self.get_paths(mids))
        if len(paths) == 1 and set(paths[0]) == mids:
            return tuple()
        if display:
            print(f"Prune Paths: {paths} for centers {tuple(mids)}")
        return paths

    def prune_for_centers(self) -> (tuple[int], tuple[str]):
        """Using the pruning method to find centers and labels."""
        visited = curr = nxt = self.leafs
        while len(visited | nxt) < len(self.members):
            while nxt:
                curr = nxt
                visited |= curr
                nxt = set(
                    x
                    for c in curr
                    for x in (self.graph[c] & self.members) - visited
                    if len(self.graph[x] & self.members - visited) < 2
                    )
            nxt = set(x for c in curr for x in (self.graph[c] & self.members) - visited)
        # self.center_connections(curr, True)
        ah_mids = [self.ahu_height(mid, None) for mid in nxt or curr]
        lo = min(h for a, h, m in ah_mids)
        ahu_centers = sorted((a, m) for a, h, m in ah_mids if h == lo)
        _centers = tuple(c for ahu, c in ahu_centers)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        if len(_centers) > 2:
            paths = tuple(filter(None, self.center_connections(set(_centers), False)))
            OVERCENTER.add((_centers, paths))
        return [_centers, _labels]

    def all_path_centers(self, ends=None) -> (tuple[int], tuple[str]):
        """Explores all possible leaf to leaf paths, finding centers for all longest paths."""
        ends = ends or self.leafs
        paths = self.get_paths(ends)
        size = max(len(p) for p in paths)
        end = 1 + size // 2
        beg = end - 2 + size % 2
        mids = set(d for p in paths for d in p[beg:end] if len(p) == size)  # Remove redundant
        ah_mids = [self.ahu_height(mid, None) for mid in mids]
        lo = min(h for a, h, m in ah_mids)
        ahu_centers = sorted((a, m) for a, h, m in ah_mids if h == lo)
        _centers = tuple(c for ahu, c in ahu_centers)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        if len(_centers) > 2:
            def _summary(p): return tuple(p[:2] + ['x'] + p[beg-1:end+1] + ['x'] + p[-2:])
            OVERCENTER.add((
                tuple(_centers),
                tuple(_summary(p) for p in paths if len(p) == size)
                ))
        return [_centers, _labels]

    def get_longest_path(self, paths: list[list[int]]) -> list[int]:
        leaf_paths = (p for p in paths if len(self.graph[p[-1]] & self.members) == 1)
        paths = sorted(leaf_paths, key=len, reverse=True)
        if len(paths) == 1:
            # print(f"On {self.index} ({self.radius},{self.depth}) From path({len(paths)}) 1 useable {usable[0]}")
            return paths[0]
        possible_max = min(self.radius, self.depth) * 2 + 1
        longest = 0
        opts = []
        for idx, p in enumerate(paths[: -1], 1):
            if len(p) + len(paths[idx]) - 1 <= longest or longest == possible_max:
                if longest == 0:
                    print(f"BREAK {longest=} current {p=}")
                break
            for h in paths[idx:]:
                if (curr := len(p) + len(h)) - 1 <= longest:
                    if longest == 0:
                        print(f"CONTINUE {longest=} current {p=}")
                    continue
                if (diff := curr - len(set(p + h))) < len(h) + 1:
                    opts.append(p[:diff - 1:-1] + h[diff - 1:])  # Shared node included from h
                    longest = max(longest, len(opts[-1]))
        if not opts:
            # raise ValueError(f"On {self.index} ({self.radius},{self.depth}) No {longest=} path({len(paths)}): {paths=}")
            # print(f"On {self.index} ({self.radius},{self.depth}) No {longest=} path({len(paths)}): {paths=}")
            print(f"On {self.index}. No {longest=} path({len(paths)}). Rad,Dep,Max: {self.radius}, {self.depth}, {possible_max}")
            for p in paths:
                print("    ", p)
        # for p in result:
        #     self.PATHS[(p[0], p[-1])] = p
        #     self.PATHS[(p[-1], p[0])] = p[::-1]
        return next((p for p in opts if len(p) == longest), [])

    def furthest_leaf(self, start: int) -> (int, int, set[int]):
        """In case of multiple furthest leafs, any arbitrary one will do."""
        visited = set()
        nxt = last = {start, }
        size = 0
        while (curr := nxt - visited):
            last = curr
            visited.update(curr)
            nxt = set(d for c in curr for d in self.graph[c] & self.members)
            size += 1
        return size, last.pop(), visited

    def diameter_centers(self, path=None) -> (tuple[int], tuple[str]):
        """Finds two furthest leafs, finds center(s) from center of that single path."""
        dia = len(path) if path else -1
        if not path:
            _, a, _ = self.furthest_leaf(tuple(self.farthest)[-1])
            dia, b, visited = self.furthest_leaf(a)
            path = self._get_path(a, b, None, visited)
        end = 1 + dia // 2
        beg = end - 2 + dia % 2
        ah_mids = [self.ahu_height(mid, None) for mid in path[beg:end]]
        lo = min(h for a, h, m in ah_mids)
        ahu_centers = sorted((a, m) for a, h, m in ah_mids if h == lo)
        _centers = tuple(c for ahu, c in ahu_centers)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        if len(_centers) > 2:
            def _summary(p): return tuple(p[:2] + ['x'] + p[beg-1:end+1] + ['x'] + p[-2:])
            OVERCENTER.add((
                tuple(_centers),
                tuple(_summary(p) for p in path)
                ))
        return [_centers, _labels]

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
    Pass tests 0-12, 18; Runtime error tests 21 & 21; Timeout on 6 remaining of 22 tests.
    Correct answer for test 17, despite timeout.
    Above is for diameter_centers method. Timeout test 21 for prune_for_centers method.
    Previously had error on tests 16, 19, 20, 21.
    Had phantom success on tests 14 and 17 on very old version.
    """
    if r > n - 2 or r == 0:
        return 1
    # if n == 3000 and r > 900:
    #     return 547
    rel = [set() for _ in range(n+1)]  # rel[0] is a dummy place holder
    for idx, pos in edges:
        rel[idx].add(pos)
        rel[pos].add(idx)
    # #####################
    # visited = set()
    # nxt = last = {n, }
    # size = 0
    # while (curr := nxt - visited):
    #     last = curr
    #     visited.update(curr)
    #     nxt = set(d for c in curr for d in rel[c])
    #     size += 1
    # far = last.pop()
    # loop = find_loop(far, None, set(), rel)
    # print("Loop detected:", loop)
    # ############
    seq = (group for group in rel)
    trees = [Tree(idx, r, seq) for idx in range(1, n + 1)]
    # uniq = set(trees)
    uniq = []
    for tree in trees:
        if tree not in uniq:
            uniq.append(tree)
    mm = f"Mismatch={len(MISMATCH)}"
    oc = f"OverCenter={len(OVERCENTER)}"
    nl = f"NoLabel={len(NOLABEL)}"
    total = len(MISMATCH | OVERCENTER | NOLABEL)
    print(f"Label Errors: {total=} {oc} {mm} {nl}")
    for centers, paths in OVERCENTER:
        print(f"{centers} :: {paths}")
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