# Some quick initial results

First full sweep of all six questions in both modes. Model: Claude Haiku 4.5.
Date: 2026-07-08. Both modes answered every question correctly, so this run is
about the cost and context tradeoff, not accuracy.

## Per-run metrics

| question | hops | mode | ok | main ctx peak | main tok | sub tok | total tok | calls (main+sub) | latency |
|----------|-----:|----------|-----|--------------:|---------:|--------:|----------:|:----------------:|--------:|
| q1 | 1 | skill    | yes | 887  | 1653 | 0    | 1653 | 2+0 | 1.9s |
| q1 | 1 | subagent | yes | 783  | 1558 | 1607 | 3165 | 2+2 | 3.4s |
| q2 | 1 | skill    | yes | 1071 | 2766 | 0    | 2766 | 3+0 | 2.5s |
| q2 | 1 | subagent | yes | 783  | 1558 | 2758 | 4316 | 2+3 | 7.2s |
| q3 | 2 | skill    | yes | 1105 | 2853 | 0    | 2853 | 3+0 | 2.8s |
| q3 | 2 | subagent | yes | 805  | 1602 | 2852 | 4454 | 2+3 | 5.0s |
| q4 | 2 | skill    | yes | 1315 | 4295 | 0    | 4295 | 4+0 | 4.2s |
| q4 | 2 | subagent | yes | 921  | 2641 | 4401 | 7042 | 3+5 | 10.9s |
| q5 | 3 | skill    | yes | 1311 | 4296 | 0    | 4296 | 4+0 | 4.3s |
| q5 | 3 | subagent | yes | 1028 | 3765 | 4834 | 8599 | 4+6 | 15.7s |
| q6 | 3 | skill    | yes | 1280 | 4133 | 0    | 4133 | 4+0 | 11.7s |
| q6 | 3 | subagent | yes | 1025 | 3732 | 4786 | 8518 | 4+6 | 12.3s |

## Per-mode summary

| mode | runs | accuracy | avg main ctx peak | avg total tok | avg latency |
|----------|-----:|---------:|------------------:|--------------:|------------:|
| skill    | 6 | 100% | 1162 | 3333 | 4.6s |
| subagent | 6 | 100% | 891  | 6016 | 9.1s |

## Reading

Subagent mode keeps the main context roughly 23% smaller on average, since the
document text stays in the subagent. It pays for that isolation with about 1.8x
the total tokens and roughly double the latency, from the extra round trips and
from re-establishing context on every lookup. The gap widens with hop count,
most visibly on q4 through q6.
