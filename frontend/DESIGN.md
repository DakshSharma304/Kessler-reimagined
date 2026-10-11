# Kessler interface direction

An orbital instrument, not a marketing page. The Earth occupies the workspace;
controls sit around it in a compact header, explorer, inspector and time rail.
Graphite surfaces, off-white text, quieter metadata, thin separators and one
consistent neutral primary action. System typography prioritizes the native
Apple stack, with tabular numeric values. No decorative orange text, random
gradient panels or multicolored metrics. Color conveys trajectories, known
object classes and actual scientific status only. Earth imagery is naturally
blue; this is not a blue dashboard theme.

Small transitions120–250ms; springs for panels, eased camera focus. Reduced
motion disables decorative animation without disabling controls. Data-source
timestamps, missing values, partial coverage, hypothetical assumptions and
incomplete screening remain visible. There are no invented progress percentages,
random object positions, fake probabilities or predetermined maneuver results.

Desktop: globe-centered overlays. Phone: compact scrollable navigation, visible
globe, contextual sheets rather than shrunken desktop panels. All actionable
controls have labels/focus states; errors are presented where they arise.

Rendering contract: backend ITRS kilometers mapped to Three.js `(x,z,-y)` and
scaled by WGS84 equatorial radius6378.137km. Earth-fixed globe does not rotate
again relative to these points. Playback requests supported epochs from the
backend; any visual interpolation must disclose its sample interval.
