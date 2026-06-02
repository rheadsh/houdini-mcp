# Biped Cube Character Generator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 5-node Houdini SOP network inside `/obj/biped_character` that generates a Minecraft-style bipedal cube character whose proportions are driven by a single integer seed.

**Architecture:** A Detail Wrangle (`seed_parms`) writes the seed as a detail attribute; a second Detail Wrangle (`build_parts`) reads it and creates 12 points — one per body part — with `@P`, `v@scale`, and `p@orient` attributes; a Box SOP provides the unit template; CopyToPoints stamps a box onto every point using the per-point transform attributes; a Null (`OUT`) is the clean output.

**Tech Stack:** Houdini 20+ SOP network, VEX (Attribute Wrangle), Houdini MCP tools.

---

## Houdini Network Structure

All nodes inside `/obj/biped_character/`:

| Node | Type | Inputs |
|------|------|--------|
| `seed_parms` | attribwrangle | none |
| `build_parts` | attribwrangle | input 0: seed_parms |
| `unit_box` | box | none |
| `copy_to_points` | copytopoints | input 0: unit_box · input 1: build_parts |
| `OUT` | null | input 0: copy_to_points |

---

### Task 1: Create the Geometry container

**Nodes:** Create `/obj/biped_character` (geo type)

- [ ] **Step 1: Verify biped_character does not exist yet**

Call `node_get` with `node_path: "/obj/biped_character"`.
Expected: error or "node not found" — confirms we start clean.

- [ ] **Step 2: Create the geo node**

Call `node_create`:
```json
{ "parent_path": "/obj", "node_type": "geo", "node_name": "biped_character" }
```

- [ ] **Step 3: Verify creation**

Call `node_get` with `node_path: "/obj/biped_character"`.
Expected: returns node info with type `geo`.

- [ ] **Step 4: Delete the default file SOP Houdini adds inside new geo nodes**

