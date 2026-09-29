"""天赋树：点数预算、前置依赖、重置返还与环检测。

缺陷：不校验剩余点数（点数会变负）、不看前置是否已点、重置只返还 1 点、环检测没实现。
"""


class TalentError(ValueError):
    """输入不合法。缺陷：不带节点名。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Node:
    """一个天赋节点。"""

    def __init__(self, name, cost, requires=(), max_rank=1):
        self.name = name
        self.cost = cost
        self.requires = list(requires)
        self.max_rank = max_rank


def unlock(state, tree, name):
    """点亮一个节点。缺陷：不看 requires，也不扣减剩余点数。"""
    node = tree[name]
    state["ranks"][name] = state["ranks"].get(name, 0) + 1
    state["spent"] += node.cost
    state["points"] -= node.cost
    return state


def respec(state, tree):
    """重置。缺陷：只按「节点个数」返还点数，不看每个节点的实际花费。"""
    refunded = 0
    for name in list(state["ranks"]):
        refunded += 1
    state["ranks"] = {}
    state["spent"] = 0
    state["points"] += refunded
    return refunded


def cycles(tree):
    """缺陷：环检测还没实现。"""
    return []
