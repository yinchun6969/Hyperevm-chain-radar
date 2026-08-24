# `main` Branch Protection

Recommended repository rule for stable releases:

- Target branch: `main`
- Require a pull request before merging
- Require status checks to pass before merging
- Required check: `validate`
- Do not allow bypassing the above settings for normal development
- Block force pushes
- Block branch deletion
- Do not allow direct pushes to `main`

GitHub UI path:

`Settings` → `Rules` → `Rulesets` → `New ruleset` → `New branch ruleset`

Suggested ruleset name: `Protect main`

Target branch pattern: `main`

Enable:

1. Restrict deletions
2. Block force pushes
3. Require a pull request before merging
4. Require status checks to pass
5. Add required check `validate`

After the ruleset is active, normal release flow is:

`version branch` → `Pull Request` → `validate` CI → review → merge to `main`.
