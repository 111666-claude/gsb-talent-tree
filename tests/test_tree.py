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
        s = state()
        unlock(s, tree(), "a")
        self.assertEqual(s["ranks"]["a"], 1)

    def test_spent_counts_cost(self):
        s = state()
        unlock(s, tree(), "b")
        self.assertEqual(s["spent"], 4)

    def test_error_type_exists(self):
        self.assertTrue(issubclass(TalentError, ValueError))

    def test_budget_insufficient_rejected(self):
        s = state(points=5)
        unlock(s, tree(), "a")
        with self.assertRaises(TalentError):
            unlock(s, tree(), "b")
        self.assertEqual(s["points"], 2)
        self.assertEqual(s["spent"], 3)
        self.assertNotIn("b", s["ranks"])

    def test_points_never_negative(self):
        s = state(points=1)
        for name in ("a", "b", "c"):
            with self.assertRaises(TalentError):
                unlock(s, tree(), name)
        self.assertGreaterEqual(s["points"], 0)
        self.assertEqual(s["spent"], 0)

    def test_requires_must_be_unlocked_first(self):
        s = state()
        with self.assertRaises(TalentError):
            unlock(s, tree(), "c")
        self.assertNotIn("c", s["ranks"])
        unlock(s, tree(), "a")
        unlock(s, tree(), "c")
        self.assertEqual(s["ranks"]["c"], 1)

    def test_max_rank_enforced(self):
        t = {"a": Node("a", 1, [], max_rank=2)}
        s = state()
        unlock(s, t, "a")
        unlock(s, t, "a")
        self.assertEqual(s["ranks"]["a"], 2)
        with self.assertRaises(TalentError):
            unlock(s, t, "a")
        self.assertLessEqual(s["ranks"]["a"], t["a"].max_rank)

    def test_unknown_node_rejected(self):
        with self.assertRaises(TalentError):
            unlock(state(), tree(), "zzz")


class RespecTest(unittest.TestCase):
    def test_ranks_cleared(self):
        s = state()
        unlock(s, tree(), "a")
        respec(s, tree())
        self.assertEqual(s["ranks"], {})
        self.assertEqual(s["spent"], 0)

    def test_refunds_actual_cost(self):
        s = state(points=5)
        unlock(s, tree(), "a")
        unlock(s, tree(), "c")
        self.assertEqual(respec(s, tree()), 5)
        self.assertEqual(s["points"], 5)
        self.assertEqual(s["spent"], 0)

    def test_refund_counts_ranks(self):
        t = {"a": Node("a", 2, [], max_rank=3)}
        s = state(points=10)
        for _ in range(3):
            unlock(s, t, "a")
        self.assertEqual(respec(s, t), 6)
        self.assertEqual(s["points"], 10)


class CyclesTest(unittest.TestCase):
    def test_cycles_returns_list(self):
        self.assertEqual(cycles({}), [])

    def test_acyclic_has_no_cycles(self):
        self.assertEqual(cycles(tree()), [])

    def test_mutual_dependency_detected(self):
        looped = {"x": Node("x", 1, ["y"]), "y": Node("y", 1, ["x"])}
        self.assertEqual(cycles(looped), [["x", "y"]])

    def test_self_loop_detected(self):
        self.assertEqual(cycles({"s": Node("s", 1, ["s"])}), [["s"]])

    def test_multiple_cycles_sorted(self):
        t = {
            "a": Node("a", 1, ["b"]), "b": Node("b", 1, ["a"]),
            "m": Node("m", 1, ["n"]), "n": Node("n", 1, ["m"]),
            "z": Node("z", 1, ["a"]),
        }
        self.assertEqual(cycles(t), [["a", "b"], ["m", "n"]])


def ref_unlockable(t, ranks, points):
    """参考实现：按前置 + 等级上限 + 预算校验，返回可点集合。"""
    ok = set()
    for name, node in t.items():
        if ranks.get(name, 0) >= node.max_rank:
            continue
        if any(ranks.get(req, 0) < 1 for req in node.requires):
            continue
        if node.cost > points:
            continue
        ok.add(name)
    return ok


class CrossCheckTest(unittest.TestCase):
    def test_random_sequences_match_reference(self):
        rng = random.Random(20260930)
        for trial in range(200):
            names = ["n%d" % i for i in range(rng.randint(2, 12))]
            t = {}
            for name in names:
                reqs = [r for r in names if r != name and rng.random() < 0.25]
                t[name] = Node(name, rng.randint(1, 4), reqs,
                               max_rank=rng.randint(1, 3))
            initial = rng.randint(3, 20)
            s = state(points=initial)
            ref_ranks, ref_points, ref_spent = {}, s["points"], 0
            for _ in range(rng.randint(5, 40)):
                if rng.random() < 0.15:
                    refunded = respec(s, t)
                    expect = sum(t[n].cost * r for n, r in ref_ranks.items())
                    self.assertEqual(refunded, expect)
                    ref_ranks, ref_spent = {}, 0
                    ref_points += refunded
                else:
                    name = rng.choice(names)
                    can = name in ref_unlockable(t, ref_ranks, ref_points)
                    try:
                        unlock(s, t, name)
                        did = True
                    except TalentError:
                        did = False
                    self.assertEqual(did, can, "trial=%d name=%s" % (trial, name))
                    if can:
                        ref_ranks[name] = ref_ranks.get(name, 0) + 1
                        ref_points -= t[name].cost
                        ref_spent += t[name].cost
                self.assertEqual(s["points"], ref_points)
                self.assertEqual(s["spent"], ref_spent)
                self.assertEqual(s["ranks"], ref_ranks)
                self.assertEqual(
                    ref_unlockable(t, s["ranks"], s["points"]),
                    ref_unlockable(t, ref_ranks, ref_points),
                )
                self.assertEqual(s["points"], initial - s["spent"])
                self.assertGreaterEqual(s["points"], 0)

    def test_replay_is_deterministic(self):
        t = tree()

        def run():
            s = state(points=5)
            for name in ("a", "c", "b", "a"):
                try:
                    unlock(s, t, name)
                except TalentError:
                    pass
            respec(s, t)
            return s["points"], s["spent"], dict(s["ranks"])

        self.assertEqual(run(), run())


class ScaleTest(unittest.TestCase):
    def test_10k_nodes_100k_ops_under_1s(self):
        n = 10000
        t = {}
        prev = None
        for i in range(n):
            name = "n%d" % i
            t[name] = Node(name, 1, [prev] if prev else [])
            prev = name
        s = {"points": 10 ** 9, "spent": 0, "ranks": {}}
        start = time.perf_counter()
        ops = 0
        while ops < 100000:
            for i in range(n):
                unlock(s, t, "n%d" % i)
            respec(s, t)
            ops += n + 1
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0, "100k ops took %.3fs" % elapsed)
        self.assertEqual(s["spent"], 0)
        self.assertEqual(s["ranks"], {})


if __name__ == "__main__":
    unittest.main()
