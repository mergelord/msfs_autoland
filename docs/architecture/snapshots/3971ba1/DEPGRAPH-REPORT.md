# DEPGRAPH-3971ba1 — Dependency Graph Report

**Commit:** `3971ba12113d8994665b1c9a172f2dca6c9e3855`

## Counters

| Metric | Value |
|--------|-------|
| Nodes (files) | 49 |
| Edges (unique pairs) | 60 |
| Unique import lines | 62 |
| Lazy / late edges (lines) | 9 |
| TYPE_CHECKING edges | 3 |
| Dynamic imports | 0 |
| Non-trivial SCCs (runtime) | 0 |
| Runtime cycles (len ≤ 6) | 0 |
| Full cycles incl. TYPE_CHECKING | 1 |
| Orphan nodes | 4 |
| Modules without test imports | 33 |

## Cycles

### Runtime cycles (no TYPE_CHECKING edges)

None — all cycles involve TYPE_CHECKING edges only.

### Full cycles (including TYPE_CHECKING)

1. `main -> modules.approach_phases -> main`

## Lazy / Late Imports

Import lines inside functions, lambdas, or conditional blocks (but NOT TYPE_CHECKING).

| File | Line | Source → Target |
|------|------|-----------------|
| `modules.aircraft_adapter` | 33 | → `modules.aircraft_config_reader` |
| `modules.aircraft_adapter` | 42 | → `modules.wasm_interface` |
| `modules.approach_dialog` | 259 | → `modules.navigraph_parser` |
| `modules.approach_phases` | 394 | → `modules.audio_alerts` |
| `modules.navigraph_parser` | 316 | → `modules.settings` |
| `modules.settings_dialog` | 73 | → `modules.navigraph_parser` |
| `modules.settings_dialog` | 152 | → `modules.navigraph_parser` |
| `modules.settings_dialog` | 174 | → `modules.navigraph_parser` |
| `gui` | 2443 | → `modules.settings_dialog` |

## TYPE_CHECKING Imports

| File | Line | Source → Target |
|------|------|-----------------|
| `modules.approach_phases` | 13 | → `main` |
| `modules.synthetic_glidepath` | 33 | → `modules.navigation` |
| `modules.synthetic_glidepath` | 34 | → `modules.types` |

## Top Fan-In (most imported)

| Rank | Module | Fan-In |
|------|--------|--------|
| 1 | `modules.types` | 5 |
| 2 | `modules.thresholds_config` | 4 |
| 3 | `modules.control_ownership` | 3 |
| 4 | `modules.ils_navigation` | 3 |
| 5 | `modules.navigraph_parser` | 3 |
| 6 | `modules.audio_alerts` | 2 |
| 7 | `modules.navigation` | 2 |
| 8 | `modules.settings` | 2 |
| 9 | `main` | 2 |
| 10 | `modules.aircraft_adapter` | 1 |

## Top Fan-Out (most dependents)

| Rank | Module | Fan-Out |
|------|--------|---------|
| 1 | `main` | 27 |
| 2 | `modules.approach_dialog` | 5 |
| 3 | `gui` | 4 |
| 4 | `modules.approach_phases` | 3 |
| 5 | `modules.aircraft_adapter` | 2 |
| 6 | `modules.airports_database` | 2 |
| 7 | `modules.autothrottle` | 2 |
| 8 | `modules.settings_dialog` | 2 |
| 9 | `modules.synthetic_glidepath` | 2 |
| 10 | `modules.aileron_compensation` | 1 |

## Topological Layers

L0 = root utilities (no runtime internal deps) → higher = closer to main/gui.

**L0** (43): `main`, `modules.aircraft_adapter`, `modules.aircraft_config_reader`, `modules.aircraft_geometry`, `modules.airports_database`, `modules.approach_dialog`, `modules.approach_phases`, `modules.approach_speed_calculator`, `modules.audio_alerts`, `modules.autopilot_takeover`, `modules.autothrottle`, `modules.base_controller`, `modules.command_gateway`, `modules.connection_monitor`, `modules.connection_optimizer`, `modules.control`, `modules.control_ownership`, `modules.dme_navigation`, `modules.engine_failure_detector`, `modules.flare_controller`, `modules.fms_reader`, `modules.ils_navigation`, `modules.log_database`, `modules.msfs_airport_reader`, `modules.navigation`, `modules.navigraph_parser`, `modules.safety_guard`, `modules.settings`, `modules.settings_dialog`, `modules.simconnect_client_data`, `modules.stabilized_approach`, `modules.structured_logger`, `modules.synthetic_glidepath`, `modules.telemetry`, `modules.telemetry_recorder`, `modules.thresholds_config`, `modules.turbulence_detector`, `modules.types`, `modules.virtual_joystick`, `modules.wasm_interface`, `modules.wasm_version_checker`, `modules.wind_correction`, `modules.wind_shear_detector`

**L1** (6): `gui`, `modules.__init__`, `modules.aileron_compensation`, `modules.auto_fixer`, `modules.log_analyzer`, `modules.rudder_compensation`

## Orphan Nodes

- `modules.__init__`
- `modules.auto_fixer`
- `modules.log_analyzer`
- `modules.rudder_compensation`

## Dynamic Imports

None.

## Untested Modules (no test imports them)

