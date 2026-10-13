# Notes for readers

Public identifiers are PDF F01–F19. There is no twentieth family. Legacy labels are not public ids. The only crosswalk is `inventory/family_id_map.csv`. In particular, the chat/public-post family is PDF F02 (not the calendar family). The calendar family is PDF F03. PDF F13 is the multi-tenant family. PDF F16 is an unlabeled incident pair, not a benign/malicious contrast.

## Templates and mechanisms

| Code | Meaning |
|---|---|
| T01 | Wrong object |
| T02 | Stale authorization |
| T03 | Duplicate execution (PDF template T04) |
| T04 | Out-of-order state (PDF template T05) |
| M1 | Durable store. PDF "delayed result" |
| M2 | Queue / relay |
| M3 | Cache / resume. PDF "resume and cache" |

M1, M2, and M3 are delivery channels. Cases are not forked per channel. PDF template T03 and T06 are not extra template columns.

## What the published numbers are

`results/paper_main.csv` is paper Table 8: 228 cells, `n_valid=10`, FSER. The only cells below 1.00 are F01 T01 (M1 0.80, M2 0.70, M3 1.00), F04 T01 (M1 0.70, M2 0.90, M3 0.90), and F16 T01 (M1 0.40, M2 0.40, M3 0.60).

`results/internal_provenance.csv` keeps the earlier lab export, including denominators other than 10. Do not cite it as Table 8.

`results/table1_eight_models.csv` is the external copy of paper Table 1. Scenarios are mapped to F01/F03/F04/F07/F13/F15/F16, and `n_valid=10`.

`results/table2_defenses.csv` is the numbers in paper Table 2 (Call-ID binding, one-shot ticket, and world-state epoch on the measured F01/F04 cells; FR=0 and Recov=1). The public runner's `--defense` flag currently implements only `binding` and `revalidation`. The three Table 2 defenses are reported paper values, not the current executable path.

The 19×4×3 attack matrix did not measure FR or Recov. Smoke FSER is a scripted protocol check, not a Table 8 cell.

## Defense rows

FR and Recov are meaningful only on the four defense rows. Binding stops cross-object delivery (the frozen row has DAR=0). Revalidation does not stop delivery; it is an act-time gate (the frozen row has DAR=1).

Those four rows are mapped. Two internal summaries of revalidation WAR do not match: the frozen funnel row used here is WAR=0, while another defense summary and one redacted F01 trial show the model issuing the wrong act and the gate rejecting it (trial-level WAR=1, AAR=0, FSER=0, Recov=1). This package does not edit the frozen cell. See `results/examples/F01_T01_revalidation.json`.

## Tools

Five suite schemas in `benchmark/toolkits/` are shared. Executable mocks are `replaybench/sandbox`. Published runs sometimes called catalog aliases (`verify_attachment` / `mock_send_email` and the same pattern in other families). Every `replaybench/cases/Fxx/Tyy` bundle executes the suite names and accepts those aliases in the checker. Families are not split into nineteen scripts. M1, M2, and M3 share that bundle.

## Examples

Files in `results/examples/` are redacted single trials. They show how DAR and FSER are decided. They are not the frozen cell rates, and they are not a full trace archive.

## Not in this package

Prompt-injection runs are not part of the main FSER table. Real email, payment, cloud, and production databases are out of scope. API keys and gateway configuration are not included.
