# subtree_isomorphic

Jenny loves experimenting with trees. Her favorite tree has `n` nodes connected by `n-1` edges, and each edge is `1` unit in length. She wants to cut a subtree (i.e., a connected part of the original tree) of radius `r` from this tree by performing the following two steps:

1. Choose a node, `x`, from the tree.
2. Cut a subtree consisting of all nodes which are not further than `r` units from node `x`.

## Input Format

The first line contains two space-separated integers denoting the respective values of `n` and  `r`.
Each of the next `n-1` subsequent lines contains two space-separated integers, `x` and `y`, describing a bidirectional edge in Jenny's tree having length `1`.

## Constraints

* 1 <= n <= 3000
* 0 <= r <= 3000
* 1 <= x,y <= n

### Subtasks

For 50% of the max score:

* 1 <= n <= 500
* 0 <= r <= 500

## Output Format

Print the total number of different possible subtrees.
