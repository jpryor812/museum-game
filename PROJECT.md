# Museum game

Working title. A museum-management game that starts at a farmers market booth and grows to a big city museum.

## Where the design lives

The design docs are in Claude Docs, not in this repo:

- Design doc: https://claude.ai/artifact/Pw7yTyt7ySnhVNgh53nGyK
- Content and style sheet (artifacts, halls, visitors, conversations, staff, report copy, events, narration, UI strings, fact-check log): https://claude.ai/artifact/QkXSaDXWc29R79L8dkQr4B

## Status

- Economy: first-pass sim in `sim/`. All numbers are placeholders.
- Content: first-build drafts. Real artifact facts are partly checked; each card still needs a source before it ships.
- Prototype: not started. Open decisions are listed at the end of the design doc.

## Economy sim

- `sim/sim_usd.py` is the current version, in dollars. Move-in for the three-room museum is $1,000, and rent is $1,200 a month.
- `sim/sim_v0_coin.py` is the earlier coin version, kept for comparison.

Run with Python 3:

    python3 sim/sim_usd.py 150 200

The output shows the median day each tier is reached for four play styles.
