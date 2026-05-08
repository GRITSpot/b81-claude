---
name: b81-platform-buttler
description: BEAT81 platform expert covering the three-repo ecosystem - b81-platform (app deployment configs + Pulumi GCP resources), b81-workflows (reusable GitHub Actions), and b81-kubernetes (cluster infra + shared Helm charts + ArgoCD bootstrap). Use whenever the user is working in any of these repos, mentions BEAT81 deployments, ArgoCD, GitOps, the wave-app or app-of-apps chart, gitops-promote/docker-build/argo-sync workflows, image promotion, adding or modifying a service, Pulumi stacks under b81-platform, or cluster infra like ingress-nginx/cert-manager/karpenter/ClickHouse. Trigger even if the user does not name the repo - phrases like "promote a tag", "add a CronJob", "bump wave-app", "deploy to staging", "fix my ArgoCD app", "why isn't the image syncing" all need this skill. The skill routes the request to the correct repo, points at the right in-repo CLAUDE.md or docs/ guide, edits files only in the current repo by default and hands off cross-repo follow-ups via paste-ready prompts, and enforces cross-repo rules (no chart edits in b81-platform, version bump + CHANGELOG required for b81-kubernetes chart changes, Conventional Commits everywhere, verify GPG signing before committing in b81-platform).
---

# BEAT81 Platform Buttler

You are working with BEAT81's three-repo platform ecosystem. The single biggest mistake you can make is to answer from memory or guess at file paths, chart versions, environment lists, or service names. **The repos themselves are the source of truth.** This skill's job is to route you to the right repo and the right doc, then enforce the rules that span all three.

## The three repos

| Repo | Owns | Read for details |
|---|---|---|
| `b81-kubernetes` | Cluster bootstrap, ArgoCD installation, shared Helm charts (`wave-app`, `app-of-apps`, `clickhouse`, `cloudsql-proxy`, `karpenter`), platform-level infra apps (ingress-nginx, cert-manager, monitoring, ClickHouse). Publishes charts to the OCI registry. | `b81-kubernetes/CLAUDE.md`, `b81-kubernetes/README.md` |
| `b81-platform` | Application workload deployment configs (admin-next, feedback-service, api-gateway, etc.) consuming the published charts. Pulumi programs for app-owned GCP resources (IAM/Workload Identity, Pub/Sub, Cloud SQL users). | `b81-platform/CLAUDE.md`, `b81-platform/README.md`, `b81-platform/docs/*.md` |
| `b81-workflows` | Reusable GitHub Actions workflows consumed by service repos: `docker-build.yaml`, `gitops-promote.yaml`, `argo-sync.yaml`, `slack-notify.yaml`, plus standalone Asana PR-trigger workflows. | `b81-workflows/CLAUDE.md`, `b81-workflows/README.md` |

## How they connect (read this before any cross-repo decision)

```
b81-kubernetes (bootstrap + cluster infra)
  └── installs ArgoCD on the cluster
        ├── platform-apps  ──▶ reads b81-kubernetes itself (cluster infra, ArgoCD project: "platform")
        └── wave-apps      ──▶ reads b81-platform        (app workloads,    ArgoCD project: "applications")
              └── app-of-apps chart in b81-platform/argocd/applications/
                    generates one ArgoCD Application per service
                      └── each renders b81-platform/argocd/deployments/<env>/<service>/

b81-workflows is consumed by service repos (not by the platform/k8s repos):
  service-repo CI ──▶ docker-build.yaml ──▶ gitops-promote.yaml (opens PR via the GitHub Git
                                            API for a GitHub-signed commit, bumping image
                                            tag in the platform repo)
                                       ──▶ argo-sync.yaml (forces ArgoCD sync)
```

Both `b81-platform` and `b81-kubernetes` consume Helm charts from the same OCI registry (`oci://europe-west3-docker.pkg.dev/b81-infra/b81-helm-registry`). **Charts are authored in `b81-kubernetes` only.** `b81-platform` is a consumer — never modify charts there.

## Read first, answer second

Before recommending a change to any of these repos, read the relevant in-repo file. The repos evolve fast and this skill is not a substitute for them.

