---
id: I007
kind: instrument
status: trusted
created: 2026-08-14
---

## Instrument

tools/re_cd.py measures the Vagrant libds blocking-control chain and gates the shipped DsControlB owner

## Validated by

Positive: unique _diskReset/DsControlB/CD_cw/CD_sync shapes on the SHA-verified image and exact shipped-owner match. Negatives: destroyed CD_cw ABI reports 83,950 candidates/0 matches; +4 owner edit names DsControlB mismatch. `re_cd.py` is 3/3 PASS. The separately compiled `vagrant_cd_contract_test` uses the shipping classifier and accepts all 9 declared control IDs while refusing query GetlocL, read ReadN, and an unknown ID (3/3).

## Known failure modes

(none recorded yet)
