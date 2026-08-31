# Pause and Game Over

## Pause

Escape during gameplay enters a dedicated Pause application mode. Player physics, enemies, boss AI, projectiles, platforms, level time, campaign play time, and visual-effect simulation freeze; audio context may continue. Options are Resume, Settings, Restart Level, Return to World Map, and Quit to Main Menu. Destructive navigation uses reusable confirmation dialogs that default to Cancel.

Restart reconstructs the authored runtime through the same reset path as F7: collectibles, score, enemies, power-ups, switches, doors, blocks, checkpoints, projectiles, timer, deaths, effects, and audio reset. It produces no `LevelResult`. Map/main-menu exits abandon the unfinished attempt without replacing committed campaign progress.

## Game Over

Game Over triggers once Nova's final-life death animation finishes. Lives clamp at zero. Combat simulation stops, hostile projectiles are cleared, boss encounters release arena/camera state, transient effects and audio context reset, and no failed `LevelResult`, boss defeat, world completion, or campaign progress is awarded.

Retry creates a fresh authored runtime with three lives, full health, initial spawn/checkpoint, reset timer and objects, and a fresh boss at Phase 1/full health. Return to World Map preserves only previously committed progress. Quit to Main Menu performs the normal safe autosave. Game Over deliberately ignores mid-run checkpoints because Retry is a new attempt.

## Controller flow

Game Over is controller-only navigable: D-pad/stick chooses Retry, World Map, or Main Menu and south face confirms. Retry suppresses the held Confirm edge, preventing an unintended jump on the fresh run. Disconnecting at Game Over clears input safely and keyboard remains usable.
