<p align="center"><a href="./README.md"><strong>English</strong></a> | <a href="./README.zh-CN.md">简体中文</a></p>

# ReplayBench

**Evaluating tool-result misbinding in LLM agents through controlled replay**

ReplayBench is a benchmark for studying **tool-result misbinding** in tool-using LLM agents. A genuine, unmodified tool result may be correct in its original execution context but become unsafe when reused for a different task, authorization state, execution stage, or causal order. ReplayBench uses **controlled replay** to investigate whether such misbinding leads agents to generate wrong actions and produce incorrect persistent states.

**Replay is the evaluation method; misbinding is the failure under study.** T01 cross-task replay is only one of four failure templates. Unlike prompt injection, the replayed tool result contains no newly injected malicious instructions.

The release provides local sandbox cases, replay delivery mechanisms, a LlamaIndex-based runner, an independent checker, example traces, and result tables accompanying the paper:

**TRAP: Tool-Result Replay Attack for Probing Misbinding in LLM Agents**  
📄 Paper: https://arxiv.org/abs/2610.16333

No real email, banking, payment, cloud, or production databases are required.

## Benchmark coverage

| Dimension | Coverage |
| --- | --- |
| Scenarios | 19 (`F01`–`F19`) |
| Failure templates | 4 (`T01`–`T04`) |
| Replay mechanisms | 3 (`M1`–`M3`) |
| Scenario–template cases | 76 |
| Scenario–template–mechanism configurations | 228 |
| Paper evaluation | 8 LLMs × 3 agent frameworks × 7 scenarios for the main T01 table |

### Four failure templates

| Template | Violated property | Description |
| --- | --- | --- |
| T01 — Cross-task wrong-object | Attribution | A genuine result from one task/object is used in another task/object context. |
| T02 — Stale-context | Contextual validity | A formerly valid result is reused after authorization, resource state, or another relevant condition changes. |
| T03 — Duplicate-effect | Single execution | Replay causes an already committed state-changing operation to execute again. |
| T04 — Out-of-order | Causal ordering | Results are consumed in an order inconsistent with the workflow's state transitions. |

T02–T04 may concern changed states or steps of the same task, even when the object identifier is unchanged.

### Three controlled replay mechanisms

| Mechanism | Delivery path |
| --- | --- |
| M1 — Durable Recovery | A persisted tool result is retrieved during recovery. |
| M2 — Queue Redelivery | A previously queued result is redelivered by a worker. |
| M3 — Cache Resume | A cached result is restored when execution resumes. |

Mechanisms determine *how* an unchanged result is delivered. Templates determine *which contextual validity requirement* is violated. These are controlled replay paths, not claims of vulnerabilities in specific frameworks.

## Quickstart

Requires Python 3.10+.

```bash
git clone https://github.com/Phitooo/Replaybench.git
cd Replaybench
python -m pip install -e ".[dev]"
replaybench smoke --family F01 --template T01 --mech M1
python -m pytest tests/test_smoke.py
```

The smoke run exercises the protocol **without making an LLM call**. Its displayed FSER is a protocol check, **not** a reproduction of a paper result.

Score an included example trace without an API key:

```bash
replaybench score --trace results/examples/F01_T01_M1_success.json
```

### Run a model-backed configuration

The public model-backed runner currently supports **LlamaIndex** with a user-configured endpoint.

```bash
python -m pip install -e ".[llamaindex]"
export OPENAI_API_KEY="YOUR_API_KEY"
export REPLAYBENCH_MODEL="YOUR_MODEL_ID"
# Optional for an OpenAI-compatible custom endpoint:
# export OPENAI_BASE_URL="https://your-endpoint.example/v1"
replaybench run --family F01 --template T01 --mech M1 --n 1
```

Keep credentials out of committed files. Missing credentials, provider blocking, empty model responses, and infrastructure failures must not be counted as successful resistance to replay.

## Evaluation metrics

| Metric | Definition |
| --- | --- |
| DAR — Delivery Rate | Fraction of valid trials in which the replayed result reaches the target execution. |
| WAR — Wrong Action Rate | Fraction of valid trials generating an incorrect state-changing action. |
| AAR — Action Acceptance Rate | Fraction of valid trials in which the incorrect action is accepted for execution. |
| **FSER — Final-State Error Rate** | **Fraction of valid trials with an independently verified incorrect persistent sandbox state (primary metric).** |

All rates use valid-trial denominators. A delivered result need not cause a wrong action: DAR = 1 with FSER = 0 does not mean the replay was blocked. See [metric definitions](./docs/METRICS.md).

## Results accompanying the paper

| File | Contents |
| --- | --- |
| [`results/table1_eight_models.csv`](./results/table1_eight_models.csv) | Main T01 evaluation: 8 models × 3 frameworks × 7 scenarios (paper Table 1). |
| [`results/paper_main.csv`](./results/paper_main.csv) | 228 configurations across 19 scenarios, 4 templates, 3 mechanisms (Appendix G / Table 8). |
| [`results/examples/`](./results/examples/) | Example traces for testing and inspecting the checker. |
| [`results/table2_defenses.csv`](./results/table2_defenses.csv) | Paper-reported defense results, provided as data only. |

The paper reports a mean **FSER of 0.649** for the main T01 evaluation and **0.989** across the full benchmark. These are reported experimental results, not guaranteed outputs of a new model run.

**Public release scope.** ReplayBench is released as a **benchmark**, not as the complete experimental codebase for every study in the paper. The paper additionally evaluates Call-ID binding, one-shot tickets, and world-state epochs; **their research implementations are not part of this public release**. The reported defense results may be included for reference, but should not be mistaken for executable reproductions of those three defenses. LangGraph and OpenAI Agents SDK paper results are included in the CSV tables, but their model-backed runners are not included here.

## Repository layout

```text
benchmark/families/             # Scenario specifications
benchmark/toolkits/             # Shared sandbox toolkits
replaybench/cases/              # Scenario–template cases
replaybench/delivery/           # Durable, queue, and cache replay paths
replaybench/sandbox/            # Local state and tool environments
replaybench/adapters/llamaindex.py
replaybench/checker.py          # Independent trace/final-state scoring
results/                         # Paper tables and example traces
docs/METRICS.md                  # Metric definitions
tests/test_smoke.py              # Model-free tests
```

## Citation

If you use ReplayBench in your research, please cite our paper:

```bibtex
@misc{zhi2026traptoolresultreplayattack,
      title={{TRAP: Tool-Result Replay Attack for Probing Misbinding in LLM Agents}},
      author={Yutong Zhi and Jie Zhang and Xiuqi Lu and Jiayuan Xu and Jing Shao},
      year={2026},
      eprint={2610.16333},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2610.16333},
}

```
## License

Apache-2.0. See [LICENSE](./LICENSE).
