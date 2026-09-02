# Phase 25 Polish Checklist

`PASS` means automated validation and/or deterministic rendering verified the structural contract. `HUMAN REVIEW` identifies subjective or hardware-dependent judgment and is not represented as completed testing.

| Area | Status | Evidence / remaining review |
|---|---|---|
| Main Menu | PASS | Safe-area capture and navigation tests |
| Save Slots | PASS | State wording, destructive defaults, persistence scenarios |
| Settings | PASS | Eleven controls fit; values and focus remain visible |
| Achievements | PASS | 19 definitions, bounded scroll/filter, hidden protection |
| World Map | PASS | Paths plus non-color node markers |
| HUD | PASS | Screen-space, cached, bounded |
| Pause | PASS | Full simulation freeze and dimmed backdrop |
| Dialogue | PASS | Wrapping, prompts, graph validation |
| Game Over | PASS | Dimmed intentional retry flow |
| Level Complete | PASS | Current map/replay prompts and frozen result |
| World Complete | PASS | Progression and transition scenarios |
| Four normal levels | PASS | Five validators and content integrity |
| Sanctum / Ashen Warden | PASS | Attack/phase/defeat scenarios and CORE OPEN cue |
| Secrets / Ember Veil | PASS | 12 definitions and reveal persistence |
| NPCs | PASS | Four catalogs and terminating dialogue graphs |
| Audio | HUMAN REVIEW | Lifecycle/fallback automated; listening mix required |
| Effects | PASS | Full/Reduced/Off, caps, lifecycle, shake policy |
| Keyboard | PASS | Simulated action/state journeys |
| Controller | HUMAN REVIEW | Simulated backend passes; physical feel required |
| Accessibility | PASS | Structural audit in `ACCESSIBILITY.md` |
| Fullscreen | HUMAN REVIEW | Mode logic automated; host display review required |
| Performance | PASS | Benchmarks below frame budget and soak bounded |
| Saves | PASS | Empty/valid/recovered/corrupt/future cases |
| Editor | HUMAN REVIEW | Isolation/commands automated; mouse ergonomics required |
