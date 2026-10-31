# Rerun log (2026-10-31T20:53:40.958732+00:00)

Rule (applied identically to every arm): a gene whose board holds an artifact with `api error` (all were HTTP 429 rate limits from running four arms at once) is deleted and rerun from scratch, one arm at a time with 3 workers. No gene is rerun for any other reason.

- A1_s1: 4 genes rerun: Gene_37 (was +0.200), Gene_38 (was -1.100), Gene_39 (was +1.975), Gene_40 (was +1.500)
- A1_s2: 0 genes rerun: 
- A3_s1: 6 genes rerun: Gene_16 (was +2.050), Gene_17 (was +2.500), Gene_18 (was +3.000), Gene_19 (was +1.400), Gene_20 (was +2.575), Gene_21 (was -1.100)
- A3_s2: 6 genes rerun: Gene_13 (was +2.200), Gene_19 (was +1.350), Gene_22 (was +2.600), Gene_23 (was +3.500), Gene_24 (was -0.700), Gene_25 (was +0.000)
