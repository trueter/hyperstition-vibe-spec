# Vibe Crowd Intensity — Spec

> This repository documents **two reference vibe engines** that measure the same
> phenomenon (a crowd's collective energy) from different signals and runtimes:
>
> 1. **Crowd-Intensity engine** — Python, person-tracking boxes → energy / bounce /
>    density / synchrony / vibe. Documented in [Part I](#part-i--crowd-intensity-engine-person-tracking) below.
> 2. **VIBEMAP engine** — in-browser, motion frame-differencing, per-section, gesture
>    bonuses, and multi-venue max-sync. Documented in
>    [Part II](#part-ii--vibemap-engine-browser-motion-driven).
>
> A field-by-field [correspondence table](#correspondence-between-the-two-engines)
> maps the two vocabularies so a single downstream UI can consume either one.
>
> **See also:** [`FIELD_REPORT.md`](FIELD_REPORT.md)
> ([PDF](FIELD_REPORT.pdf)) measures Part II against 49 hours of exhibition
> telemetry and lists six proposed amendments to the constants documented here.

---

# Part I — Crowd-Intensity engine (person-tracking)

Source of truth: `apps/tracker/src/vibe.py` (`VibeEngine.update`, lines ~220-305).
Delivered to the web tracker page via `apps/tracker/src/tracks_bridge.py` →
`apps/web/components/TrackerLab.tsx` / `apps/web/lib/tracks/types.ts`.

## Overview

The tracker page's "vibe crowd intensity" widget derives five metrics from
person-tracking boxes: **energy**, **bounce**, **density**, **synchrony**, and
a blended **vibe** composite.

Common pipeline per channel:

1. Compute raw value.
2. Normalize against a rolling peak: `x / max(p95 over last 300s, floor)`, clipped to 1.
3. EMA smooth (`channel_tau_s = 1.5s`).
4. Weighted-sum into composite.
5. EMA smooth again (`fast_tau_s = 0.5s`) → `vibe`.

## Metrics

### Energy (`vibe.py:216, 271, 286`)

Per track: windowed displacement speed in body-heights/sec:

```
speed = hypot(dx, dy) / span / h
```

Computed over a `speed_window_s = 0.5s` window (not instantaneous vx/vy —
those are jitter-dominated per the noise-model notes at `vibe.py:25-35`).
Clipped to `MAX_SPEED_BH = 6.0`.

`energy_raw = mean(speeds)` across tracks. Normalized against `energy_floor = 0.5` bh/s.

### Bounce (`vibe.py:254-261, 273`)

Per track, over a `window_s = 2.0s` position history:

1. Linearly detrend `cy` (`resid = cy - polyfit(t, cy, 1)`) to remove camera-approach drift.
2. `track_bounce = std(resid) / mean_h`, capped at 0.5.

`bounce_raw = median(track_bounces)` across tracks — median so one flickering
box can't dominate. Requires ≥8 samples spanning ≥75% of the window.
Normalized against `bounce_floor = 0.08` bh.

### Density (`vibe.py:274`)

`density_raw = len(tracks)` — raw track count. Normalized against
`density_floor = 8.0` people via the same peak-relative p95 scheme.

### Synchrony (`vibe.py:275-280`)

Circular mean of unit displacement vectors for "moving" tracks
(speed > `move_gate = 0.2` bh/s):

```
mx = mean(ux); my = mean(uy)
synchrony_raw = hypot(mx, my)
```

1 = all aligned, 0 = vectors cancel out. Requires `min_movers = 4`, else
forced to 0 — below that the circular mean is noisy (measured 0.33/frame
jumps). Already 0..1, no normalization needed.

### Vibe composite (`vibe.py:294-299`)

```
composite = (0.40*energy + 0.25*bounce + 0.20*density + 0.15*synchrony) / sum(weights)
vibe = EMA(composite, tau=0.5s)
rising = clip(vibe - EMA(composite, tau=30s), -1, 1)   # heating-up indicator
```

## Extras

- **tempo_bpm / tempo_conf**: FFT (Hann-windowed, resampled to 20Hz) over the
  crowd's mean vertical velocity, searching the 0.8–4Hz band (48–240 BPM).
  Confidence = (peak bin + 2 neighbors) / total band power, gated at
  `tempo_conf_gate = 0.40`.
- **arms_up**: reserved for phase-2 pose keypoints, always 0 for now.

## Calibration provenance

All thresholds (floors, gates, taus, weights) were tuned empirically against
a "long-queue capture" (2026-07-20, ~3100 frames / 28 tracks) documented in
the module docstring at `vibe.py:25-45`.

---

# Part II — VIBEMAP engine (browser, motion-driven)

Source of truth: `index.html` in the VIBEMAP surveillance-unit app
(`updateVibe`, `updateThirdVibe`, `currentActivity`, `addBonusVibe`).
Runs entirely client-side (no server, no pose model required); designed for
low-resolution CRT/monitor feeds where reliable per-person tracking is not
available, so **frame-to-frame motion** — not tracked boxes — is the base signal.

## Overview

VIBEMAP derives a single `0..100` **vibe** level, plus a per-section breakdown and
a network-wide **shared** vibe. It rises fast on movement and decays slowly when
things go still, so a room "holds" its energy for a few seconds after motion stops.

Pipeline:

1. `currentActivity()` → instantaneous `0..1` activity from the active detector.
2. Scale by the `VIBE` sensitivity slider, clip to `0..1`, `target = A * 100`.
3. Asymmetric EMA (fast attack, slow release) toward `target`.
4. Add decaying **gesture/move bonuses**, then fold in network peers.

## Base activity (`currentActivity`)

Two detector backends feed the same `0..1` scale:

- **Motion mode** (default, for monitor/CRT feeds):

  ```
  activity = blob * 1.5 + min(movers, 6) * 0.07
  ```

  where `blob` is the fraction of the monitored region covered by the largest
  moving blob (frame-differenced) and `movers` is the count of persistent motion
  blobs. Deliberately gentle: a single person crossing (~25% moving) reads ~0.4,
  so a maxed meter needs sustained, whole-frame motion.
- **AI person mode**: `activity = live_tracks * 0.18` (~5–6 concurrent people to peak),
  where `live_tracks` are COCO-SSD person tracks currently visible (`missed == 0`).

## Attack / release smoothing (`updateVibe`)

```
A      = min(1, currentActivity() * vibeSensitivity)
target = A * 100
rate   = target > vibe ? 1.6 : 0.5        # per-second, frame-rate independent
vibe  += (target - vibe) * (1 - exp(-rate * dt))
vibe   = clip(vibe, 0, 100)
```

Attack (`1.6/s`) ramps the meter up over a couple of seconds of sustained
activity; release (`0.5/s`) lets it coast down. Both are integrated with
`dt` so the curve is identical regardless of frame rate.

## Per-section vibe (`updateThirdVibe`)

The camera is split into **left / middle / right** thirds (or a section can be
bound to a specific **monitor** quad instead of a geometric third — see
"section→monitor mapping"). Each section `b` gets its own energy and meter:

```
thirdEnergy[b] = movedPixels[b] / area[b]         # or sampleMonitorEnergy(mon)
A              = min(1, thirdEnergy[b] * 2.4 * vibeSensitivity)
target         = A * 100
rate           = target > thirdVibe[b] ? 1.6 : 0.5
thirdVibe[b]  += (target - thirdVibe[b]) * (1 - exp(-rate * dt))
```

Per-section vibe drives the trio of green-screen performers (one per third) and
the per-side meters/sparklines.

## Gesture & move bonuses (`addBonusVibe`, `recordMove`)

Recognized gestures/poses add a **decaying** reward to a section's vibe
(`thirdBonus`, shed at `BONUS_DECAY = 20` pts/s, clipped `0..100`):

| Trigger | Bonus (points) |
| --- | --- |
| Two-hand **heart** shape | +45 |
| Performer **V / arms-up** pose | +22 |
| Recognized **hand shape** (open palm / fist / peace…) | `SHAPE_BONUS` |
| Hands-up **"Y"** shape | +9 |

Each discovered move also calls `recordMove(third)`, which increments that
section's `thirdMoves` counter and adds `MOVE_SCORE = 5` to its cumulative score.
`thirdScore[b]` accumulates **vibe-seconds** (`min(100, thirdVibe+thirdBonus)/100 * dt`)
plus move points — this is the per-section leaderboard ("which third is winning").

## Network / multi-venue sync (shared vibe)

Every machine broadcasts its **local** vibe ~2.5×/s (every `0.4s`) to LAN peers
(via the bus) and to a linked remote venue (a vibe-only bridge; remote ids are
prefixed `remote:`). Peers expire after 3s of silence.

```
localWithBonus = min(100, vibe + maxBonus())
sharedVibe     = netSync ? max(localWithBonus, maxPeer) : localWithBonus
```

The room/network vibe is the **strongest live signal anywhere**, so motion in any
connected room lights up every screen. `sharedVibe` is what drives global effects
(e.g. the hype burst above 0.8) and is the value plotted on the geomap per venue.

## Outputs & logging

- **Sparkline**: `vibeSeries` keeps the shared vibe at `0.4s` resolution,
  capped at `VIBE_SERIES_CAP = 240` samples (~96s).
- **Night log**: `vibeLog` samples at `1s` with `{ shared, local, peers, l, m, r }`
  (per-third = `thirdVibe + thirdBonus`), capped at `VIBE_LOG_CAP` and auto-saved.
- **Geomap**: each camera carries a place (GPS / what3words) + coverage bearing;
  `sharedVibe` and peer vibes are plotted per location.

## Calibration provenance

Constants (`1.5`/`0.07` activity weights, `2.4` section gain, `1.6`/`0.5` attack/
release, `20` pts/s bonus decay, gesture bonus values) were tuned live against
low-contrast monitor feeds of dancing crowds during exhibition use, favoring a
meter that holds energy briefly and rewards recognizable moves.

---

# Correspondence between the two engines

Both engines emit a `0..100`-scale **vibe** intended for the same downstream UI.
The table maps concepts so a consumer can treat them interchangeably.

| Concept | Part I — Crowd-Intensity (Python) | Part II — VIBEMAP (browser) |
| --- | --- | --- |
| Base signal | Per-track windowed displacement speed (body-heights/s) | Frame-differenced motion blob coverage + mover count (or person tracks in AI mode) |
| Movement magnitude | `energy` | `currentActivity()` → `vibe` base |
| Rhythm / vertical oscillation | `bounce`, `tempo_bpm` | (not modeled; implied by sustained motion) |
| Crowd size | `density` (track count) | `min(movers, 6)` term / live track count |
| Directional agreement | `synchrony` (circular mean of unit vectors) | `netSync` max across venues + per-side motion vectors |
| Composite | Weighted sum → EMA(`0.5s`) | Asymmetric EMA (attack `1.6/s`, release `0.5/s`) |
| Heating-up indicator | `rising = vibe − EMA(vibe, 30s)` | slow release tail + `thirdBonus` decay |
| Spatial breakdown | single global value | `thirdVibe[L,M,R]` (+ section→monitor mapping) |
| Pose/gesture | `arms_up` (reserved, phase-2) | live heart / V / Y / hand-shape bonuses |
| Multi-venue | n/a (single tracker) | LAN + remote peers, `sharedVibe = max(...)` |
| Normalization | rolling p95 vs floor, clipped to 1 | fixed sensitivity slider, clipped to 1 |

Both are valid ways to answer the same question — *how alive is the room right
now* — and this repo keeps them side by side as the canonical **hyperstition
vibe spec**.
