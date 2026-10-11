# Actual public-source fixtures

`satcat_actual.csv` preserves six complete rows from the actual 70,980-row
download of https://celestrak.org/pub/satcat.csv on 2026-10-11 UTC. The documented
schema/type/status definitions were checked at
https://celestrak.org/satcat/satcat-format.php (updated 2026-09-23) and
https://celestrak.org/satcat/status.php. These are dated offline metadata, not
live records. RCS is radar cross section in m², never aerodynamic area or mass.

`socrates_actual.csv` contains the first five rows actually downloaded from
https://celestrak.org/SOCRATES/sort-minRange.csv during this implementation.
HTTP Last-Modified: Sat, 10 Oct 2026 15:48:20 GMT. The full CSV contained
195,282 rows. The documentation was verified at
https://celestrak.org/SOCRATES/socrates-format.php.

Rows used in offline validation are historical predictions, not current live
encounters. Tests that change fields or append invalid/duplicate rows do so only
to exercise validation; those mutations are never labeled as external data.

`gp_actual.json` stores the actual separately downloaded JSON GP records for
catalog IDs 53495, 34452 and 100033. Source query for each object:
`https://celestrak.org/NORAD/elements/gp.php?CATNR=<id>&FORMAT=JSON`.
Their original epochs and fields have been preserved. The fixture combines
three independent responses for convenient offline testing; it is not passed
off as a single-object response or as a current live dataset.
