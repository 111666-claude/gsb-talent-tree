import unittest

from talenttree.tree import Node, TalentError, cycles, respec, unlock


def tree():
    return {"a": Node("a", 3, []), "b": Node("b", 4, []), "c": Node("c", 2, ["a"])}


class UnlockTest(unittest.TestCase):
    def test_rank_increases(self):
        state = {"points": 10, "spent": 0, "ranks": {}}
        unlock(state, tree(), "a")
        self.assertEqual(state["ranks"]["a"], 1)

    def test_spent_counts_cost(self):
        state = {"points": 10, "spent": 0, "ranks": {}}
        unlock(state, tree(), "b")
        self.assertEqual(state["spent"], 4)

    def test_error_type_exists(self):
        self.assertTrue(issubclass(TalentError, ValueError))


class RespecTest(unittest.TestCase):
    def test_ranks_cleared(self):
        state = {"points": 10, "spent": 0, "ranks": {}}
        unlock(state, tree(), "a")
        respec(state, tree())
        self.assertEqual(state["ranks"], {})
        self.assertEqual(state["spent"], 0)

    def test_cycles_returns_list(self):
        self.assertEqual(cycles({}), [])


if __name__ == "__main__":
    unittest.main()
