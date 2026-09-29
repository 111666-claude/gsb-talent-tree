"""天赋树：点数预算、前置依赖、重置返还与环检测。

口径（见 README）：
- 剩余点数不足时拒绝点亮并抛 TalentError，点数永不为负。
- requires 里的节点至少 1 级才能点下一个。
- 重置按每个已点节点的 cost * rank 求和返还，并清空 ranks 与 spent。
- cycles(tree) 返回所有互相依赖的节点名（按名字排序）。
- 不变量：points = 初始点数 - spent；ranks[name] <= max_rank；操作可重放。
- 单次操作 O(节点度数)，不整树重扫；内存 O(节点数)。
"""


class TalentError(ValueError):
    """加点/重置请求不合法，携带出错节点名。"""

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
    """点亮一个节点：校验前置、等级上限与点数预算，全部通过才扣点。"""
    node = tree.get(name)
    if node is None:
        raise TalentError("未知节点: %s" % name, name)
    ranks = state["ranks"]
    rank = ranks.get(name, 0)
    if rank >= node.max_rank:
        raise TalentError("节点 %s 已满级 (%d)" % (name, node.max_rank), name)
    for req in node.requires:
        if ranks.get(req, 0) < 1:
            raise TalentError("节点 %s 需要先点亮 %s" % (name, req), name)
    if state["points"] < node.cost:
        raise TalentError(
            "点数不足：%s 需要 %d，剩余 %d" % (name, node.cost, state["points"]),
            name,
        )
    ranks[name] = rank + 1
    state["spent"] += node.cost
    state["points"] -= node.cost
    return state


def respec(state, tree):
    """重置：按每个已点节点的 cost * rank 求和返还，并清空 ranks 与 spent。"""
    refunded = 0
    for name, rank in state["ranks"].items():
        refunded += tree[name].cost * rank
    state["ranks"] = {}
    state["spent"] = 0
    state["points"] += refunded
    return refunded


def cycles(tree):
    """返回所有互相依赖的环：每个环是节点名列表，环内与环间均按名字排序。

    迭代版 Tarjan SCC：大小 > 1 的强连通分量，或自环节点，即为互相依赖。
    复杂度 O(节点数 + 边数)，不递归，万级节点安全。
    """
    index_of = {}
    low = {}
    on_stack = set()
    stack = []
    found = []
    counter = 0
    for root in tree:
        if root in index_of:
            continue
        index_of[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        work = [(root, iter(tree[root].requires))]
        while work:
            node, it = work[-1]
            descended = False
            for nxt in it:
                if nxt not in tree:
                    continue
                if nxt not in index_of:
                    index_of[nxt] = low[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(tree[nxt].requires)))
                    descended = True
                    break
                if nxt in on_stack and index_of[nxt] < low[node]:
                    low[node] = index_of[nxt]
            if descended:
                continue
            work.pop()
            if work and low[node] < low[work[-1][0]]:
                low[work[-1][0]] = low[node]
            if low[node] == index_of[node]:
                scc = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    scc.append(member)
                    if member == node:
                        break
                if len(scc) > 1:
                    found.append(sorted(scc))
                elif node in tree[node].requires:
                    found.append([node])
    return sorted(found)
