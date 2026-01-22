#!/bin/python3

import os
from collections import defaultdict, Counter
from itertools import combinations, chain
from typing import Iterable

MISMATCH = set()
NOLABEL = set()
OVERCENTER = set()
PATHCENTERS: list[set[int]] = []
TECHNIQUE = []


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
        self.origin: int = root
        self.radius: int = radius
        if not hasattr(self, 'graph'):
            self.set_graph(adjacency)
        self.paths: list[list[int]] = []  # All paths from origin
        self.leaf_paths: list[list[int]] = []  # origin to leaf paths
        members, furthest, dist = self.build(root)
        self.members: frozenset[int] = members
        self.farthest: list[int] = furthest
        self.depth: int = dist
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
            path = self.easy_long_path(self.leaf_paths) or None
            if path:
                TECHNIQUE.append(('Make', self.radius, len(self.leaf_paths), len(self.paths), self.farthest))
            else:
                TECHNIQUE.append(('Leaf', self.radius, len(self.leaf_paths), len(self.paths), self.farthest))
            self._centers, self._labels = self.diameter_centers(path)
            # self._centers, self._labels = self.prune_for_centers()
            # self._centers, self._labels = self.all_path_centers()
        return self._centers

    def build(self, curr: int) -> (set[int], set[int], int):
        # b_members, b_furthest, b_dist = self.build_breadth(curr)
        dist, paths = self.build_depth(curr)
        furthest = [p[-1] for p in paths if len(p) == dist + 1]
        members = set().union(*paths)
        self.paths = paths
        self.leaf_paths = [p for p in paths if len(self.graph[p[-1]] & members) == 1]
        if len(self.leaf_paths) > len(furthest) > 1:
            self.leaf_paths = [p for p in self.leaf_paths if p[-1] in furthest]
        if len(furthest) == 1:
            furthest = [p[-1] for p in paths if len(p) == dist] + furthest
        # d_mem = len(d_members) - len(b_members)
        # d_fur = len(d_furthest & b_furthest)
        # d_dis = d_dist - b_dist
        # # o_mem = members - g_members
        # o_fur = d_furthest - b_furthest
        # o_fur = 'ALL' if o_fur == d_furthest else len(o_fur)
        # m_fur = b_furthest - d_furthest
        # m_fur = 'ALL' if m_fur == b_furthest else len(m_fur)
        # print(f"{d_dis} mem:{d_mem} far:{d_fur} Over:{o_fur} Miss:{m_fur}")
        return frozenset(members), furthest, dist

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

    def build_depth(self, curr: int, dist=0, path: list[int] = None) -> (int, list[list[int]]):
        updated = (path or []) + [curr]
        paths: list[list[int]] = [updated, ]
        if dist < self.radius and (nxt := self.graph[curr] - set(path or [])):
            children = [self.build_depth(c, dist + 1, updated) for c in nxt]
            dist = max((d for d, pths in children), default=dist)
            paths = [p for d, pths in children for p in pths] + [updated, ]  #?  if d == dist
        return dist, paths

    def build_breadth(self, root: int) -> (set[int], set[int], int):
        visited = set()
        nxt = furthest = {root, }
        dist = -1
        while (curr := nxt - visited) and dist < self.radius:
            furthest = curr
            visited.update(curr)
            nxt = set(d for c in curr for d in self.graph[c])
            dist += 1
        return visited, furthest, dist

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
            return [[ea] for ea in ends]
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

    def prune_path_center(self, start: int, last: int, size: int, allowed: set[int]) -> set[int]:
        """Using the pruning method to find center for single path."""
        visited, seen = set(), set()
        nxt, end = {start, }, {last, }
        for _ in range(size // 2):
            visited |= nxt
            seen |= end
            nxt = set(x for c in nxt for x in self.graph[c] & allowed - visited)
            end = set(x for c in end for x in self.graph[c] & allowed - seen)
        centers = nxt & end if size % 2 else nxt & seen | end & visited
        PATHCENTERS.append(tuple(centers))
        return centers

    def prune_for_centers(self, leafs, allowed: set[int]) -> (tuple[int], tuple[str]):
        """Using the pruning method to find centers and labels."""
        visited = curr = nxt = leafs
        while len(visited | nxt) < len(allowed):
            while nxt:
                curr = nxt
                visited |= curr
                nxt = set(
                    x
                    for c in curr
                    for x in (self.graph[c] & allowed) - visited
                    if len(self.graph[x] & allowed - visited) < 2
                    )
            nxt = set(x for c in curr for x in (self.graph[c] & allowed) - visited)
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

    def easy_long_path(self, paths: list[list[int]]) -> list[int]:
        """Combines two origin to leaf paths into one longest path, if possible."""
        if len(paths) == 1:
            return paths[0]
        depth = min(self.radius, self.depth)
        best = [p for p in paths if len(p) == depth + 1]
        size = 2 * depth + 1
        while len(best) < 2:
            best += [p for p in paths if len(p) == depth]
            depth -= 1
            size -= 1
        long_max = (a[:0:-1] + b for a, b in combinations(best, 2) if len(set(a + b)) == size)
        res = next(long_max, [])
        return res

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
        """Find center(s) from given longest path or from two furthest leafs."""
        if path:
            dia = len(path)
            end = 1 + dia // 2
            beg = end - 2 + dia % 2
            mids = path[beg:end]
        else:
            _, a, _ = self.furthest_leaf(tuple(self.farthest)[-1])
            dia, b, visited = self.furthest_leaf(a)
            mids = self.prune_path_center(a, b, dia, visited)
        ah_mids = [self.ahu_height(mid, None) for mid in mids]
        lo = min(h for a, h, m in ah_mids)
        ahu_centers = sorted((a, m) for a, h, m in ah_mids if h == lo)
        _centers = tuple(c for ahu, c in ahu_centers)
        _labels = tuple(ahu for ahu, c in ahu_centers)
        # print(f"{self.radius - self.depth} {dia} {path[0]} to {path[-1]}: {_centers}")
        if len(_centers) > 2:
            def _summary(p): return tuple(p[:2] + ['x'] + p[beg-1:end+1] + ['x'] + p[-2:])
            OVERCENTER.add((
                tuple(_centers),
                tuple(_summary(p) for p in path or [])
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
    mid_cnt = Counter(len(ea) for ea in PATHCENTERS)
    mid_cnt['GOOD'] = mid_cnt[1] + mid_cnt[2]
    del mid_cnt[1]
    del mid_cnt[2]
    print(f"Path Centers {mid_cnt.items()}")
    for ea in PATHCENTERS:
        if 0 < len(ea) < 3:
            continue
        print(f"  {ea}")
    for centers, paths in OVERCENTER:
        print(f"{centers} :: {paths}")
    for tree, members in NOLABEL:
        print(f"{members=} {tree}")
    for tree, missing in MISMATCH:
        print(f"{missing=} {tree}")
    tech = defaultdict(list)
    for t, r, lp, ap, f in TECHNIQUE:
        tech[t].append((r, lp, ap, f))
    for label in ('Make', 'Get', 'Leaf'):
        tech.setdefault(label, [(0, 0, 0, [])])
    num = len(tech['Make'])
    fl = min(len(f) for r, pl, pa, f in tech['Make'])
    fh = max(len(f) for r, pl, pa, f in tech['Make'])
    ll = min(pl for r, pl, pa, f in tech['Make'])
    lh = max(pl for r, pl, pa, f in tech['Make'])
    al = min(pa for r, pl, pa, f in tech['Make'])
    ah = max(pa for r, pl, pa, f in tech['Make'])
    txt = f"Make:{num} far({fl} {fh}) *leaf_p({ll} {lh})* all_p({al} {ah}) "
    num = len(tech['Get'])
    fl = min(len(f) for r, pl, pa, f in tech['Get'])
    fh = max(len(f) for r, pl, pa, f in tech['Get'])
    ll = min(pl for r, pl, pa, f in tech['Get'])
    lh = max(pl for r, pl, pa, f in tech['Get'])
    al = min(pa for r, pl, pa, f in tech['Get'])
    ah = max(pa for r, pl, pa, f in tech['Get'])
    txt += f"Get:{num} far({fl} {fh}) leaf_p({ll} {lh}) *all_p({al} {ah})* "
    num = len(tech['Leaf'])
    fl = min(len(f) for r, pl, pa, f in tech['Leaf'])
    fh = max(len(f) for r, pl, pa, f in tech['Leaf'])
    ll = min(pl for r, pl, pa, f in tech['Leaf'])
    lh = max(pl for r, pl, pa, f in tech['Leaf'])
    al = min(pa for r, pl, pa, f in tech['Leaf'])
    ah = max(pa for r, pl, pa, f in tech['Leaf'])
    txt += f"Leaf:{num} *far({fl} {fh})* leaf_p({ll} {lh}) all_p({al} {ah}) "
    print(txt)
    for radius, p_leaf, p_all, leafs in tech['Make']:
        print(f"   Make {p_leaf=} {leafs=}")
    for radius, p_leaf, p_all, leafs in tech['Get']:
        print(f"   Get {p_leaf=} {p_all=} leafs#{len(leafs)}")
    for radius, p_leaf, p_all, leafs in tech['Leaf']:
        print(f"   Leaf {p_leaf=} {p_all=} leafs#{len(leafs)}")
    print(txt)
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