| Question | Read this |
|---|---|
| Which services exist in which environment? | `b81-platform/argocd/applications/values.<env>.yaml` (and the table in its `CLAUDE.md`) |
| What chart version is a service on? | `b81-platform/argocd/deployments/<env>/<service>/Chart.yaml` |
| What does a chart actually do? | `b81-kubernetes/helm/charts/<chart>/` (template + values + README) |
| Inputs/outputs of a reusable workflow? | `b81-workflows/.github/workflows/<workflow>.yaml` (and its README section) |
| What CI runs on PRs in `b81-kubernetes`? | `b81-kubernetes/scripts/ci/*.sh` and `.github/workflows/` |
| GCP resources for a service? | `b81-platform/pulumi/<service>/__main__.py` |

If you don't have access to the repo (e.g., user pasted a snippet), say so and ask the user to share the relevant file rather than guessing.

## Stay in one repo at a time — hand off, don't reach across

Each of these three repos is its own Claude Code session, its own commit, its own PR. **By default, only edit files in the repo the user is currently in.** Even when a task requires a follow-up in a sibling repo (chart bump → consumer bump, new service → CI promotion), finish the work in the current repo and hand off the rest. Don't make the cross-repo edit yourself unless the user explicitly says so ("go ahead and edit `b81-platform` too", "do it all in one shot").

How to figure out the current repo: it's the git root of the working directory (`git rev-parse --show-toplevel`). If a change you're about to make would land outside that path, stop.

When a follow-up in another repo is needed, end your response with a **hand-off block** in exactly this format — no extra prose, no "context" sections, no restated rationale:

```
─── Follow-up needed in <other-repo> ───

Files to change there:
- <path>: <what to change and why> (one line each)

Prompt to paste in a <other-repo> Claude Code session:
"""
Use the b81-platform-buttler skill.

<2–4 sentences: what just shipped (repo + branch/PR), what version/tag is
now available, what this session must do, what it must NOT do.>

Stay in this repo only.
"""
```

The pasted prompt is self-contained — assume the next session has zero context. Keep it under ~10 lines; if you're writing more, you're re-deriving work the next session will redo anyway.

## Routing common requests

Match the user's request to the repo before doing anything else.

### "Add a new service" / "Deploy a new app"

Almost always **`b81-platform`** — these are application workloads. Follow `b81-platform/docs/adding-new-service.md` (App-of-Apps registration, `wave-app` Chart.yaml, `values.yaml` template by service tier, optional Pulumi program).

It is **`b81-kubernetes`** only if the new "app" is cluster infrastructure (e.g., a new operator, monitoring stack, ingress controller). Use `b81-kubernetes/README.md` "Adding a New Application" + the chart authoring flow.

If the request is ambiguous, ask one question: "Is this an application workload (admin-next/feedback-service style) or cluster infrastructure (ingress, monitoring, operators)?"

### "Promote an image tag" / "Deploy this SHA"

**`b81-platform`**. Edit `argocd/deployments/<env>/<service>/values.yaml` under `wave-app.image.tag`. Commit with `feat(<service>): promote image tag to <sha>`. Full procedure in `b81-platform/docs/promoting-image-tags.md`.

In service repos this is automated by chaining `docker-build.yaml` → `gitops-promote.yaml` from `b81-workflows` — point users at `b81-workflows/README.md` for the consumer recipe.

### "Add a service to another environment"

**`b81-platform`**. Follow `b81-platform/docs/adding-service-to-environment.md`. Do NOT copy `values.yaml` verbatim across environments — ingress hostnames, replica counts, and config differ. Copy `Chart.yaml` only.

### "Bump a Helm chart" / "Modify wave-app / app-of-apps / clickhouse"

**`b81-kubernetes`** only. Workflow:
1. Edit the chart in `helm/charts/<chart-name>/`.
2. `make bump-chart <chart-name> [--minor|--major|<exact-version>]`.
3. Update `helm/charts/<chart-name>/CHANGELOG.md` and `README.md` to describe the change.
4. `make can-i-push` (runs validation, version checks, pre-commit).
5. Open PR. CI enforces version bump and changelog update.
6. On merge to `main`, CI packages and pushes to the OCI registry.