Call `node_delete` with `node_path: "/obj/biped_character/file1"`.
(Ignore error if it doesn't exist — Houdini version-dependent.)

---

### Task 2: Create seed_parms (Detail Wrangle)

**Nodes:** Create `/obj/biped_character/seed_parms` (attribwrangle)

- [ ] **Step 1: Create attribwrangle**

Call `node_create`:
```json
{ "parent_path": "/obj/biped_character", "node_type": "attribwrangle", "node_name": "seed_parms" }
```

- [ ] **Step 2: Set Run Over to Detail**

Call `parm_set`:
```json
{ "node_path": "/obj/biped_character/seed_parms", "parm_name": "class", "value": 0 }
```
(0 = Detail in the Attribute Wrangle "Run Over" menu)

- [ ] **Step 3: Set VEX snippet**

Call `parm_set`:
```json
{
  "node_path": "/obj/biped_character/seed_parms",
  "parm_name": "snippet",
  "value": "// Change this integer (0–999) to get a different character\nsetdetailattrib(0, \"seed\", 42);"
}
```

- [ ] **Step 4: Cook and verify the seed detail attribute exists**

Call `node_cook` with `node_path: "/obj/biped_character/seed_parms"`.
Call `geo_attributes` with `node_path: "/obj/biped_character/seed_parms"`.
Expected: attribute named `seed`, class `detail`, type `int`.

---

### Task 3: Create unit_box (Box SOP)

**Nodes:** Create `/obj/biped_character/unit_box` (box)

- [ ] **Step 1: Create box SOP**

Call `node_create`:
```json
{ "parent_path": "/obj/biped_character", "node_type": "box", "node_name": "unit_box" }
```

- [ ] **Step 2: Verify default size is 1×1×1**

Call `parm_get` with `node_path: "/obj/biped_character/unit_box"`, `parm_name: "size"`.
Expected: `[1.0, 1.0, 1.0]`. (Houdini default — no change needed.)

- [ ] **Step 3: Cook and verify geometry**

Call `node_cook` with `node_path: "/obj/biped_character/unit_box"`.
Call `geo_info` with `node_path: "/obj/biped_character/unit_box"`.
Expected: **6 primitives** (6 quad faces), **8 points**.

---

### Task 4: Create build_parts (core VEX — generates 12 body part points)

**Nodes:**
- Create: `/obj/biped_character/build_parts` (attribwrangle)
- Connect: `seed_parms` → `build_parts` input 0

- [ ] **Step 1: Create attribwrangle**

Call `node_create`:
```json
{ "parent_path": "/obj/biped_character", "node_type": "attribwrangle", "node_name": "build_parts" }
```

- [ ] **Step 2: Connect seed_parms → build_parts input 0**

Call `node_connect`:
```json
{
  "output_node": "/obj/biped_character/seed_parms",
  "output_index": 0,
  "input_node": "/obj/biped_character/build_parts",
  "input_index": 0
}
```

- [ ] **Step 3: Set Run Over to Detail**

Call `parm_set`:
```json
{ "node_path": "/obj/biped_character/build_parts", "parm_name": "class", "value": 0 }
```

- [ ] **Step 4: Set VEX snippet**

Call `parm_set` with `node_path: "/obj/biped_character/build_parts"`, `parm_name: "snippet"`, value is the VEX block below.

```vex
int seed = detail(0, "seed", 0);

// Four global multipliers derived from seed
float head_sc = fit01(rand(seed),     0.8,  1.2);
float torso_w = fit01(rand(seed + 1), 0.8,  1.2);
float limb_l  = fit01(rand(seed + 2), 0.8,  1.2);
float ht      = fit01(rand(seed + 3), 0.85, 1.15);

// Torso geometry constants (torso center=1.5, height=3.0, depth=1.0)
float torso_hw  = 1.0 * torso_w;         // half-width (scaled)
float torso_top = 3.0;                    // torso top Y
float torso_bot = 0.0;                    // torso bottom Y
float arm_hw    = 0.375;                  // arm half-width
float arm_x     = torso_hw + arm_hw + 0.05;  // arm X offset

// Arm Y positions (cascade downward from shoulder)
float ua_hh = 0.75 * limb_l;
float ua_y  = torso_top - ua_hh;          // upper arm center Y
float la_y  = ua_y - ua_hh - ua_hh;       // lower arm center Y

// Leg Y positions (cascade downward from hip)
float ul_hh = 0.75 * limb_l;
float ul_y  = torso_bot - ul_hh;          // upper leg center Y
float ll_y  = ul_y - ul_hh - ul_hh;       // lower leg center Y
float foot_y = ll_y - ul_hh - 0.2;        // foot center Y

float leg_x = 0.5;
vector4 id  = set(0.0, 0.0, 0.0, 1.0);   // identity quaternion (no rotation)

// HEAD
{
    int pt = addpoint(0, set(0.0, torso_top + head_sc * ht, 0.0));
    setpointattrib(0, "scale",  pt, set(2.0, 2.0, 2.0) * head_sc);
    setpointattrib(0, "orient", pt, id);
}
// TORSO
{
    int pt = addpoint(0, set(0.0, 1.5, 0.0));
    setpointattrib(0, "scale",  pt, set(2.0 * torso_w, 3.0, 1.0));
    setpointattrib(0, "orient", pt, id);
}
// UPPER ARM L
{
    int pt = addpoint(0, set(-arm_x, ua_y, 0.0));
    setpointattrib(0, "scale",  pt, set(0.75, 1.5 * limb_l, 0.75));
    setpointattrib(0, "orient", pt, id);
}
// UPPER ARM R
{
    int pt = addpoint(0, set(arm_x, ua_y, 0.0));
    setpointattrib(0, "scale",  pt, set(0.75, 1.5 * limb_l, 0.75));
    setpointattrib(0, "orient", pt, id);
}
// LOWER ARM L
{
    int pt = addpoint(0, set(-arm_x, la_y, 0.0));
    setpointattrib(0, "scale",  pt, set(0.75, 1.5 * limb_l, 0.75));
    setpointattrib(0, "orient", pt, id);
}
// LOWER ARM R
{
    int pt = addpoint(0, set(arm_x, la_y, 0.0));
    setpointattrib(0, "scale",  pt, set(0.75, 1.5 * limb_l, 0.75));
    setpointattrib(0, "orient", pt, id);
}
// UPPER LEG L
{
    int pt = addpoint(0, set(-leg_x, ul_y, 0.0));
    setpointattrib(0, "scale",  pt, set(0.75, 1.5 * limb_l, 0.75));
    setpointattrib(0, "orient", pt, id);
}
// UPPER LEG R
{
    int pt = addpoint(0, set(leg_x, ul_y, 0.0));
    setpointattrib(0, "scale",  pt, set(0.75, 1.5 * limb_l, 0.75));
    setpointattrib(0, "orient", pt, id);
}
// LOWER LEG L
{
    int pt = addpoint(0, set(-leg_x, ll_y, 0.0));
    setpointattrib(0, "scale",  pt, set(0.75, 1.5 * limb_l, 0.75));
    setpointattrib(0, "orient", pt, id);
}
// LOWER LEG R
{
    int pt = addpoint(0, set(leg_x, ll_y, 0.0));
    setpointattrib(0, "scale",  pt, set(0.75, 1.5 * limb_l, 0.75));
    setpointattrib(0, "orient", pt, id);
}
// FOOT L
{
    int pt = addpoint(0, set(-leg_x, foot_y, 0.15));
    setpointattrib(0, "scale",  pt, set(0.9, 0.4, 1.2));
    setpointattrib(0, "orient", pt, id);
}
// FOOT R
{
    int pt = addpoint(0, set(leg_x, foot_y, 0.15));
    setpointattrib(0, "scale",  pt, set(0.9, 0.4, 1.2));
    setpointattrib(0, "orient", pt, id);
}
```

- [ ] **Step 5: Cook and verify 12 points were created**

Call `node_cook` with `node_path: "/obj/biped_character/build_parts"`.
Call `geo_info` with `node_path: "/obj/biped_character/build_parts"`.
Expected: **12 points**, 0 primitives.

If cook errors, the snippet likely has a VEX syntax issue — re-read and fix the `snippet` parameter before continuing.

---

### Task 5: Create copy_to_points and OUT null

**Nodes:**
- Create: `/obj/biped_character/copy_to_points` (copytopoints)
- Create: `/obj/biped_character/OUT` (null)

- [ ] **Step 1: Create copytopoints SOP**

Call `node_create`:
```json
{ "parent_path": "/obj/biped_character", "node_type": "copytopoints", "node_name": "copy_to_points" }
```

- [ ] **Step 2: Connect unit_box → copy_to_points input 0**

Call `node_connect`:
```json
{
  "output_node": "/obj/biped_character/unit_box",
  "output_index": 0,
  "input_node": "/obj/biped_character/copy_to_points",
  "input_index": 0
}
```

- [ ] **Step 3: Connect build_parts → copy_to_points input 1**

Call `node_connect`:
```json
{
  "output_node": "/obj/biped_character/build_parts",
  "output_index": 0,
  "input_node": "/obj/biped_character/copy_to_points",
  "input_index": 1
}
```

- [ ] **Step 4: Cook and verify 12 boxes were stamped**

Call `node_cook` with `node_path: "/obj/biped_character/copy_to_points"`.
Call `geo_info` with `node_path: "/obj/biped_character/copy_to_points"`.
Expected: **72 primitives** (12 boxes × 6 faces), **96 points** (12 × 8 vertices).

- [ ] **Step 5: Create OUT null**

Call `node_create`:
```json
{ "parent_path": "/obj/biped_character", "node_type": "null", "node_name": "OUT" }
```

- [ ] **Step 6: Connect copy_to_points → OUT**

Call `node_connect`:
```json
{
  "output_node": "/obj/biped_character/copy_to_points",
  "output_index": 0,
  "input_node": "/obj/biped_character/OUT",
  "input_index": 0
}
```

- [ ] **Step 7: Set OUT as the display node**

Call `node_set_flag`:
```json
{ "node_path": "/obj/biped_character/OUT", "flag": "display", "value": true }
```

---

### Task 6: Layout, screenshot, seed variation test, and save

- [ ] **Step 1: Auto-layout all nodes**

Call `node_layout` with `node_path: "/obj/biped_character"`.

- [ ] **Step 2: Take viewport screenshot — seed 42**

Call `viewport_screenshot`. Confirm the character silhouette looks like a bipedal blocky figure.

- [ ] **Step 3: Test a different seed (123)**

Call `parm_set`:
```json
{
  "node_path": "/obj/biped_character/seed_parms",
  "parm_name": "snippet",
  "value": "setdetailattrib(0, \"seed\", 123);"
}
```
Call `node_cook` with `node_path: "/obj/biped_character/OUT"`.
Call `viewport_screenshot`. Expected: visibly different proportions from seed 42.

- [ ] **Step 4: Test seed 0 (minimum)**

Call `parm_set` with value `"setdetailattrib(0, \"seed\", 0);"`, cook, screenshot.

- [ ] **Step 5: Restore default seed and save**

Call `parm_set` with value `"// Change this integer (0-999) to get a different character\nsetdetailattrib(0, \"seed\", 42);"`.
Call `hip_save` to save the scene.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add biped cube character generator SOP network"
```
