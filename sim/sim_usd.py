"""Museum game economy v1 (dollars): a headless, seeded sim of one curator over many days.

All numbers are placeholders in dollars. Run: python sim_usd.py [days] [seeds]
Rent is per day here; monthly = rent x 30.
"""

import math
import random
import statistics
import sys
from dataclasses import dataclass

START_CASH = 500
TIERS = [
    # base = visitors/day, ticket = dollars, halls = max halls,
    # rent = dollars/day (x30 = monthly), cost = dollars to move in,
    # upkeep = dollars/day per hall, hall_cost = dollars per hall, stars = min stars,
    # guide_wage = dollars/day per guide
    dict(name="Farmers market", base=35, ticket=0, halls=1, rent=25, cost=0, upkeep=0, hall_cost=0, stars=0.0, guide_wage=0),
    dict(name="Small town rooms", base=80, ticket=5, halls=3, rent=40, cost=1000, upkeep=10, hall_cost=600, stars=0.0, guide_wage=60),
    dict(name="Small town museum", base=180, ticket=8, halls=6, rent=80, cost=12000, upkeep=25, hall_cost=1500, stars=3.0, guide_wage=60),
    dict(name="City, small museum", base=400, ticket=12, halls=10, rent=200, cost=40000, upkeep=50, hall_cost=4000, stars=3.2, guide_wage=90),
    dict(name="City, big museum", base=900, ticket=15, halls=20, rent=450, cost=120000, upkeep=100, hall_cost=12000, stars=3.4, guide_wage=90),
    dict(name="Big city, small museum", base=1200, ticket=18, halls=12, rent=900, cost=300000, upkeep=200, hall_cost=25000, stars=3.6, guide_wage=120),
    dict(name="Big city, big museum", base=2500, ticket=22, halls=30, rent=1800, cost=800000, upkeep=300, hall_cost=60000, stars=3.8, guide_wage=120),
]
APPEAL = {"C": 3, "N": 8, "R": 25, "L": 100}
EXPEDITIONS = [
    # name, min tier index, cost (dollars), days away, odds (percent)
    ("Local dig", 0, 150, 3, {"C": 85, "N": 15}),
    ("Regional expedition", 2, 1000, 6, {"C": 55, "N": 35, "R": 10}),
    ("Far expedition", 4, 8000, 12, {"C": 30, "N": 45, "R": 24, "L": 1}),
]
WAGE = dict(guide=60, guard=70, researcher=150, intern=40)  # dollars per day
GUIDE_CAP = 30  # visitors a guide covers per open hour
HALL_CAP = 80  # visitors a hall holds per day at 10 hours
STALL_CAP = 60
TALKS = 6  # conversations the curator has time for per day
GROUPS = [1, 2, 2, 2, 3, 4, 6]  # visitor group sizes met in conversation
OLD_SITE_SHARE = 0.6  # share of a left-behind site's net that a manager keeps earning
GIFT_SPEND = 3.0  # average gift shop spend per visitor, dollars, tier 1 and up


@dataclass
class Policy:
    name: str
    staff_ratio: float  # guides hired vs. guides needed
    sec_ratio: float
    clarity: float  # signage quality 0..1 (sign cost paid per hall)
    pitch_min_group: int  # only pitch to groups at least this big
    pitch_cap: int  # max pitches a day
    flyers: int  # flyers posted a day at tiers 1-2
    campaign: bool  # paid campaigns at tier 4+
    expand_mult: float  # expand when cash >= cost * this
    reserve_days: int  # cash kept back, in days of costs
    shop_match: float


POLICIES = [
    Policy("rusher", 0.6, 0.4, 0.6, 2, 3, 0, False, 1.0, 1, 0.6),
    Policy("pitcher", 1.0, 1.0, 0.9, 1, 6, 2, True, 1.1, 3, 0.9),
    Policy("balanced", 1.0, 1.0, 0.9, 4, 2, 2, True, 1.1, 3, 0.9),
    Policy("cautious", 1.25, 1.2, 1.0, 6, 1, 1, True, 1.5, 6, 0.9),
]