Then, if consumers need the new version, **separately** bump the chart version in `b81-platform/argocd/deployments/<env>/<service>/Chart.yaml` (or in `b81-kubernetes/argocd/deployments/<env>/<infra-app>/Chart.yaml` for infra apps). If you're working in `b81-kubernetes`, do not edit the consumer files yourself — use the hand-off block to tell the user (or a fresh Claude Code session in `b81-platform`) what to change and provide a ready-to-paste prompt. Only edit `b81-platform` from this session if the user explicitly tells you to.

### "Add a reusable workflow" / "Fix a CI workflow used by other repos"

**`b81-workflows`**. Add as a `workflow_call` reusable workflow under `.github/workflows/`. Update `CLAUDE.md` workflow inventory and `README.md`. Test via `test-workflows.yaml` if applicable. Bump entry in `CHANGELOG.md`. Consumers pin via `@main` or a release tag.

### "Add GCP resources for a service" / "I need a service account / Pub/Sub topic / Cloud SQL user"

**`b81-platform/pulumi/<service>/`**. Three files: `Pulumi.yaml` (backend `gs://b81-platform-pulumi-state`), `__main__.py`, `requirements.txt`. Commit with `SKIP=pulumi-stack-configs-present` on the initial commit so the `pulumi-stack-init` workflow can generate the per-environment stack configs and KMS-encrypt them automatically. Procedure in `b81-platform/docs/adding-new-service.md` Step 6.

KMS key ring naming differs per environment (historical artefact) — let the workflow handle it; do not copy `Pulumi.<env>.yaml` from another service.

### "Migrate a wave-app to ArgoCD" / "Move this service off the legacy Pulumi-based deploy"

This is the migration of a `wave-*` service repo (e.g. `wave-result-service`, `wave-feedback-service`) from the legacy pattern — where the app repo's `pulumi/index.ts` calls `infra.waveDeploy(...)` / `infra.waveCronJob(...)` directly to render Deployments/CronJobs — to the new pattern, where `b81-platform/argocd/deployments/<env>/<service>/values.yaml` declares the deployment via the `wave-app` Helm chart.

**Reference example:** `result-service` is fully migrated. Compare side-by-side as your template:
- Legacy source: `wave-result-service/pulumi/index.ts` + `wave-result-service/pulumi/Pulumi.services.wave-result.<env>.yaml`
- New deployment config: `b81-platform/argocd/deployments/<env>/result-service/values.yaml`
- New GCP IAM (split out): `b81-platform/pulumi/result-service/__main__.py`

**Boundary — what moves where:**

| What | Stayed in app repo Pulumi | Moved to `b81-platform/argocd/deployments/<env>/<service>/values.yaml` | Moved to `b81-platform/pulumi/<service>/` |
|---|---|---|---|
| App env vars (the dict passed to `waveSetConfigMap`) | — | `wave-app.configMap.data.*` | — |
| `waveSetSecretMap` / `waveSetArgoSecretMap` (DATABASE_URL, CLICKHOUSE_PASSWORD, …) | yes (still owned here) | referenced via `wave.configs: true` (auto-envFrom) and `migrations.<engine>.extraEnvFrom` | — |
| `infra.waveDeploy({ deploymentScript: web, ... })` | — | `wave-app.web.{enabled,replicas,resources,...}` | — |
| `infra.waveDeploy({ deploymentScript: worker, ... })` | — | `wave-app.worker.{enabled,replicas,resources,extraVolumes,extraVolumeMounts}` | — |
| `infra.waveCronJob({ cronJobName, schedule, args })` | — | `wave-app.cronjobs.<name>.{schedule,args,suspend}` | — |
| Goose / Alembic / `npm run migrate` jobs | — | `wave-app.migrations.{postgres,clickhouse}` | — |
| `addVolumes` / `addVolumeMounts` (e.g. `pubsub-credentials`, GCP service account JSON) | — | per-process `extraVolumes` / `extraVolumeMounts` | — |
| Pub/Sub topics, subscriptions | yes (still owned here) | — | — |
| Workload Identity SA + IAM role bindings (Pub/Sub publisher/subscriber, GCS objectAdmin) | — | — | `GcpK8sWorkloadIdentity(...)` (see `b81-platform/pulumi/result-service/__main__.py` for the canonical pattern) |

**The env var → configMap mapping is the part that bites people most.** Do it carefully:

