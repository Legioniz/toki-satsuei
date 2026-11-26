# Required GitHub repository ruleset for TOKI SATSUEI

This file documents settings to apply in GitHub Settings → Rules → Rulesets. It is not itself an active ruleset.

Target: `refs/heads/main`

- Require a pull request before merging; block direct pushes.
- Require the deployment workflow's `verify-and-package` status check.
- Require CodeQL analysis checks for JavaScript/TypeScript, Python, and Actions when those exact check names appear in the ruleset picker.
- Block force pushes and branch deletion.
- Require all review conversations to be resolved.
- Disable routine bypasses; retain a separately documented owner emergency process.
- Enable secret scanning and push protection.
- Keep Dependabot security updates enabled.

Do not require signed commits until automation produces verified signatures. Do not require a second-person approval if no second maintainer exists, because that would block the sole owner from merging.

The connected GitHub integration can read rulesets but cannot create or edit repository security settings. An owner must apply this ruleset in GitHub.
