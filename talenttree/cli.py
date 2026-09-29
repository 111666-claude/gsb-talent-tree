"""命令行入口：跑天赋树样例。"""

import argparse

from .tree import Node, TalentError, cycles, respec, unlock


def sample_tree():
    return {
        "a": Node("a", 3, []),
        "b": Node("b", 4, []),
        "c": Node("c", 2, ["a"]),
    }


def build_parser():
    parser = argparse.ArgumentParser(prog="talent-tree", description="天赋树")
    parser.add_argument("--sample", default="budget", help="budget / respec / cycle")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    tree = sample_tree()
    state = {"points": 5, "spent": 0, "ranks": {}}
    if args.sample == "budget":
        unlock(state, tree, "a")
        try:
            unlock(state, tree, "b")
        except TalentError:
            pass  # 点数不足，按口径拒绝点亮
        print("points=%d spent=%d" % (state["points"], state["spent"]))
    elif args.sample == "respec":
        unlock(state, tree, "a")
        unlock(state, tree, "c")  # c 需要 a，a 已点，允许
        print("refunded=%d" % respec(state, tree))
    elif args.sample == "cycle":
        looped = {"x": Node("x", 1, ["y"]), "y": Node("y", 1, ["x"])}
        print("cycles=%d" % len(cycles(looped)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
