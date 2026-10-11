# Actual public-source fixtures

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
