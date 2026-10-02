# Experimentation Architecture

Pompom Creative Lab keeps three concepts separate:

1. **Creative quality** describes the video itself.
2. **Observed performance** records what platforms actually reported.
3. **Learned opportunity** ranks how useful the next test could be.

The operating loop is `video -> fingerprint -> hypothesis -> test plan -> locked prediction -> publication -> checkpoints -> audit -> challenger evaluation`. Experiments may compare direct variants or matched groups of different videos. A direct A/B test must record audience-overlap risk; the default is a matched cross-video test.

The planner reserves independent budgets for creative mechanisms and characters. Defaults are 60% exploit, 20% adjacent, 20% explore for creative mechanics and 70% established, 20% limited-data, 10% new/untested for characters. These are planning allocations, not promises of performance.

Checkpoints are 15m, 30m, 1h, 2h, 3h, 6h, 12h, 24h, 48h, and 7d. Internal distribution labels are descriptive Pompom bands, never claims about a platform's private algorithm.

