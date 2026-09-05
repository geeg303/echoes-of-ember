# Mechanical Progression and Capability Inventory

## Progression matrix

| Mechanic | Introduced | Reinforced | Combined | Challenged | Mastered |
|---|---|---|---|---|---|
| Run/jump, coyote/buffer | W1-1 | all W1 | platforms/combat | currents/polarity | W4 network traversal |
| Stomp | W1-1 | W1 enemies | moving terrain | armored/polarity defenses | W4 mixed encounters |
| Ember Pulse | W1-1 | turrets/breakables/boss | currents redirect shots | polarity/reflective defenses | Keeper/network |
| Wind Boots | W1 | ravine momentum | currents and timed routes | reversed flow | W4 branch mastery |
| Aether Wing | W1 | canopy | updrafts/alternate states | polarity timing | network vertical sequence |
| Stone Guard | W1 | combined danger/boss | environmental pressure | deliberate high-value hazards | final endurance choices |
| Moving/falling/disappearing platforms | W1 | all later worlds | currents/polarity | state/timing inversions | W4 combinations |
| Switches/doors/checkpoints | W1 | world objectives | current/polarity routing | nonlinear branches | final network control |
| Secrets/secret exits | W1 Ember Veil | every world | power/mechanic routes | misleading official paths | full Veil history |
| Ember Currents | W2 prototype | W2 levels | projectiles/platforms/enemies | polarity in W3 | W4 network |
| Ember Polarity | W3 prototype | W3 levels | currents/doors/defenses | rapid multi-state decisions | W4 network/Keeper |

## Proposed mechanic contracts

### Ember Currents — NEW SYSTEM REQUIRED

World-space authored fields push or lift actors, optionally redirect projectiles, influence designated platforms/enemies, and shape collectible routes. Direction, strength, bounds, affected categories, visualization, and activation must be data-driven. Teach with safe horizontal flow, test with lift/landing, then twist by redirecting Ember Pulse or moving hazards. Required routes must have recoverable exits and readable effects-off geometry. Current editor needs field placement/direction handles; validators need finite bounds/strength/category checks; debug needs vector overlays.

### Ember Polarity — NEW SYSTEM REQUIRED

An authoritative two-state environmental relationship, not a second physics engine. Designated platforms, hazards, doors, currents, and defenses react to the active state. Switching must be clearly telegraphed by shape/pattern/animation plus color and cannot invalidate Nova inside geometry. The editor needs paired-state preview; validators need compatible references and safe spawn/goal reachability; debug needs active-state and linked-object inspection.

## Reusable-system inventory

| Idea | Classification | Notes |
|---|---|---|
| Linear five-level World 2 route | SUPPORTED NOW | Registry/map data already supports ordered unlocks |
| World 4 branches | MINOR EXTENSION | Graph supports branching; “all branches complete” unlock predicate likely required |
| New levels/themes/collectibles/enemy placements | SUPPORTED NOW | Existing JSON/editor/validators; new decorative palettes may be data additions |
| Currents | NEW SYSTEM REQUIRED | Actor/projectile/platform influence and authoring/debug support |
| Polarity | NEW SYSTEM REQUIRED | Global/local state, safe geometry transitions, references |
| New enemy behaviors | MINOR EXTENSION | Base enemy/config/animation architecture exists; mechanic integration is new work |
| Luminous/Hollow/final bosses | MINOR EXTENSION | Boss contract exists; implementations and richer arena orchestration required |
| Midpoint encounter | MINOR EXTENSION | Boss-like state without world completion needs metadata/progression support |
| Veil narrative branches | MINOR EXTENSION | Secret exits/revealed nodes exist; multi-world persistence catalogs must expand |
| Existing power-up route alternatives | SUPPORTED NOW | One-active policy and data pickups exist |
| Secret Token lore thresholds | MINOR EXTENSION | Current totals persist; optional unlock semantics/UI need design |
| Full-game achievements | SUPPORTED/MINOR EXTENSION | Definition/event architecture scales; catalogs and possible world-set conditions needed |
| Multi-world saves | MINOR EXTENSION | Current registry is single-world; migration must preserve World 1 |
| Packaging new content | SUPPORTED NOW | Resource manifest automatically includes assets/data |

## Achievement and save direction

Keep achievement categories progression, collectibles, secrets, story, combat, and challenge. Add sparingly at world completion, defining mechanic mastery, meaningful Veil milestones, and whole-game feats; avoid one achievement per trivial stage event. Do not modify definitions in Milestone A.

Likely future save additions are active/current world, multi-world registries/results, new boss/midpoint flags, polarity/current-related objective flags only if persistent, and expanded revealed nodes. A future migration must retain World 1 results, secret exits, revealed Ember Veil, Ashen Warden defeat, dialogue flags, timestamps/playtime, and the separate achievement profile.

## Editor/debug/test production rule

Prototype authoring support before full level production. Extend object schemas and validators first; add editor palette/properties/visual overlays; add debug inspection and safe grant/state commands; write units plus mechanic scenarios; add one representative performance benchmark; then author campaign content. Each world integration adds clean/returning/secret/failure E2E paths and packaged-content validation.
