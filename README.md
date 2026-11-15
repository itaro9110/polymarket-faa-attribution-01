[![make.fun · polymarket-faa-attribution-01](https://make.fun/badge/polymarket-faa-attribution-01.svg)](https://make.fun/bounty/polymarket-faa-attribution-01?utm_source=github&utm_medium=readme&utm_campaign=polymarket-faa-attribution-01)
[![rank](https://make.fun/badge/polymarket-faa-attribution-01/itaro9110/polymarket-faa-attribution-01/rank.svg)](https://make.fun/bounty/polymarket-faa-attribution-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=polymarket-faa-attribution-01)
[![reward](https://make.fun/badge/polymarket-faa-attribution-01/itaro9110/polymarket-faa-attribution-01/reward.svg)](https://make.fun/bounty/polymarket-faa-attribution-01?utm_source=github&utm_medium=readme&utm_campaign=polymarket-faa-attribution-01)

# Polymarket FAA attribution forecast

Entry for make.fun `polymarket-faa-attribution-01`: forecast the Yes price
of every market of Polymarket's FAA outage attribution family at every
minute of the 4 hours after a checkpoint, as five quantiles
(5%, 25%, 50%, 75%, 95%).

## Method

Persistence median with a level-dependent, jump-aware spread. For a market
whose last price is `x`, at minute `h` after the checkpoint:

```
q_tau(h) = clamp(x + z_tau * S(x) * h^0.45 * mult_tau(x), 0, 1)
S(x)     = 0.0009 * (1 + 4x), doubled when a 1-minute move larger than
           0.03 happened in the last 120 minutes (jump regime)
mult     = 1 + 6x for the two lower quantiles, 1.0 otherwise
median   = x (no drift)
```

The four markets of one attribution family are mutually exclusive, so
their Yes prices should sum to about 1: the medians are renormalised to
sum to 1 whenever the checkpoint sum lies in [0.5, 1.5].

Calibrated on the practice instance (the NVIDIA "Next CEO" event, six
cases p00–p05). Local practice score on p00–p04 (scored against the next
case's prices): **0.306120** mean pinball loss, vs **0.392518** for the
house persistence baseline — better on every case (p00 0.3871, p01 0.3101,
p02 0.3693, p03 0.2913, p04 0.2030). The same ranking holds on five
fresh rolling origins inside p05 (0.3510 vs baseline 0.4458).

What was tested and rejected: median drift toward a trailing median,
per-market activity scaling, and raw empirical quantiles all scored worse
than the base model on practice and are not used.

## Run

```
python3 main.py            # reads $MAKEFUN_INPUT_DIR (else /input),
                            # writes $MAKEFUN_OUTPUT_DIR (else /output)
```

Standard library only, no network, deterministic (two runs on the same
case are byte-identical). Runs in ~40 ms per case on one CPU, far inside
the 8 s cap.

## License

MIT — see LICENSE.
