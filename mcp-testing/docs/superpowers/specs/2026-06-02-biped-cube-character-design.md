# Biped Cube Character Generator — Design Spec

**Date:** 2026-06-02  
**Status:** Approved  

## Overview

A procedural SOP network inside a single Houdini Geometry node that generates a Minecraft-style bipedal character made of cubes. Proportions are driven by a single integer seed parameter, producing varied but coherent characters.

## Architecture

5 nodes inside one Geometry SOP at `/obj/biped_character`:

```
[seed_parms] ──► [build_parts] ──► [copy_to_points] ──► [OUT]
                                          ▲
                                    [unit_box]
```

| Node | Type | Role |
|------|------|------|
| `seed_parms` | Detail Wrangle | Holds a spare `seed` parameter (int, 0–999); writes it as `detail attribute i@seed` |
| `build_parts` | Point Wrangle | Creates 12 points (one per body part) with `@P`, `v@scale`, `p@orient` derived from the seed |
| `unit_box` | Box SOP | 1×1×1 unit box at origin — the template primitive |
| `copy_to_points` | CopyToPoints | Copies `unit_box` to each point, applying per-point scale and orientation |
| `OUT` | Null | Clean output |

## Body Parts

12 parts total, positioned relative to the character's base (feet at y≈−3):

| Part | Base Position (x, y, z) | Base Scale (x, y, z) |
|------|------------------------|----------------------|
| head | (0, 4.0, 0) | (2.0, 2.0, 2.0) |
| torso | (0, 1.5, 0) | (2.0, 3.0, 1.0) |
| upper_arm_L | (−1.5, 2.0, 0) | (0.75, 1.5, 0.75) |
| upper_arm_R | (1.5, 2.0, 0) | (0.75, 1.5, 0.75) |
| lower_arm_L | (−1.5, 0.5, 0) | (0.75, 1.5, 0.75) |
| lower_arm_R | (1.5, 0.5, 0) | (0.75, 1.5, 0.75) |
| upper_leg_L | (−0.5, −0.5, 0) | (0.75, 1.5, 0.75) |
| upper_leg_R | (0.5, −0.5, 0) | (0.75, 1.5, 0.75) |
| lower_leg_L | (−0.5, −2.0, 0) | (0.75, 1.5, 0.75) |
| lower_leg_R | (0.5, −2.0, 0) | (0.75, 1.5, 0.75) |
| foot_L | (−0.5, −2.9, 0) | (0.9, 0.4, 1.2) |
| foot_R | (0.5, −2.9, 0) | (0.9, 0.4, 1.2) |

## Seed-Driven Variation

Four global multipliers are derived from the seed using `rand(seed + offset)`, mapped to the range [0.8, 1.2] (±20%) unless noted:

| Multiplier | Offset | Range | Affects |
|-----------|--------|-------|---------|
| `head_scale` | 0 | 0.8–1.2 | Head x/y/z scale uniformly |
| `torso_width` | 1 | 0.8–1.2 | Torso x scale only |
| `limb_length` | 2 | 0.8–1.2 | Y scale of all arm and leg parts |
| `height` | 3 | 0.85–1.15 | Y position of all parts above torso |

Parts below torso (legs/feet) receive the limb_length multiplier on their Y scale; their Y positions shift accordingly to maintain connectivity.

## VEX Implementation Notes

- `seed_parms` is a Detail Wrangle with no geometry input; a spare parameter `seed` (type: Integer, default: 0, range: 0–999) is added via "Edit Parameter Interface."
- `build_parts` reads the seed with `detail(0, "seed", 0)` and uses a series of `addpoint()` calls, one per body part, followed by `setpointattrib()` for `@P`, `v@scale`, and `p@orient`.
- `p@orient` is set to identity quaternion `{0, 0, 0, 1}` for all parts (no rotation needed for this system).
- CopyToPoints must have **"Copy and Transform"** enabled and **"Use Template Point Attributes"** on so that `v@scale` and `p@orient` are applied per copy.

## Constraints & Non-Goals

- No rig, no skeleton, no animation support.
- No UVs or materials — geometry only.
- Not packaged as HDA; lives as a raw SOP network.
- No collision detection between parts (overlaps acceptable at extreme seeds).
