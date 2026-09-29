import random
import time
import unittest

from talenttree.tree import Node, TalentError, cycles, respec, unlock


def tree():
    return {"a": Node("a", 3, []), "b": Node("b", 4, []), "c": Node("c", 2, ["a"])}


def state(points=10):
    return {"points": points, "spent": 0, "ranks": {}}


class UnlockTest(unittest.TestCase):
    def test_rank_increases(self):
        st = state()
        unlock(st, tree(), "a")
        self.assertEqual(st["ranks"]["a"], 1)

    def test_spent_counts_cost(self):
        st = state()
        unlock(st, tree(), "b")
        self.assertEqual(st["spent"], 4)

    def test_error_type_exists(self):
        self.assertTrue(issubclass(TalentError, ValueError))

    def test_error_carries_node_name(self):
        st = state()
        with self.assertRaises(TalentError) as ctx:
            unlock(st, tree(), "zzz")
        self.assertEqual(ctx.exception.name, "zzz")


class BudgetTest(unittest.TestCase):
    def test_insufficient_points_rejected(self):
        st = state(points=5)
        unlock(st, tree(), "a")
        with self.assertRaises(TalentError):
            unlock(st, tree(), "b")
        self.assertEqual(st["points"], 2)
        self.assertEqual(st["spent"], 3)
        self.assertNotIn("b", st["ranks"])

    def test_points_never_negative(self):
        st = state(points=1)
        for name in ("a", "b", "c"):
            with self.assertRaises(TalentError):
                unlock(st, tree(), name)
        self.assertEqual(st["points"], 1)
        self.assertGreaterEqual(st["points"], 0)

    def test_max_rank_enforced(self):
        t = {"a": Node("a", 1, [], max_rank=2)}
        st = state()
        unlock(st, t, "a")
        unlock(st, t, "a")
        with self.assertRaises(TalentError):
            unlock(st, t, "a")
        self.assertEqual(st["ranks"]["a"], 2)


class PrereqTest(unittest.TestCase):
    def test_requires_must_be_unlocked_first(self):
        st = state()
        with self.assertRaises(TalentError):
            unlock(st, tree(), "c")
        unlock(st, tree(), "a")
        unlock(st, tree(), "c")
        self.assertEqual(st["ranks"]["c"], 1)

    def test_prereq_lost_after_respec(self):
        st = state()
        unlock(st, tree(), "a")
        unlock(st, tree(), "c")
        respec(st, tree())
        with self.assertRaises(TalentError):
            unlock(st, tree(), "c")


class RespecTest(unittest.TestCase):
    def test_ranks_cleared(self):
        st = state()
        unlock(st, tree(), "a")
        respec(st, tree())
        self.assertEqual(st["ranks"], {})
        self.assertEqual(st["spent"], 0)

    def test_refund_is_actual_cost(self):
        st = state(points=5)
        unlock(st, tree(), "a")
        unlock(st, tree(), "c")
        self.assertEqual(respec(st, tree()), 5)
        self.assertEqual(st["points"], 5)

    def test_refund_counts_ranks(self):
        t = {"a": Node("a", 2, [], max_rank=3)}
        st = state(points=10)
        for _ in range(3):
            unlock(st, t, "a")
        self.assertEqual(respec(st, t), 6)
        self.assertEqual(st["points"], 10)


class CycleTest(unittest.TestCase):
    def test_cycles_returns_list(self):
        self.assertEqual(cycles({}), [])

    def test_acyclic_has_no_cycles(self):
        self.assertEqual(cycles(tree()), [])

    def test_mutual_dependency(self):
        looped = {"x": Node("x", 1, ["y"]), "y": Node("y", 1, ["x"])}
        self.assertEqual(cycles(looped), [["x", "y"]])

    def test_self_loop(self):
        self.assertEqual(cycles({"s": Node("s", 1, ["s"])}), [["s"]])

    def test_multiple_cycles_sorted(self):
        t = {
            "x": Node("x", 1, ["y"]),
            "y": Node("y", 1, ["x"]),
            "p": Node("p", 1, ["q"]),
            "q": Node("q", 1, ["p"]),
            "ok": Node("ok", 1, []),
        }
        self.assertEqual(cycles(t), [["p", "q"], ["x", "y"]])

    def test_cycle_member_with_acyclic_tail(self):
        t = {
            "x": Node("x", 1, ["y"]),
            "y": Node("y", 1, ["x"]),
            "z": Node("z", 1, ["x"]),
        }
        self.assertEqual(cycles(t), [["x", "y"]])