- `__init__`
- `aileron_compensation`
- `aircraft_config_reader`
- `aircraft_geometry`
- `airports_database`
- `approach_dialog`
- `approach_speed_calculator`
- `audio_alerts`
- `auto_fixer`
- `autothrottle`
- `base_controller`
- `connection_monitor`
- `dme_navigation`
- `engine_failure_detector`
- `flare_controller`
- `fms_reader`
- `log_analyzer`
- `log_database`
- `msfs_airport_reader`
- `navigraph_parser`
- `rudder_compensation`
- `settings`
- `settings_dialog`
- `simconnect_client_data`
- `stabilized_approach`
- `structured_logger`
- `telemetry`
- `thresholds_config`
- `turbulence_detector`
- `virtual_joystick`
- `wasm_interface`
- `wasm_version_checker`
- `wind_shear_detector`

## File Statistics

| File | Local Edges | Lazy | TC | Stdlib | Third-party | Dynamic |
|------|-------------|------|-----|--------|-------------|---------|
| `gui.py` | 4 | 1 | 0 | 8 | 0 | 0 |
| `main.py` | 27 | 0 | 0 | 7 | 0 | 0 |
| `modules\__init__.py` | 0 | 0 | 0 | 0 | 0 | 0 |
| `modules\aileron_compensation.py` | 1 | 0 | 0 | 3 | 0 | 0 |
| `modules\aircraft_adapter.py` | 2 | 2 | 0 | 4 | 0 | 0 |
| `modules\aircraft_config_reader.py` | 0 | 0 | 0 | 5 | 0 | 0 |
| `modules\aircraft_geometry.py` | 0 | 0 | 0 | 2 | 0 | 0 |
| `modules\airports_database.py` | 2 | 0 | 0 | 5 | 0 | 0 |
| `modules\approach_dialog.py` | 5 | 1 | 0 | 4 | 0 | 0 |
| `modules\approach_phases.py` | 3 | 1 | 1 | 3 | 0 | 0 |
| `modules\approach_speed_calculator.py` | 0 | 0 | 0 | 4 | 0 | 0 |
| `modules\audio_alerts.py` | 0 | 0 | 0 | 4 | 2 | 0 |
| `modules\auto_fixer.py` | 0 | 0 | 0 | 6 | 0 | 0 |
| `modules\autopilot_takeover.py` | 0 | 0 | 0 | 4 | 0 | 0 |
| `modules\autothrottle.py` | 2 | 0 | 0 | 4 | 0 | 0 |
| `modules\base_controller.py` | 0 | 0 | 0 | 2 | 0 | 0 |
| `modules\command_gateway.py` | 1 | 0 | 0 | 5 | 0 | 0 |
| `modules\connection_monitor.py` | 0 | 0 | 0 | 9 | 0 | 0 |
| `modules\connection_optimizer.py` | 0 | 0 | 0 | 5 | 0 | 0 |
| `modules\control.py` | 0 | 0 | 0 | 3 | 1 | 0 |
| `modules\control_ownership.py` | 0 | 0 | 0 | 2 | 0 | 0 |
| `modules\dme_navigation.py` | 0 | 0 | 0 | 4 | 0 | 0 |
| `modules\engine_failure_detector.py` | 0 | 0 | 0 | 4 | 0 | 0 |
| `modules\flare_controller.py` | 1 | 0 | 0 | 4 | 0 | 0 |
| `modules\fms_reader.py` | 0 | 0 | 0 | 3 | 0 | 0 |
| `modules\ils_navigation.py` | 0 | 0 | 0 | 4 | 0 | 0 |
| `modules\log_analyzer.py` | 0 | 0 | 0 | 7 | 0 | 0 |
| `modules\log_database.py` | 0 | 0 | 0 | 6 | 0 | 0 |
| `modules\msfs_airport_reader.py` | 1 | 0 | 0 | 3 | 0 | 0 |
| `modules\navigation.py` | 1 | 0 | 0 | 4 | 0 | 0 |
| `modules\navigraph_parser.py` | 1 | 1 | 0 | 6 | 0 | 0 |
| `modules\rudder_compensation.py` | 0 | 0 | 0 | 3 | 0 | 0 |
| `modules\safety_guard.py` | 0 | 0 | 0 | 4 | 0 | 0 |
| `modules\settings.py` | 0 | 0 | 0 | 4 | 0 | 0 |
| `modules\settings_dialog.py` | 4 | 3 | 0 | 4 | 0 | 0 |
| `modules\simconnect_client_data.py` | 0 | 0 | 0 | 3 | 0 | 0 |
| `modules\stabilized_approach.py` | 1 | 0 | 0 | 4 | 0 | 0 |
| `modules\structured_logger.py` | 1 | 0 | 0 | 10 | 0 | 0 |
| `modules\synthetic_glidepath.py` | 2 | 0 | 2 | 2 | 0 | 0 |
| `modules\telemetry.py` | 0 | 0 | 0 | 2 | 1 | 0 |
| `modules\telemetry_recorder.py` | 0 | 0 | 0 | 5 | 0 | 0 |
| `modules\thresholds_config.py` | 0 | 0 | 0 | 4 | 0 | 0 |
| `modules\turbulence_detector.py` | 1 | 0 | 0 | 6 | 0 | 0 |
| `modules\types.py` | 0 | 0 | 0 | 1 | 0 | 0 |
| `modules\virtual_joystick.py` | 0 | 0 | 0 | 2 | 1 | 0 |
| `modules\wasm_interface.py` | 1 | 0 | 0 | 4 | 1 | 0 |
| `modules\wasm_version_checker.py` | 0 | 0 | 0 | 7 | 0 | 0 |
| `modules\wind_correction.py` | 0 | 0 | 0 | 3 | 0 | 0 |
| `modules\wind_shear_detector.py` | 1 | 0 | 0 | 5 | 0 | 0 |