1. Open the app repo's `pulumi/index.ts` (or `__main__.py`). Find the dict passed to `waveSetConfigMap({ data: ... })` (sometimes named `serviceConfig`, `configData`, etc.).
2. For each entry: hardcoded literals (e.g. `GOOSE_DRIVER: 'clickhouse'`) copy verbatim. Calls like `infra.config.get('FOO')` must be resolved by reading `pulumi/Pulumi.<env>.yaml` for the literal value — they are not derivable from the TypeScript alone.
3. Cross-check spellings against the app's runtime config loader (`config/default.js` + `config/custom-environment-variables.json` for Node services, `settings.py` for Python). The runtime is what actually reads these names.
4. Anything marked `secure:` in `Pulumi.<env>.yaml` is a **secret** and must NOT go in `configMap.data`. Those continue to be managed by `waveSetSecretMap` in the app repo's Pulumi and arrive in pods automatically when `wave.configs: true` is set.
5. Don't over-migrate: `GOOSE_DRIVER` / `GOOSE_COMMAND` etc. that exist only to drive a Goose migration CronJob belong in `migrations.clickhouse.extraEnv`, not the shared configMap.
6. Migration is not a verbatim freeze — values can be adjusted intentionally during the cutover (e.g. `result-service` flipped `ENABLE_CUSTOMER_PROGRESS` from `'true'` to `'false'`). Flag any deliberate overrides explicitly so the reviewer notices.

**CronJob dormant pattern:** Legacy Pulumi keeps "manual-trigger-only" CronJobs alive by setting an impossible date (e.g. `schedule: '0 * 31 2 *'` — Feb 31). The new pattern uses a real cron + `suspend: true`, which is admission-valid and obvious to readers (see `result-service` `cronjobs.restore-powermeter-readings`).

**Cross-repo handoffs this migration requires:**

- Edits to **`b81-platform`** only from this session (per the "Stay in one repo at a time" rule).
- Hand off to a session in the **app repo** (e.g. `wave-result-service`) with a paste-ready prompt to: remove the `waveDeploy(...)` and `waveCronJob(...)` calls now that they live in the platform repo, while keeping secret/topic creation in place; update the app repo's CI to stop running `pulumi up` against the deployment stack.
- If the app needs new GCP IAM that didn't exist before (Workload Identity SA, Pub/Sub role bindings, bucket access), that goes in **`b81-platform/pulumi/<service>/__main__.py`** — same session as the values.yaml work, since both live in `b81-platform`. Use `result-service`'s Pulumi as the template.

**Migration checklist (work in `b81-platform`):**

- [ ] Read app-repo `pulumi/index.ts` (or `__main__.py`) — list every key in the `waveSetConfigMap` data dict and every `waveSetSecretMap` key.
- [ ] Read app-repo `pulumi/Pulumi.<env>.yaml` — resolve each `infra.config.get(...)` to its literal value; note `secure:` entries (secrets, not configMap).
- [ ] Cross-check key names against the app's runtime config loader.
- [ ] Add the App-of-Apps registration in `argocd/applications/values.<env>.yaml`.
- [ ] Create `argocd/deployments/<env>/<service>/Chart.yaml` referencing the `wave-app` version peer services on this env use (e.g. backends in staging are on `0.2.0`).
- [ ] Create `argocd/deployments/<env>/<service>/values.yaml` translating per the boundary table above. Use `result-service`'s values.yaml as a structural reference.
- [ ] If new GCP IAM is needed: add `b81-platform/pulumi/<service>/` (Pulumi.yaml + `__main__.py` + requirements.txt). Initial commit uses `SKIP=pulumi-stack-configs-present`.
- [ ] Verify in staging first. ArgoCD Healthy + Synced + the workload running both web and worker. Don't decommission the legacy Pulumi-driven deployment until the ArgoCD one is proven healthy on the same env.
- [ ] Hand off the app-repo cleanup as a separate session.

**App-repo side of the migration (work in `wave-<service>` repo).** This is what you do when the user is in the app repo, not the platform repo. There are up to three phases — handle whichever the user is currently on.

Reference: `wave-result-service` is the canonical migrated example. Read its `.github/workflows/` and `pulumi/index.ts` (post-migration state) before editing.

**Phase 1 — Add the GitHub Actions build + promote pipeline.** Replaces the legacy `cloudbuild.yaml` (gcr.io push + direct `kubectl set image`). Without this the new ArgoCD app sits in `ImagePullBackOff` because the image only exists in the old registry.

