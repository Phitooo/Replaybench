<p align="center"><a href="./README.md">English</a> | <a href="./README.zh-CN.md"><strong>简体中文</strong></a></p>

# ReplayBench

**通过受控工具结果重放评估 LLM Agent 中的工具结果上下文错绑**

ReplayBench 是一个用于评估 **工具结果错绑（tool-result misbinding）** 的基准测试。真实且未经修改的工具结果在原始执行上下文中可能完全正确，但在其他任务、授权状态、执行阶段或因果顺序下被再次使用时，可能诱导 Agent 生成错误动作，进而产生错误的持久化状态。

**重放（replay）是评估手段，错绑（misbinding）才是研究对象。** T01 跨任务重放仅是四种失败模板之一。与提示注入不同，重放的工具结果不需要加入新的恶意指令。

本仓库公开本地沙箱案例、重放交付机制、基于 LlamaIndex 的运行器、独立检查器、示例轨迹，以及论文 **TRAP: Tool-Result Replay Attack for Probing Misbinding in LLM Agents** 对应的结果数据。运行不需要真实的邮箱、支付、银行、云服务或生产数据库。

## 基准覆盖范围

| 维度 | 数量 |
| --- | --- |
| 应用场景 | 19（`F01`–`F19`） |
| 失败模板 | 4（`T01`–`T04`） |
| 重放机制 | 3（`M1`–`M3`） |
| 场景 × 模板案例 | 76 |
| 场景 × 模板 × 机制配置 | 228 |
| 论文主要 T01 实验 | 8 个 LLM × 3 个框架 × 7 个场景 |

### 四种失败模板

| 模板 | 违反的性质 | 具体含义 |
| --- | --- | --- |
| T01 跨任务错误对象 | 归属正确性 | 将任务 A／对象 A 的真实结果用于另一任务／对象。 |
| T02 陈旧上下文 | 上下文有效性 | 授权、资源状态等条件变化后，重复使用旧结果。 |
| T03 重复执行 | 单次执行约束 | 已提交的状态修改因重放而再次执行。 |
| T04 乱序执行 | 因果顺序 | 结果的消费顺序违反工作流状态转移的先后关系。 |

T02–T04 可能发生在同一对象或同一任务的不同状态、阶段中，因此不能将整个 ReplayBench 简化为跨任务或跨对象攻击。

### 三种受控重放机制

| 机制 | 交付路径 |
| --- | --- |
| M1 Durable Recovery | 从持久化存储中恢复并交付旧结果。 |
| M2 Queue Redelivery | 通过队列与工作线程重新交付旧结果。 |
| M3 Cache Resume | 恢复缓存或检查点中的旧结果。 |

机制决定真实结果**如何再次交付**，模板决定违反了**哪一种上下文有效性要求**。它们是受控实验路径，并非声称特定 Agent 框架存在已证实的漏洞。

## 快速开始

需要 Python 3.10 或更高版本。

```bash
git clone https://github.com/Phitooo/Replaybench.git
cd Replaybench
python -m pip install -e ".[dev]"
replaybench smoke --family F01 --template T01 --mech M1
python -m pytest tests/test_smoke.py
```

`smoke` 不调用大模型，仅检查本地运行和评分协议。它输出的 FSER **不是论文实验结果的复现值**。

无需 API Key，也可以为现有轨迹评分：

```bash
replaybench score --trace results/examples/F01_T01_M1_success.json
```

### 运行一个真实模型配置

当前公开的模型运行器支持 **LlamaIndex**，模型与 API 接口由使用者配置。

```bash
python -m pip install -e ".[llamaindex]"
export OPENAI_API_KEY="YOUR_API_KEY"
export REPLAYBENCH_MODEL="YOUR_MODEL_ID"
# 可选：兼容 OpenAI API 的自定义端点
# export OPENAI_BASE_URL="https://your-endpoint.example/v1"
replaybench run --family F01 --template T01 --mech M1 --n 1
```

不要把密钥提交到 GitHub。供应商拦截、模型空响应、缺少密钥和基础设施错误都不能当作成功防御或 FSER = 0。

## 评估指标

| 指标 | 定义 |
| --- | --- |
| DAR（交付率） | 真实重放结果到达目标执行上下文的有效试验比例。 |
| WAR（错误动作率） | Agent 生成错误状态修改动作的有效试验比例。 |
| AAR（错误动作接受率） | 错误动作通过执行层检查并被接受的有效试验比例。 |
| **FSER（最终状态错误率）** | **由独立检查器验证持久化沙箱状态发生错误的有效试验比例，是主要指标。** |

所有比例均使用有效试验作为分母。DAR = 1、FSER = 0 表示结果已交付但未造成最终状态错误，并不表示重放没有发生。详细定义见 [METRICS.md](./docs/METRICS.md)。

## 论文结果数据

| 文件 | 内容 |
| --- | --- |
| [`results/table1_eight_models.csv`](./results/table1_eight_models.csv) | T01 主要实验，8 模型 × 3 框架 × 7 场景（论文 Table 1）。 |
| [`results/paper_main.csv`](./results/paper_main.csv) | 19 场景 × 4 模板 × 3 机制的 228 个配置（附录 G / Table 8）。 |
| [`results/examples/`](./results/examples/) | 用于查看和检查评分器的示例轨迹。 |
| [`results/table2_defenses.csv`](./results/table2_defenses.csv) | 论文防御实验的结果数据，并非防御复现代码。 |

论文报告 T01 主要实验的平均 **FSER = 0.649**，全部基准配置的平均 **FSER = 0.989**。这是论文实验的报告结果，不能保证使用不同模型和端点重新运行得到相同数值。

**公开范围说明。** 本仓库以 **ReplayBench 基准** 为核心，并非论文所有实验的完整代码发布。论文还研究了 Call-ID binding、One-shot ticket 和 World-state epoch 三种运行时防御，但**这些研究性防御实现不包含在本公开版本中**。仓库可以提供对应的论文结果表供参考，但不应将其理解为三种防御的可执行复现。论文中 LangGraph 和 OpenAI Agents SDK 的结果包含在表格中，当前仓库未提供这两个框架的模型运行器。

## 仓库结构

```text
benchmark/families/             # 应用场景规范
benchmark/toolkits/             # 共用沙箱工具
replaybench/cases/              # 场景与模板案例
replaybench/delivery/           # 持久化、队列、缓存重放路径
replaybench/sandbox/            # 本地状态与工具环境
replaybench/adapters/llamaindex.py
replaybench/checker.py          # 独立评分与最终状态检查
results/                         # 论文结果表与示例轨迹
docs/METRICS.md                  # 指标定义
tests/test_smoke.py              # 无模型测试
```

## 引用

使用 ReplayBench 时，请引用相应论文：

> Yutong Zhi, Jie Zhang, Xiuqi Lu, Jiayuan Xu, and Jing Shao. *TRAP: Tool-Result Replay Attack for Probing Misbinding in LLM Agents*. 2026.

引用元数据见 [`CITATION.cff`](./CITATION.cff)。公开 arXiv 编号确认后可进一步补充。

## 许可证

Apache-2.0，详见 [LICENSE](./LICENSE)。
