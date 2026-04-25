## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. -->

## Changes

<!-- Bullet list of key changes. -->

-

## Testing

- [ ] All tests pass (`python -m pytest Programma_CS2_RENAN/tests/ tests/`)
- [ ] Headless validator passes (`python tools/headless_validator.py`)
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] No decrease in test coverage

## Security review

<!--
If this PR touches any path matching SECURITY/BOUNDARY_FILES.txt, the
threat-model-gate workflow has labelled it `security-review-required`.
Complete the checklist below before requesting review.
-->

- [ ] This PR does **not** touch any path in [`SECURITY/BOUNDARY_FILES.txt`](../SECURITY/BOUNDARY_FILES.txt)
      _(if checked, skip the rest of this section)_
- [ ] [`SECURITY/THREAT_MODEL.md`](../SECURITY/THREAT_MODEL.md) section for the affected trust
      boundary has been reviewed and updated if needed
- [ ] [`SECURITY/CONTROL_CATALOG.md`](../SECURITY/CONTROL_CATALOG.md) reflects any new or modified
      controls
- [ ] No new `os.environ.get` of `*_API_KEY` / `*_TOKEN` / `*_SECRET` outside whitelisted modules
- [ ] No new `pickle.load` / `yaml.load(` / `subprocess(..., shell=True)` / `eval` / `exec` without
      a `# SEC: justified <reason>` waiver tag
- [ ] No new external HTTP calls outside the `_validated_get` wrapper
- [ ] No new GitHub Action references without 40-char SHA pinning
- [ ] Any new dependency is exact-pinned in `requirements*.in` and the lock file regenerated with
      `--generate-hashes`

## Related Issues

<!-- Link any related issues: Fixes #123, Relates to #456 -->
