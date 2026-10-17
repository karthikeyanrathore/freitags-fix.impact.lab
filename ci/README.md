# GitHub Actions workflows (to be moved into place)

These are the CI/CD workflows. They live here because the tool that wrote them can't push to `.github/workflows/` (GitHub requires the `workflow` scope). Move them with your own git credentials:

```bash
git pull
git mv ci/workflows .github/workflows
git commit -m "ci: enable GitHub Actions workflows"
git push
```

- `ci.yml`: on every push/PR, builds the compose stack and runs `scripts/e2e.sh` (429 outage → agent fix → health check 5/5).
- `deploy.yml`: when CI passes on `main`, SSHes into the VM, runs `scripts/deploy.sh`, smoke-tests the public URL. Skips until these repo settings exist:
  - Secret `VM_SSH_KEY`: private key of a deploy key pair; its public key goes in the VM user's `~/.ssh/authorized_keys`
  - Variables `VM_HOST` (`66.201.4.39`), `VM_USER`, `VM_APP_DIR` (repo clone path on the VM), optional `VM_PORT`