def random_tree(rng, size):
    t = {}
    names = ["n%d" % i for i in range(size)]
    for i, name in enumerate(names):
        reqs = rng.sample(names[:i], k=min(i, rng.randint(0, 2)))
        t[name] = Node(name, rng.randint(1, 5), reqs, max_rank=rng.randint(1, 3))
    return t


def random_ops(rng, names, count):
    ops = []
    for _ in range(count):
        if rng.random() < 0.15:
            ops.append(("respec", None))
        else:
            ops.append(("unlock", rng.choice(names)))
    return ops


def apply_ops(tree_, initial_points, ops):
    st = state(points=initial_points)
    for op, name in ops:
        if op == "respec":
            respec(st, tree_)
        else:
            try:
                unlock(st, tree_, name)
            except TalentError:
                pass
    return st


def reference_run(tree_, initial_points, ops):
    """参考实现：按前置拓扑序 + 预算校验。"""
    points, spent, ranks = initial_points, 0, {}
    for op, name in ops:
        if op == "respec":
            points += spent
            spent, ranks = 0, {}
            continue
        node = tree_[name]
        if ranks.get(name, 0) >= node.max_rank:
            continue
        if any(ranks.get(req, 0) < 1 for req in node.requires):
            continue
        if points < node.cost:
            continue
        ranks[name] = ranks.get(name, 0) + 1
        spent += node.cost
        points -= node.cost
    return points, spent, ranks


def topological_order(tree_):
    indegree = {name: 0 for name in tree_}
    dependents = {name: [] for name in tree_}
    for name, node in tree_.items():
        for req in node.requires:
            if req in tree_:
                indegree[name] += 1
                dependents[req].append(name)
    queue = sorted(name for name, deg in indegree.items() if deg == 0)
    order = []
    while queue:
        name = queue.pop()
        order.append(name)
        for nxt in dependents[name]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    return order


def reference_unlockable(tree_, points, ranks):
    """按拓扑序返回当前可点亮的节点集合。"""
    able = set()
    for name in topological_order(tree_):
        node = tree_[name]
        if ranks.get(name, 0) >= node.max_rank:
            continue
        if node.cost > points:
            continue
        if all(ranks.get(req, 0) >= 1 for req in node.requires):
            able.add(name)
    return able


def actual_unlockable(tree_, st):
    """用真实 unlock 探测当前可点亮的节点集合。"""
    able = set()
    for name in tree_:
        probe = {"points": st["points"], "spent": st["spent"], "ranks": dict(st["ranks"])}
        try:
            unlock(probe, tree_, name)
        except TalentError:
            continue
        able.add(name)
    return able


class ReferenceComparisonTest(unittest.TestCase):
    def test_200_random_sequences_match_reference(self):
        rng = random.Random(20240901)
        mismatches = 0
        for _ in range(200):
            t = random_tree(rng, size=12)
            initial = rng.randint(0, 30)
            ops = random_ops(rng, list(t), count=40)
            st = apply_ops(t, initial, ops)
            ref_points, ref_spent, ref_ranks = reference_run(t, initial, ops)
            if (st["points"], st["spent"], st["ranks"]) != (ref_points, ref_spent, ref_ranks):
                mismatches += 1
            if actual_unlockable(t, st) != reference_unlockable(t, ref_points, ref_ranks):
                mismatches += 1
        self.assertEqual(mismatches, 0)


class InvariantTest(unittest.TestCase):
    def test_points_equals_initial_minus_spent(self):
        rng = random.Random(7)
        t = random_tree(rng, size=20)
        initial = 50
        st = apply_ops(t, initial, random_ops(rng, list(t), count=200))
        self.assertEqual(st["points"], initial - st["spent"])

    def test_rank_never_exceeds_max_rank(self):
        rng = random.Random(8)
        t = random_tree(rng, size=20)
        st = apply_ops(t, 500, random_ops(rng, list(t), count=500))
        for name, rank in st["ranks"].items():
            self.assertLessEqual(rank, t[name].max_rank)

    def test_deterministic_replay(self):
        rng = random.Random(9)
        t = random_tree(rng, size=15)
        ops = random_ops(rng, list(t), count=100)
        first = apply_ops(t, 25, ops)
        second = apply_ops(t, 25, ops)
        self.assertEqual(first, second)


class ScaleTest(unittest.TestCase):
    def test_10k_nodes_100k_ops_under_1s(self):
        rng = random.Random(42)
        t = random_tree(rng, size=10000)
        names = list(t)
        ops = random_ops(rng, names, count=100000)
        start = time.perf_counter()
        st = apply_ops(t, 100000, ops)
        elapsed = time.perf_counter() - start
        self.assertEqual(st["points"], 100000 - st["spent"])
        self.assertLess(elapsed, 1.0, "100k ops took %.3fs" % elapsed)


if __name__ == "__main__":
    unittest.main()
