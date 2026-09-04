# Pull Request

## What does this PR do?

<!-- One-paragraph summary. Reference the work package from docs/work-packages.md if applicable. -->

- Related issue: <!-- `Closes #123` or `Refs #123` -->
- Work package: <!-- e.g. "WP-03 Bitcoin provider" -->

## Type of change

- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] refactor — code change with no behaviour change
- [ ] test — adds or fixes tests
- [ ] chore — tooling / build / CI

## Checklist

- [ ] Branch is named `feature/<x>`, `fix/<x>` or `chore/<x>` (see CONTRIBUTING.md)
- [ ] Commit messages follow Conventional Commits
- [ ] I have added/updated tests for any new/changed behaviour
- [ ] `make lint` passes locally
- [ ] `make test` passes locally
- [ ] Docs updated (if behaviour changed): `docs/*.md`
- [ ] No new secrets committed
- [ ] I have **not** modified any `docs/contracts.md` interface without a
      `BREAKING CHANGE:` footer and a heads-up in `#dev`

## Public interface impact

If this PR changes a public interface, list the affected symbols and the
breaking/contract-impact tag:

| Symbol | Change kind | Versioned? |
|--------|-------------|------------|

## How was this tested?

<!-- Describe the manual/automated steps you ran. -->

## Screenshots / logs

<!-- Optional. Drop CI output here if it helps reviewers. -->