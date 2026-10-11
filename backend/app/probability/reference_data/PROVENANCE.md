# Genuine NASA CARA validation fixtures

Unmodified downloads from NASA `CARA_Analysis_Tools`, commit
`ce0f00722c56808755ee0adbe47a4e3d56439484`, directory
`DataFiles/PcTestCaseCDMs`. The accompanying NASA README and complete original
workbook are included. Four CDMs are selected for reproducible offline validation.
NASA data attribution: United States Government / NASA CARA.

These are historical reference conjunctions, not live SOCRATES encounters.
States use EME2000, positions km, velocities km/s, and CR/CT/CN covariance
records object-local RTN in m². The header COMMENT HBR is the combined radius;
object EXCLUSION_VOLUME_RADIUS is not the collision radius.

CDM Pc is rounded; the workbook has precise Pc2D and Pc2D_NoAdj values.
NASA `Pc2D_FromCDM.m` / `ComparePc2D_to_CARAValues.m` describe a linear local
TCA correction (`FindNearbyCA.m`). Covariances are rotated using original
states then held fixed across this sub-millisecond correction.

NASA's standalone Pc2D comparison sums covariances (independent model), even
though CDMs also contain common-density DCP metadata. Reference validation
must explicitly select that independent benchmark model, disclose the
correlation omission, and must never present it as calibrated encounter risk.
The general engine must reject known correlations without cross-covariance.
No NASA numerical implementation is copied into the Kessler integrator.
