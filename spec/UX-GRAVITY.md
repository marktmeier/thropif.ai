# UX Gravity — Physics-Based Data Visualization

## The Rule

**truth.rate = mass. Mass = gravity. Gravity = behavior.**

Everything in the OOi visualizer has weight. Weight comes from truth. Truth comes from evidence. No evidence = no weight = float away.

## Physics

| Property | Drives | Behavior |
|---|---|---|
| truth.rate | mass | Higher truth = heavier = harder to move, stays centered |
| interconnections | magnetism | Connected objects attract each other |
| fill count | density | More cells filled = denser, more opaque |
| decay rate | entropy | Stale objects lose mass, drift outward |
| L7 gold seal | anchor | Maximum gravity — pins the object |

## Behaviors

### Objects
- **Heavy** (high truth.rate) → center of view, slow to drag, snaps back, pulls neighbors
- **Light** (low truth.rate) → edges, easy to fling, drifts, transparent
- **Empty** (00i, no data) → floats, nearly invisible, no gravity
- **Gold seal** (L7.7 verified) → immovable anchor, everything orbits it

### Connections (beams)
- **Strong** (high strength) → rubber band, pulls objects together
- **Weak** (low strength) → loose thread, barely visible
- **Active** (data flowing) → pulsing glow, particles moving along the beam

### Interactions
- **Hover** → object lifts slightly (anti-gravity preview)
- **Click** → object PULLS connected objects toward it (magnetic focus)
- **Release** → spring physics, objects settle back with damping
- **Drag** → feel the mass (heavy = slow follow, light = instant follow)
- **Double-click** → drill down (zoom into object's own hourglass)
- **Scroll** → zoom with momentum (physics scroll, not instant)
- **Throw** → fling an object, it arcs and settles by gravity

### The Hub
01-meier-festivals = center of gravity. Everything orbits it. Highest inbound connections = highest pull. The hub doesn't move — everything else positions relative to it.

### macOS Style
- **Backdrop blur** on panels (vibrancy)
- **Spring animations** (not linear — overshoot + settle)
- **Depth shadows** (layers of shadow = layers of depth)
- **Smooth corners** (continuous corner radius, not circular)
- **System font** when possible, JetBrains Mono for data
- **Reduce motion** respected for accessibility

## Implementation

Force-directed graph with:
- Charge force = truth.rate (repel proportional to mass)
- Link force = interconnection strength
- Center force = hub gravity
- Collision force = prevent overlap
- Drag force = mouse interaction with mass-based resistance
- Damping = 0.92 (things settle, don't oscillate forever)

Library: d3-force or custom Canvas2D physics loop.

## The Metaphor

The OOi visualizer is a solar system:
- **Hub** = the sun (center, maximum gravity)
- **Heavy objects** = planets (orbit close, stable)
- **Light objects** = asteroids (orbit far, unstable)
- **Empty objects** = dust (float, barely visible)
- **Gold-sealed** = fixed stars (anchored, everything references them)
- **Beams** = gravitational pull (visible as glowing threads)
- **Time** = orbital decay (old objects spiral outward unless re-verified)
