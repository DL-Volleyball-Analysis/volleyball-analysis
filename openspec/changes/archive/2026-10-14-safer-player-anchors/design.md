# Design

- `anchor_for` sorts candidates by horizontal distance to the ray's footprint between touch heights (unchanged) and
  returns the nearest only if it is within the radius and the second-nearest is at least `margin` farther.
- Default 1.0 m: in the stress test (20 seeds) it is never worse than the unanchored fit for 0.3-1.0 m of position
  error and a slightly wrong camera, while 0.5 m keeps about 20% on the attack up to 0.6 m and is worse at 1.0 m. A
  wrong anchor costs much more (meters) than a right one gains (decimetres), and the real position error per touch is
  unknown, so the safe value is the default.
- The unambiguous case (one candidate) is unaffected, so the ablation's 0.31 m stays.
