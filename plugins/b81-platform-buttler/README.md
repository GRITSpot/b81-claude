# b81-platform-buttler

A Claude Code skill that turns Claude into a competent collaborator across BEAT81's three-repo platform ecosystem — `b81-platform`, `b81-kubernetes`, and `b81-workflows`. It routes requests to the correct repo, reads the in-repo source of truth before answering, enforces cross-repo rules, and hands off follow-up work in sibling repos with ready-to-paste prompts instead of reaching across boundaries.

## Install

The marketplace must already be added (see the repo-level [README](../../README.md)).

```
/plugin install b81-platform-buttler@b81-claude
```

The skill activates automatically whenever you're working in any of the three repos or your prompt mentions BEAT81 deployment concepts (ArgoCD, GitOps, `wave-app`, image promotion, etc.). No slash command to remember.

## What's in the box

A single skill: `b81-platform-buttler`. Its job is to make Claude reason about the platform the way the platform team does — repo-aware, doc-first, and disciplined about cross-repo boundaries.

## Features

### Repo-aware routing

Maps the request to the repo that owns the change, before any file is touched.

| Repo | Owns |
|---|---|
| `b81-kubernetes` | Cluster bootstrap, ArgoCD installation, shared Helm charts (`wave-app`, `app-of-apps`, `clickhouse`, `cloudsql-proxy`, `karpenter`), platform infra (ingress-nginx, cert-manager, monitoring, ClickHouse). Publishes charts to the OCI registry. |
| `b81-platform` | Application workload deployment configs consuming the published charts. Pulumi programs for app-owned GCP resources (IAM/Workload Identity, Pub/Sub, Cloud SQL users). |
| `b81-workflows` | Reusable GitHub Actions consumed by service repos: `docker-build.yaml`, `gitops-promote.yaml`, `argo-sync.yaml`, `slack-notify.yaml`, plus Asana PR-trigger workflows. |

Phrases like *"promote a tag"*, *"add a CronJob"*, *"bump wave-app"*, *"deploy to staging"*, *"fix my ArgoCD app"*, or *"why isn't the image syncing"* trigger the skill even when the repo isn't named.

### Source-of-truth-first answers

The skill blocks Claude from guessing at file paths, chart versions, environment lists, or service names. For every common question it points Claude at the file that actually has the answer:

| Question | File Claude reads first |
|---|---|
| Which services exist in which environment? | `b81-platform/argocd/applications/values.<env>.yaml` |
| What chart version is a service on? | `b81-platform/argocd/deployments/<env>/<service>/Chart.yaml` |
| What does a chart actually do? | `b81-kubernetes/helm/charts/<chart>/` |
| Inputs/outputs of a reusable workflow? | `b81-workflows/.github/workflows/<workflow>.yaml` |
| GCP resources for a service? | `b81-platform/pulumi/<service>/__main__.py` |

### Stay-in-one-repo discipline + paste-ready handoffs

By default Claude only edits files in the repo you're currently in. When a follow-up is needed in a sibling repo, it ends the response with a structured hand-off block: the exact files and edits, plus a self-contained prompt you can paste into a fresh Claude Code session in the target repo. No silent cross-repo writes, no context loss between sessions.

### Routing recipes for common tasks

Pre-baked playbooks for the requests that come up most often:

- **Add a new service / deploy a new app** → `b81-platform`, following `docs/adding-new-service.md` (App-of-Apps registration, `wave-app` Chart.yaml, values.yaml, optional Pulumi program). Falls back to `b81-kubernetes` only when the "app" is cluster infra.
- **Promote an image tag** → `b81-platform`, edit `argocd/deployments/<env>/<service>/values.yaml` under `wave-app.image.tag`. Automated path via `docker-build.yaml` → `gitops-promote.yaml` for service-repo CI.
- **Add a service to another environment** → `b81-platform`, with the explicit warning *not* to copy `values.yaml` verbatim (ingress, replicas, config differ — only `Chart.yaml` is safe to copy).
- **Bump a Helm chart** → `b81-kubernetes` only. Full `make bump-chart` → CHANGELOG → README → `make can-i-push` → PR flow, with consumer bumps in `b81-platform` handed off as a separate session.
- **Add or fix a reusable workflow** → `b81-workflows`, with workflow inventory + README + CHANGELOG updates.
- **Add GCP resources for a service** → `b81-platform/pulumi/<service>/`, including the `SKIP=pulumi-stack-configs-present` initial-commit dance so `pulumi-stack-init` generates per-environment KMS-encrypted stack configs.
- **Bootstrap a new cluster / touch ArgoCD itself** → `b81-kubernetes/argocd/bootstrap/`, gated on `@GRITSpot/tech-platform` involvement.
- **ArgoCD app isn't syncing** → starts at `b81-platform/docs/troubleshooting.md` with the usual suspects (YAML formatting, missing `values.yaml`, image tag missing in registry, stale `source.targetRevision`).

### Wave-app migration playbook

A first-class workflow for migrating `wave-*` services off the legacy pattern (`pulumi/index.ts` calling `infra.waveDeploy(...)` / `infra.waveCronJob(...)`) onto the `wave-app` Helm chart consumed via ArgoCD. Includes:

