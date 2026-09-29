"""天赋树：点数预算、前置依赖、重置返还与环检测。

口径（README 为准）：
- 剩余点数不足时拒绝点亮并抛 TalentError，点数永不为负。
- requires 里的节点至少 1 级才能点下一个。
- 重置按每个已点节点的实际花费（cost * rank）返还，并清空 ranks 与 spent。
- cycles(tree) 返回所有互相依赖的环：每个环是按名字排序的节点名列表，
  环与环之间同样按名字排序。
- 单次操作只触碰目标节点及其直接前置，不重扫整棵树。
"""


class TalentError(ValueError):
    """输入不合法；携带出错的节点名。"""

    def __init__(self, message, name=None):
        super().__init__(message)
        self.message = message
        self.name = name


class Node:
    """一个天赋节点。"""

    def __init__(self, name, cost, requires=(), max_rank=1):
        self.name = name
        self.cost = cost
        self.requires = list(requires)
        self.max_rank = max_rank


def unlock(state, tree, name):
    """点亮一个节点：先校验节点存在、等级上限、前置与剩余点数，全部通过才扣点。"""
    try:
        node = tree[name]
    except KeyError:
        raise TalentError("未知天赋: %s" % name, name) from None
    ranks = state["ranks"]
    rank = ranks.get(name, 0)
    if rank >= node.max_rank:
        raise TalentError("已达等级上限: %s (max_rank=%d)" % (name, node.max_rank), name)
    for req in node.requires:
        if ranks.get(req, 0) < 1:
            raise TalentError("前置未点亮: %s 需要 %s" % (name, req), name)
    if state["points"] < node.cost:
        raise TalentError(
            "点数不足: %s 需要 %d，剩余 %d" % (name, node.cost, state["points"]), name
        )
    ranks[name] = rank + 1
    state["spent"] += node.cost
    state["points"] -= node.cost
    return state


def respec(state, tree):
    """重置：按每个已点节点的实际花费（cost * rank）返还，并清空 ranks 与 spent。"""
    refunded = 0
    for name, rank in state["ranks"].items():
        refunded += tree[name].cost * rank
    state["ranks"] = {}
    state["spent"] = 0
    state["points"] += refunded
    return refunded


def cycles(tree):
    """返回所有互相依赖的环。

    每个环是一个按名字排序的节点名列表（同一强连通分量，或自环），
    环与环之间按名字排序；无环时返回空列表。复杂度 O(节点数 + 依赖边数)。
    """
    index_of = {}
    lowlink = {}
    on_stack = set()
    stack = []
    result = []
    next_index = 0

    for root in tree:
        if root in index_of:
            continue
        index_of[root] = lowlink[root] = next_index
        next_index += 1
        stack.append(root)
        on_stack.add(root)
        work = [(root, iter(tree[root].requires))]
        while work:
            node, edges = work[-1]
            descended = False
            for nxt in edges:
                if nxt not in tree:
                    continue
                if nxt not in index_of:
                    index_of[nxt] = lowlink[nxt] = next_index
                    next_index += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(tree[nxt].requires)))
                    descended = True
                    break
                if nxt in on_stack:
                    if index_of[nxt] < lowlink[node]:
                        lowlink[node] = index_of[nxt]
            if descended:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                if lowlink[node] < lowlink[parent]:
                    lowlink[parent] = lowlink[node]
            if lowlink[node] == index_of[node]:
                scc = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    scc.append(member)
                    if member == node:
                        break
                if len(scc) > 1 or node in tree[node].requires:
                    result.append(sorted(scc))
    result.sort()
    return result
