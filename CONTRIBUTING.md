# Contributing

Thanks for looking. Please read the next paragraph before investing effort.

This is an experimental research system, released so the approach and the code can be studied
and adapted. It is **maintained as time permits, with no production-support commitment**.
Issues and pull requests are welcome, but may not be reviewed promptly, and large unsolicited
changes are unlikely to be merged. If you need this to move at your pace, forking is a
legitimate and expected outcome.

## Getting set up

```sh
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests scripts
```

Python 3.12 is required. The unit suite needs no AWS credentials. Live and destructive tests
are deselected by default; do not enable them against an account you do not intend to change.

## What is likely to be accepted

- Bug fixes with a test that fails before the change and passes after
- Corrections when documentation overstates what is implemented
- Tests that pin down a guard that is currently only implied

## What is unlikely to be accepted

- New autonomy rungs, spending, or external communications
- Weakening the AWS context guard, IAM negatives, or the implemented/not-enabled boundary
- Adding a path that talks to AWS from the default unit suite

## Security

Do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).

## Conduct

Be straightforward and civil; assume competence. See
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
