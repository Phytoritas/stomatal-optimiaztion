# Event Bridge Calibration Contract

The production observer export derives 10-minute loadcell water-loss intervals from current Dataset1 rows. Legacy v1.3 daily event-bridged totals may be used only as a provenance-tagged calibration target.

Calibration is allowed only when:

- `date`, `loadcell_id`, and `treatment` match.
- The legacy daily total is finite.
- `valid_coverage_fraction` passes the configured threshold.
- `primary_event_bridge_qc` is acceptable or explicitly allowed.

If no legacy source is available or no rows match, calibrated interval values remain unavailable and metadata reports an uncalibrated status. The pipeline must not fake calibrated ET.

Day/night phases remain radiation-defined from Dataset1 `env_inside_radiation_wm2`, not fixed 06:00-18:00.
