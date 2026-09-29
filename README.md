# talent-tree

天赋树：点数预算、前置依赖、重置返还与环检测，只用 Python 标准库。

```
python3 -m talenttree.cli --sample budget
python3 -m talenttree.cli --sample respec
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **点数不能透支**：剩余点数不足时拒绝点亮并返回 `TalentError`。
  `--sample budget`（5 点，点 a(3) 再点 b(4)）按口径是 `points=2 spent=3`（第二次被拒），
  现在给 `points=-2 spent=7`。
- **前置必须先点**：`requires` 里的节点至少 1 级才能点下一个；`--sample respec` 里点 c（依赖 a）时
  a 已点，所以按口径是允许的，但重置要按各节点实际花费返还。
- **重置返还实际花费**：a(3)+c(2) 应返还 5。现在按「节点个数」返还 2。
- **环检测**：`cycles(tree)` 要返回所有互相依赖的节点名（排序），`--sample cycle` 按口径是 `cycles=1`，
  现在恒为 0。
- 不变量：点数 = 初始点数 − 已花费；`ranks[name] <= max_rank`；同一操作序列重复执行结果相同。
- 规模：1 万个节点、10 万次操作 1 秒内完成，内存 O(节点数)；不许每次操作都重扫整棵树。

## 现在的行为

- `unlock` 不查 `requires`、也不检查剩余点数：点数会变成负数。
- `respec` 按节点个数返还点数，与各节点的 cost 无关。
- `cycles` 直接返回空列表。

## 输出

```
points=2 spent=3
refunded=5
cycles=1
```

## 目录

```
talenttree/tree.py   点数、前置与重置
talenttree/cli.py    命令行入口
tests/               unittest 用例
```
