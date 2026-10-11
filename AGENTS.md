# Repository workflow

## Checkpoints

Test code at every implementation checkpoint. On the first failed checkpoint,
investigate the likely cause, stop, and report it to the user. Do not implement
the correction or continue until the user authorizes it. After an authorized
correction passes, continue the remaining requested checkpoints.

## Commit and push by default

The user wants completed changes committed and pushed without a separate reminder.
After all required checkpoints pass, commit the task's changes and push them to
the configured repository's target branch (currently `origin/main`), unless the
user explicitly requests otherwise. Verify that the remote branch contains the
new commit before reporting publication.

Preserve unrelated user changes. Never include credentials, virtual environments,
download caches, or other generated local data. Never force-push. If the remote
has diverged or publishing is blocked, report the blocker rather than overwriting
remote work or claiming that a local commit has been published.