def run(pol, seed, days):
    rng = random.Random(seed)
    tier, halls, cash, stars, trust = 0, 1, START_CASH, 2.5, 50.0
    appeal = 14  # opening dig: two common finds and one notable
    old_income = 0.0
    last_vis, best_vis = 30, 0
    ad_days, exp_days, exp_pending = 0, 0, None
    reached = {0: 0}
    short_days, thefts, recent_net = 0, 0, []
    for d in range(1, days + 1):
        t = TIERS[tier]
        hours = 10
        # staffing decided on yesterday's crowd
        need_g = max(1, math.ceil(last_vis / (hours * GUIDE_CAP)))
        guides = max(1, round(need_g * pol.staff_ratio)) if tier > 0 else (1 if pol.staff_ratio >= 1 else 0)
        need_s = max(1, math.ceil(halls / 3))
        guards = round(need_s * pol.sec_ratio) if tier > 0 else 0
        researchers = 1 if tier >= 3 else 0
        # marketing
        mkt = 1.0
        cost_mkt = 0
        if tier <= 1 and ad_days == 0 and cash > 100:
            ad_days, cost_mkt = 3, 25
        if ad_days > 0:
            mkt += 0.3
            ad_days -= 1
        if tier <= 2 and pol.flyers:
            mkt += 0.05 * pol.flyers
            cost_mkt += 5 * pol.flyers
        if pol.campaign and tier >= 3:
            mkt += 0.2
            cost_mkt += 40 * tier
        appeal_ratio = min(1.0, appeal / (halls * 10))
        demand = (t["base"] * (hours / 10) * (0.4 + 0.6 * appeal_ratio) * (0.5 + 0.15 * stars)
                  * (0.8 + 0.4 * trust / 100) * mkt * rng.uniform(0.85, 1.15))
        cap = STALL_CAP if tier == 0 else halls * HALL_CAP
        vis = int(min(demand, cap))
        crowded = demand > cap * 1.1
        best_vis = max(best_vis, vis)
        cover = min(1.0, guides * GUIDE_CAP * hours / max(1, vis)) if guides else 0.3
        sec_cover = 1.0 if tier == 0 else min(1.0, guards / need_s)
        if appeal > 3 and rng.random() < 0.08 * (1 - sec_cover):
            appeal -= 3
            thefts += 1
            stars -= 0.1
        sat = 0.3 + 0.35 * cover + 0.2 * pol.clarity + 0.15 * appeal_ratio - (0.05 if crowded else 0)
        stars = min(5.0, max(1.0, stars + (5 * sat - stars) * 0.15))
        # conversations: save trust for big groups
        pitches, conv_rev = 0, 0
        for _ in range(TALKS):
            g = rng.choice(GROUPS)
            if g >= pol.pitch_min_group and pitches < pol.pitch_cap:
                pitches += 1
                if rng.random() < trust / 100:
                    conv_rev += g * (5 + 4 * tier)
        trust = min(100.0, max(0.0, trust + 2 * (TALKS - pitches) - 4 * pitches))
        # revenue
        rev = vis * t["ticket"]
        if tier >= 1:
            rev += vis * GIFT_SPEND * pol.shop_match
        rev += vis * (2.0 * (0.4 + 0.6 * appeal_ratio) if tier == 0 else 0.0)
        rev += conv_rev + old_income
        # costs
        wage = (guides * t["guide_wage"] + guards * WAGE["guard"]
                + researchers * WAGE["researcher"])
        costs = t["rent"] + t["upkeep"] * halls + wage + cost_mkt
        # expeditions
        if exp_days > 0:
            exp_days -= 1
            if exp_days == 0 and exp_pending:
                odds = exp_pending
                roll, acc = rng.randrange(100), 0
                for k, p in odds.items():
                    acc += p
                    if roll < acc:
                        appeal += APPEAL[k]
                        break
                exp_pending = None
        else:
            best = [e for e in EXPEDITIONS if e[1] <= tier]
            e = best[-1]
            if cash > 3 * e[2]:
                costs += e[2] / e[3]  # fee spread over the trip
                exp_days, exp_pending = e[3], e[4]
        net = rev - costs
        cash += net
        recent_net = (recent_net + [net])[-5:]
        if cash < 0:
            short_days += 1
            if appeal > 3:  # sell a common find at the dealer's price
                appeal -= 3
                cash += 3 * 20 * 0.6
        reserve = pol.reserve_days * costs
        # build halls
        if tier > 0 and halls < t["halls"] and cash > t["hall_cost"] + 20 * pol.clarity + reserve:
            cash -= t["hall_cost"] + 20 * pol.clarity
            halls += 1
        # expand
        if tier < len(TIERS) - 1:
            nt = TIERS[tier + 1]
            gate = best_vis >= 40 if tier == 0 else True
            if gate and cash >= nt["cost"] * pol.expand_mult + reserve and stars >= nt["stars"]:
                cash -= nt["cost"]
                old_income += max(0.0, OLD_SITE_SHARE * statistics.mean(recent_net))
                tier += 1
                halls = 1
                reached[tier] = d
        last_vis = vis
    return dict(reached=reached, cash=cash, stars=stars, short=short_days, thefts=thefts,
                trust=trust, tier=tier)


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    for pol in POLICIES:
        res = [run(pol, s, days) for s in range(seeds)]
        print(f"\n== {pol.name} ({seeds} runs, {days} days)")
        for k in range(1, len(TIERS)):
            ds = [r["reached"][k] for r in res if k in r["reached"]]
            if ds:
                print(f"  tier {k + 1} {TIERS[k]['name']:<24} median day {statistics.median(ds):>5.0f}"
                      f"  reached {100 * len(ds) // seeds:>3}%")
            else:
                print(f"  tier {k + 1} {TIERS[k]['name']:<24} never")
        print(f"  end stars {statistics.median(r['stars'] for r in res):.2f}"
              f"  trust {statistics.median(r['trust'] for r in res):.0f}"
              f"  cash-short days {statistics.mean(r['short'] for r in res):.1f}"
              f"  thefts {statistics.mean(r['thefts'] for r in res):.1f}"
              f"  end cash ${statistics.median(r['cash'] for r in res):,.0f}")


if __name__ == "__main__":
    main()
