# Economy sim

Headless, seeded simulation of one curator over many days. No randomness outside the seeded generator.

- `sim_usd.py`: current, in dollars.
- `sim_v0_coin.py`: earlier version in coin, kept for comparison.

Arguments: `python3 sim_usd.py [days] [seeds]`, default 150 days and 200 seeds.

Rent is per day in the code; the monthly figure is rent x 30.
