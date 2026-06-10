# Changelog

## [Recently Completed]
### Local Network Play (Phase 1): Discovery Foundation
- **Identity & Config:** Established `PLAYER_NAME` and `LAN_PORT` (55555) in `constants.py` for standardized network identification.
- **Non-Blocking Network Manager:** Created `engine/network_manager.py` using Python's `socket` and `threading` libraries.
- **UDP Discovery Loop:** Implemented background broadcasting of identity payloads ("Dustin's Game") and automated subnet scanning for active host beacons.
- **Terminal Debugging:** Added direct console logging for discovered hosts, allowing connectivity verification without graphic synchronization.

### Frame-Perfect Parry: High-Skill Defensive Combat
- **Active Parry Window:** Implemented a 0.15s (9-frame) window at the start of a `BLOCK` or `DASH`.
- **Damage Negation:** Successful parries reduce incoming damage to 0% and prevent stagger.
- **Enemy Stun:** Parrying an attack triggers a long stagger (0.8s) on the hostile entity.
- **Kinetic Reset:** Instantly resets the player's Dash cooldown upon a successful parry.
- **Visual Feedback:** High-contrast ink spark VFX triggered at the point of impact.
- **Audio Cues:** Integrated `combat_parry.ogg` trigger with OSD logging.
- **Screen Shake:** Brief, intense shake effect to signify a powerful deflection.

### Telegraphed Enemy Attacks: Combat State Machine & Visual Tells
- **Actor Combat Lifecycle:** Expanded `ActorState` with `WIND_UP`, `STRIKE`, and `RECOVERY`, creating a rhythmic, skill-based combat loop.
- **Visual Stanza Tells:** Implemented pulsing "Margin Red" outlines for wind-ups and solid red flashes for damage frames.
- **Weapon-Specific Indicators:** Added transient white line indicators for 'THRUST' attacks and arc segments for 'SWING' attacks to help player anticipation.
- **Audio Telegraphing:** Hooked `enemy_telegraph.ogg` (shink/glint) into the start of every enemy wind-up.
- **Behavioral Variety:** Balanced unique telegraph and recovery durations for Slugs (slow), Bats (fast), Minibosses (elite), and The Final Author (boss).
- **Non-Weapon Telegraphs:** Ensured that 'Lunge' enemies (Bats, Slugs) have clearly readable attack frames even without held weapons.
- **Combat Stability Fixes:**
    - **Per-Attack Hit Latch:** Implemented `has_hit_this_attack` to prevent enemies from one-shotting players with per-frame damage.
    - **Player i-frames:** Added damage invincibility during the `STAGGERED` and `DASHING` states for fair engagement.

### Dynamic Proximity Music & Core SFX Engine
- **Euclidean Engagement Layer:** Overhauled GameState proximity tracking to use 600px Euclidean radius for elite engagement.
- **Temporal Hysteresis:** Implemented a 3.0s temporal cooldown to prevent music jitter when exiting proximity.
- **AudioManager Overhaul:** Refined music transitions to handle intelligent sequential fading for stable track switching.
- **Physical Audio Layer (SFX):** Enhanced AudioManager to support concurrent sound effects with debug tracking and a live OSD.
- **Layered Attack System:** Implemented the 'Layered Attack Rule' where `attack_swing.ogg` triggers on swing and layers with `attack_hit.ogg` on impact.
- **Environmental & System Cues:** Added auditory feedback for acid rain damage (`player_hurt_rain.ogg`), safe circle contraction (`bleed_start.ogg`), and Respite resting (`respite_rest.ogg`).
- **Audio Debug OSD:** Implemented a live on-screen display in the top-left corner to verify music and SFX triggers in real-time.

### The Stanza System: Actor State Machine & Patrols
