#!/usr/bin/env python3
"""Deterministic return calculator for the returns-modeler agent.

Usage: python3 -I scripts/returns.py <inputs.json>

Prints a Markdown block (scenario table, sensitivity grid, breakeven) that the agent
pastes into 04-returns.md. The agent chooses the inputs; this script only does the maths,
so no MOIC or IRR in the memo is ever computed by a language model.

Input JSON (amounts in millions of one currency):
{
  "currency": "EUR",
  "ticket": 5.0,                      # our cheque
  "entry_post_money": 80.0,           # post-money (or blended effective post) we buy at
  "dilution_to_exit": 0.15,           # total future dilution, 0.15 = 15%
  "net_debt_at_exit": 0.0,            # subtracted from EV to get equity value (negative = net cash)
  "liquidation_preference": {         # optional; omit for common / no preference
    "multiple": 1.0,
    "participating": false,
    "pari_passu_stack": 45.0,         # total preference ranking with ours, INCLUDING our ticket
    "senior_ahead": 0.0               # preference ranking ahead of ours
  },
  "carry": 0.10,                      # carry on profit (SPV / co-invest), 0 if none
  "annual_fee": 0.0,                  # management fee as fraction of ticket per year
  "entry_revenue": {"FY25A": 8.0, "FY26E": 14.0},   # optional, for implied entry multiples
  "scenarios": [
    {"name": "Bear", "exit_revenue": 25.0, "ev_revenue_multiple": 3.0, "years": 5},
    {"name": "Base", "exit_revenue": 45.0, "ev_revenue_multiple": 5.0, "years": 5},
    {"name": "Bull", "exit_revenue": 70.0, "ev_revenue_multiple": 7.0, "years": 4}
  ]
}
Simplifications (stated in the output): single entry and single exit cash flow; the
non-participating preference is taken as max(as converted, preference payout) without
modelling other holders' conversion choices.
"""
import json
import sys


def proceeds(inp, equity):
    own_exit = inp['ticket'] / inp['entry_post_money'] * (1 - inp.get('dilution_to_exit', 0))
    as_converted = own_exit * max(equity, 0)
    lp = inp.get('liquidation_preference')
    if not lp:
        return as_converted, 'as converted'
    pref = inp['ticket'] * lp.get('multiple', 1.0)
    stack = max(lp.get('pari_passu_stack', pref), pref)
    available = max(equity - lp.get('senior_ahead', 0.0), 0)
    pref_payout = min(pref, available * pref / stack)
    if lp.get('participating'):
        return pref_payout + own_exit * max(equity - lp.get('senior_ahead', 0.0) - min(stack, available), 0), 'participating'
    if pref_payout > as_converted:
        return pref_payout, 'preference'
    return as_converted, 'as converted'


def net(inp, gross, years):
    fees = inp['ticket'] * inp.get('annual_fee', 0.0) * years
    carry = max(gross - inp['ticket'] - fees, 0) * inp.get('carry', 0.0)
    return gross - fees - carry


def irr(moic, years):
    if moic <= 0:
        return -1.0
    return moic ** (1 / years) - 1


def pct(x):
    return f'{x * 100:.1f}%'


def main(path):
    inp = json.load(open(path))
    cur, t = inp.get('currency', ''), inp['ticket']
    nd = inp.get('net_debt_at_exit', 0.0)
    own_entry = t / inp['entry_post_money']
    own_exit = own_entry * (1 - inp.get('dilution_to_exit', 0))
    has_net = inp.get('carry', 0) or inp.get('annual_fee', 0)

    print(f'Ticket {cur} {t:g}M at {cur} {inp["entry_post_money"]:g}M post money: '
          f'{pct(own_entry)} at entry, {pct(own_exit)} at exit after {pct(inp.get("dilution_to_exit", 0))} dilution.')
    for k, rev in (inp.get('entry_revenue') or {}).items():
        print(f'Implied entry multiple: {inp["entry_post_money"] / rev:.1f}x {k} revenue')
    print()
    head = '| Scenario | Exit revenue | EV/Rev | Exit EV | Our proceeds | Paid via | Gross MOIC | Gross IRR |'
    sep = '|---|---|---|---|---|---|---|---|'
    if has_net:
        head += ' Net MOIC | Net IRR |'
        sep += '---|---|'
    print(head)
    print(sep)
    base = None
    for s in inp['scenarios']:
        ev = s['exit_revenue'] * s['ev_revenue_multiple']
        g, via = proceeds(inp, ev - nd)
        m = g / t
        row = (f'| {s["name"]} | {s["exit_revenue"]:g} | {s["ev_revenue_multiple"]:g}x | {ev:.1f} | {g:.2f} | {via} | '
               f'{m:.2f}x | {pct(irr(m, s["years"]))} |')
        if has_net:
            n = net(inp, g, s['years']) / t
            row += f' {n:.2f}x | {pct(irr(n, s["years"]))} |'
        print(row)
        if s['name'].lower().startswith('base'):
            base = s
    base = base or inp['scenarios'][len(inp['scenarios']) // 2]

    print(f'\nSensitivity: gross MOIC, {base["name"]} case ({base["years"]} years), exit revenue vs EV/Rev multiple')
    mults = [round(base['ev_revenue_multiple'] * f, 1) for f in (0.6, 0.8, 1.0, 1.2, 1.4)]
    print('| Revenue \\ Multiple | ' + ' | '.join(f'{m:g}x' for m in mults) + ' |')
    print('|---|' + '---|' * len(mults))
    for f in (0.6, 0.8, 1.0, 1.2):
        rev = base['exit_revenue'] * f
        cells = [f'{proceeds(inp, rev * m - nd)[0] / t:.2f}x' for m in mults]
        print(f'| {rev:.1f} ({int(f * 100)}% of base) | ' + ' | '.join(cells) + ' |')

    # Exit equity value at which the as converted stake returns 1.0x
    be_equity = t / own_exit
    print(f'\nBreakeven (1.0x gross, as converted): exit equity value {cur} {be_equity:.1f}M, '
          f'i.e. {be_equity / base["exit_revenue"]:.1f}x {base["name"]} exit revenue.')
    print('\nAssumptions: single entry and exit cash flow; IRR = MOIC^(1/years) minus 1; '
          'non participating preference taken as max(as converted, preference payout).')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