- Add `.github/workflows/build.yaml` (or equivalent) that calls `GRITSpot/b81-workflows/.github/workflows/docker-build.yaml@main`. It pushes to `europe-west3-docker.pkg.dev/b81-infra/b81-docker-registry/<service>:<sha>`.
- Chain `gitops-promote.yaml@main` after the build. **Must** pass `target_repo: GRITSpot/b81-platform` (the workflow's default is `b81-kubernetes` — wrong for app workloads). It opens a PR in `b81-platform` bumping `wave-app.image.tag` in the relevant `argocd/deployments/<env>/<service>/values.yaml`.
- Optionally chain `argo-sync.yaml@main` to force a sync after the promote PR merges.
- **First-run trigger.** On the initial commit that adds this workflow, include the migration feature branch in the `on.push.branches` filter (e.g. `branches: [main, feat/ID-1353/migrate-mail-service-argo]`). Otherwise the workflow only fires on `main` pushes and you have no built image to point ArgoCD at while the migration PR is still open. After the PR merges, drop the feature-branch entry in a follow-up commit. (Note: this is the workflow's `on:` trigger — not `runs-on:`, which selects the runner.)
- Use `wave-result-service/.github/workflows/` as the structural template — copy the file layout and adjust the service name + image path. Don't re-derive the workflow inputs from the `b81-workflows` README; the result-service version is the working contract.
- Delete the legacy `cloudbuild.yaml` and any `kubectl set image` / `kubectl apply` steps **only** after the new pipeline has produced an image in the new registry that ArgoCD successfully pulled in staging.

**Phase 2 — Bump `@gritspot/wave-lib-pulumi` to `>= 2.0.13`.** Older versions still ship the legacy `waveDeploy(...)` helpers but lack the toggles needed to cleanly disable the deployment-rendering side while keeping `waveSetSecretMap` + Pub/Sub creation alive. `2.0.13` is the hard floor for partial-removal mode — anything below will not work.

- Edit `pulumi/package.json` — set `"@gritspot/wave-lib-pulumi": "^2.0.13"` (or whatever caret bound matches the team's pinning convention; check `wave-result-service/pulumi/package.json` for the current canonical pin).
- Run `npm install` (or `yarn` / `pnpm` per the repo's lockfile) inside `pulumi/` to refresh the lockfile.
- Commit lockfile + `package.json` together. Conventional Commits: `chore(pulumi): bump wave-lib-pulumi to ^2.0.13 for argocd migration`.
- Don't bundle this with the deploy-removal commit — keep the bump as its own commit so any regression is bisectable.

**Phase 3 — Remove the legacy Pulumi deploy.** Only do this *after* the user confirms the new ArgoCD deployment is `Healthy + Synced` in **at least staging** (production cutover usually wants a longer soak). Until then, leaving the legacy deploy running means rollback is `git revert` on the platform repo's deployment + `pulumi up` on the app repo, not a server-side scramble.

Edits in `pulumi/index.ts` (or `__main__.py` for Python services):

- **Remove:**
  - `waveSetConfigMap({ data: ... })` — the configMap now lives in `b81-platform/argocd/deployments/<env>/<service>/values.yaml` under `wave-app.configMap.data`. Cross-check the platform repo's values.yaml has the full key set before deleting here.
  - `waveDeploy({ deploymentScript: 'web', ... })` and `waveDeploy({ deploymentScript: 'worker', ... })` — Deployments are now rendered by the `wave-app` chart.
  - `waveCronJob(...)` calls **only** for cronjobs that have been migrated to `wave-app.cronjobs.<name>` in the platform values.yaml. Cronjobs that need a non-default image (e.g. `google/cloud-sdk` for `gcloud pubsub publish`) can't yet use `wave-app.cronjobs` — leave those calls in place and flag them for a follow-up app-code refactor.
- **Keep:**
  - `waveSetSecretMap(...)` / `waveSetArgoSecretMap(...)` — secrets stay owned in the app repo's Pulumi. `wave.configs: true` in the platform values.yaml auto-injects them via `envFrom`.
  - Pub/Sub topic + subscription creation. ArgoCD doesn't manage GCP resources.
  - Anything related to GCS bucket creation, Cloud SQL ownership, or other GCP resources the app provisions for itself.
  - Any IAM / Workload Identity bindings the app currently owns. (New IAM that didn't exist pre-migration goes in `b81-platform/pulumi/<service>/__main__.py`, but pre-existing bindings can stay where they are unless the user explicitly wants them moved.)
- **Stack cleanup:** the deployment stack outputs (e.g. `deploymentName`, `serviceUrl`) referenced by other consumers no longer exist. Grep for `pulumi stack output` references in the app repo's CI before removing — usually there are none, but worth checking.
- **CI cleanup:** remove any GitHub Actions / cloudbuild steps that ran `pulumi up` against the deployment stack. The Pulumi program now only manages secrets + Pub/Sub, and those are typically applied manually or via a much narrower CI job.
- Commit per phase: `refactor(pulumi): remove legacy waveDeploy now in argocd` + `refactor(pulumi): remove waveSetConfigMap now in argocd values`. Don't combine into one giant "rip out the deploy" commit — partial rollbacks are easier when each removal is its own commit.

If the user is uncertain whether they're ready for Phase 3, ask: "Has the new ArgoCD deployment shown `Healthy + Synced` in <env> for at least one full deploy cycle?" If no, defer Phase 3 and ship Phases 1–2 first.

### "ArgoCD app isn't syncing" / "My deploy isn't showing up"

Start with `b81-platform/docs/troubleshooting.md`. Most common causes: YAML formatting (run `pre-commit run --all-files` locally), missing `values.yaml`, image tag doesn't exist in the registry, or a stale `source.targetRevision` branch override left behind from testing.

### "Bootstrap a new cluster" / "ArgoCD itself"

**`b81-kubernetes`** — `argocd/bootstrap/`. This is platform-team-only territory; defer to `@GRITSpot/tech-platform`.

## Cross-repo rules (enforce these regardless of in-repo docs)

**In `b81-platform`, signed commits are mandatory for human contributors — but verify before raising it.** Don't preemptively lecture about GPG. When (and only when) you're about to produce a commit in `b81-platform`, silently check the user's setup first:

```bash
git config --get commit.gpgsign       # expect: true
git config --get user.signingkey      # expect: a key ID
git log --show-signature -1           # expect: "Good signature from ..."
```

If signing is already configured (`commit.gpgsign=true`, signing key set, recent commits show a good signature), just use `git commit -S` and continue without commenting on signing — the user already has it set up and doesn't need the reminder. Only when the check fails: stop, surface the specific gap (no signing key set, signing disabled, or last commit unsigned), point at `b81-platform/docs/contributing.md` for the setup, and do not produce an unsigned commit. CI image-promotion commits are the one exemption. Never bypass with `--no-gpg-sign` or `-c commit.gpgsign=false`.

**Never modify Helm charts inside `b81-platform`.** That repo is a consumer; charts are authored in `b81-kubernetes/helm/charts/`. If a chart change is needed, the work happens in `b81-kubernetes`, then `b81-platform`'s `Chart.yaml` is bumped to the new version in a separate PR.

**`b81-kubernetes` chart changes require version bump + CHANGELOG + README updates in the same PR.** CI enforces this via `scripts/ci/chart_version.sh`. Use `make bump-chart` rather than editing `Chart.yaml` by hand — the script also seeds the changelog entry.

**Conventional Commits everywhere.** Format: `type(scope): description`. Types: `feat` (new service / new env config / new CronJob / image promotion), `fix` (correcting a broken config), `chore` (maintenance, deps). Scope is the service or area (`feedback-service`, `staging`, `argocd`, `wave-app`). Description: imperative, lowercase, ≤72 chars total, no trailing period. See `b81-platform/docs/contributing.md`.

**Pre-commit must pass before push.**
- `b81-platform`: `pre-commit run --all-files`
- `b81-kubernetes`: `make can-i-push` (runs version checks + validator + pre-commit)
- `b81-workflows`: no Makefile, just `pre-commit` if hooks are installed

Don't `--no-verify` past failing hooks. The hooks are cheap and CI runs the same checks; bypassing locally only delays the failure.

**Image promotion target is `b81-platform`, not `b81-kubernetes`.** The `gitops-promote.yaml` workflow in `b81-workflows` defaults `target_repo: GRITSpot/b81-kubernetes` historically — for application workloads (admin-next, feedback-service, etc.), consumers must override `target_repo: GRITSpot/b81-platform`. If a service repo is using the default, that's a bug worth flagging. Only cluster-infra image promotions belong in `b81-kubernetes`.

## Constants you can rely on

These are stable across the ecosystem. If you see a deviation, treat it as a bug to investigate, not as a new convention.

- **Docker registry:** `europe-west3-docker.pkg.dev/b81-infra/b81-docker-registry/<service>`
- **OCI Helm registry:** `oci://europe-west3-docker.pkg.dev/b81-infra/b81-helm-registry`
- **Pulumi state backend:** `gs://b81-platform-pulumi-state` (only for `b81-platform/pulumi/`)
- **Environments:** `development`, `staging`, `production` (each is also the K8s namespace by convention; not every service exists in every environment)
- **GCP infra project:** `b81-infra` (registries, Workload Identity)
- **Per-env GCP projects:** `b81-dev-env`, `b81-staging-env`, `b81-production-env`
- **Default reusable-workflow runner:** `github-runner-platform`; `argo-sync.yaml` uses `github-runner-<environment>`

Do **not** memorize service-specific values like chart versions, replica counts, or ingress hostnames — those drift. Read the actual `values.yaml`.

## Anti-patterns to push back on

If a user (or your own draft response) does any of these, stop and reconsider:

- Editing both a chart in `b81-kubernetes/helm/charts/` AND `b81-platform/argocd/deployments/...` in the same change "to keep things in sync." That couples the producer and consumer; ship the chart change first, let it publish, then bump the consumer.
- Promoting an image directly to production without first promoting (or having promoted) the same SHA to staging.
- Adding a service to `argocd/applications/values.<env>.yaml` without creating the corresponding `argocd/deployments/<env>/<service>/` directory (or vice versa) — both are required and the orphan check on the platform repo / ArgoCD will surface the inconsistency.
- Hand-editing `Pulumi.<env>.yaml` files immediately after creating a Pulumi program. Let the `pulumi-stack-init` CI workflow generate them on the initial commit (use `SKIP=pulumi-stack-configs-present` to bypass the pre-commit count check on that one commit only).
- Touching `argocd/bootstrap/` in `b81-kubernetes` without `@GRITSpot/tech-platform` involvement.
- Reaching across into another repo to "finish the job" without being asked. If the work needs follow-up in `b81-platform`, `b81-kubernetes`, or `b81-workflows` other than the one the user is currently in, hand off with a paste-ready prompt rather than editing files there yourself.
- Producing an unsigned commit in `b81-platform` after the check showed signing wasn't configured. If GPG "didn't work for some reason," fix the setup; don't bypass with `--no-verify` or `--no-gpg-sign`.

## Reporting back to the user

Keep completion summaries tight. The user is asking *what to do next*, not *what just happened* — lead with the action, not the recap.

Required structure (in this order, omit empty sections):

1. **Next step** — one line. The single thing the user should do right now (`git push`, open PR, hand off, verify in staging).
2. **Done** — 3–5 bullets max. One line per file or logical change. Don't reproduce the full diff.
3. **Blockers** — only if they exist. One line each: what's broken + what unblocks it.
4. **Hand-off block** — only if cross-repo work remains. Use the template above verbatim; don't expand it with prose.

Anti-patterns:

- **Reproducing reference tables from this skill in the report.** The boundary-mapping table (legacy → new location) is *for you to consult while doing the work*, not to paste back. The user knows the mapping; just bullet which items moved.
- **The same content twice in different formats** (e.g. a bullet list followed by a wide table of the same data). Pick one — bullets.
- **"What's done" before "what's next".** Lead with the next step. Recap is supporting detail, not the headline.
- **Meta-commentary** like "the buttler skill flagged this" or "per the cross-repo rules". Apply the rules silently; don't narrate them.
- **Restating the user's request** before answering it.

If the response is longer than ~30 lines and isn't a hand-off prompt, cut it.

## When in doubt

Open the relevant repo's `CLAUDE.md` and follow it. This skill exists to point you at the right repo and the right doc, and to remind you of the rules that span all three — it does not replace the in-repo guidance.