- The full **boundary table** showing what stays in the app repo's Pulumi (secrets, Pub/Sub topics) vs. moves to `b81-platform/argocd/deployments/<env>/<service>/values.yaml` (configMap, web/worker, cronjobs, migrations, volumes) vs. moves to `b81-platform/pulumi/<service>/` (Workload Identity SA + IAM bindings).
- The **env-var → configMap mapping recipe** that catches the most common bugs: resolving `infra.config.get(...)` against `Pulumi.<env>.yaml`, never migrating `secure:` entries into configMap, cross-checking against the runtime config loader, keeping Goose-only env vars in `migrations.<engine>.extraEnv` rather than the shared configMap.
- The **CronJob dormancy pattern** (real cron + `suspend: true` instead of the legacy "Feb 31" trick).
- A migration **checklist** to work through inside `b81-platform`, plus the handoff to a session in the app repo to remove the legacy `waveDeploy(...)` / `waveCronJob(...)` calls and stop running `pulumi up` against the deployment stack.
- A reference example (`result-service`) to compare against side-by-side.

### Cross-repo rule enforcement

Rules that hold across all three repos, regardless of what an in-repo doc says:

- **GPG signing in `b81-platform`** — when (and only when) Claude is about to commit there, it silently checks `commit.gpgsign`, `user.signingkey`, and the last commit's signature. If signing is set up, it just signs and stays quiet. If not, it stops and points at `docs/contributing.md`. CI image-promotion commits are the one exemption. Never `--no-gpg-sign` or `-c commit.gpgsign=false`.
- **No chart edits in `b81-platform`** — that repo is a consumer; charts are authored in `b81-kubernetes/helm/charts/` only.
- **Chart changes in `b81-kubernetes` require a version bump + CHANGELOG + README update in the same PR** — enforced by `scripts/ci/chart_version.sh`. Use `make bump-chart`, not hand edits.
- **Conventional Commits everywhere** — `type(scope): description`, imperative, lowercase, ≤72 chars, no trailing period.
- **Pre-commit must pass before push** — `pre-commit run --all-files` (`b81-platform`), `make can-i-push` (`b81-kubernetes`), `pre-commit` if installed (`b81-workflows`). No `--no-verify`.
- **Image promotion targets `b81-platform`** for application workloads — `gitops-promote.yaml` defaults `target_repo` to `b81-kubernetes` historically; consumers must override. A service repo on the default is a bug worth flagging.

### Constants reference

Stable values the skill treats as load-bearing — deviations are bugs, not new conventions:

- **Docker registry:** `europe-west3-docker.pkg.dev/b81-infra/b81-docker-registry/<service>`
- **OCI Helm registry:** `oci://europe-west3-docker.pkg.dev/b81-infra/b81-helm-registry`
- **Pulumi state backend:** `gs://b81-platform-pulumi-state` (only for `b81-platform/pulumi/`)
- **Environments:** `development`, `staging`, `production` (each is also the K8s namespace; not every service exists in every env)
- **GCP infra project:** `b81-infra` (registries, Workload Identity)
- **Per-env GCP projects:** `b81-dev-env`, `b81-staging-env`, `b81-production-env`
- **Default reusable-workflow runner:** `github-runner-platform`; `argo-sync.yaml` uses `github-runner-<environment>`

Service-specific values (chart versions, replica counts, ingress hostnames) are explicitly *not* memorized — Claude reads the actual `values.yaml` instead.

### Anti-pattern detection

The skill stops Claude (and pushes back on the user) when any of these appear:

- Editing both a chart in `b81-kubernetes/helm/charts/` and a consumer in `b81-platform/argocd/deployments/...` in the same change "to keep things in sync".
- Promoting a SHA to production without first promoting (or having promoted) it to staging.
- Adding a service to `argocd/applications/values.<env>.yaml` without creating the matching `argocd/deployments/<env>/<service>/` directory (or vice versa).
- Hand-editing `Pulumi.<env>.yaml` immediately after creating a Pulumi program instead of letting the `pulumi-stack-init` workflow generate it.
- Touching `argocd/bootstrap/` in `b81-kubernetes` without `@GRITSpot/tech-platform`.
- Reaching across into a sibling repo to "finish the job" instead of handing off.
- Producing an unsigned commit in `b81-platform` after the signing check failed.

## When the skill activates

Any of these will pull it in:

- You're working in `b81-platform`, `b81-kubernetes`, or `b81-workflows`.
- Your prompt mentions ArgoCD, GitOps, the `wave-app` or `app-of-apps` chart, `gitops-promote` / `docker-build` / `argo-sync` workflows, image promotion, adding or modifying a service, Pulumi stacks under `b81-platform`, or cluster infra (ingress-nginx, cert-manager, karpenter, ClickHouse).
- Your prompt names a recognizable BEAT81 verb: *"promote a tag"*, *"add a CronJob"*, *"bump wave-app"*, *"deploy to staging"*, *"fix my ArgoCD app"*, *"why isn't the image syncing"*.

## Layout

```
plugins/b81-platform-buttler/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── b81-platform-buttler/
│       └── SKILL.md
├── evals/
│   └── evals.json
└── eval-runs/
    └── iteration-1/benchmark.md
```

## Feedback

Open an issue or PR against [`GRITSpot/b81-claude`](https://github.com/GRITSpot/b81-claude). Concrete repro cases (the prompt that misrouted, what Claude did, what you expected) are the most useful kind.
