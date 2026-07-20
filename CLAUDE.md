# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**csl-devanagari** is a Sanskrit Lexicon **converter** repository — part of the Cologne Digital Sanskrit Lexicon (CDSL) infrastructure.

## Repo Category

`converter` — see the [tooling runbook](https://github.com/sanskrit-lexicon/csl-observatory/blob/main/runbook/cologne-tooling-runbook.md) for category-specific conventions.

## GitHub Issue Conventions

This repository uses the **Cologne tooling-repo taxonomy**. All issues must have:
- **Exactly one type label** (9 options)
- **Exactly one severity label** (4 levels)
- **One milestone** (5 options)

### Type Labels
- `bug` — Code defect (wrong output, broken contract)
- `feature` — Net-new capability
- `enhancement` — Improvement to existing capability
- `performance` — Speed, memory, throughput optimization
- `tech-debt` — Refactoring, cleanup, dependency updates
- `security` — CVE, auth issue, credential exposure
- `documentation` — Prose docs, API docs, comments
- `infrastructure` — CI/CD, deploy, data pipelines, build tooling
- `question` — Research, proposals, open discussions

### Severity Labels
- `trivial` — Cosmetic, < 1 hour
- `minor` — Single function/component
- `major` — Multiple files, design decision
- `critical` — Blocks users, data loss/security CVE

### Milestones
- **API Stability** — performance, security, regressions
- **User Experience** — bugs, features, enhancements
- **Data Quality** — data-pipeline issues, integrity
- **Developer Experience** — tech-debt, infrastructure, docs
- **Community** — questions, proposals, discussions

## Cross-Repo Coordination

The org-level project [Tooling Roadmap](https://github.com/orgs/sanskrit-lexicon/projects/9) tracks tool work across all repositories.

## Operational hazard notes

Destructive-risk facts for this repo (do-not-rerun scripts, decoys, traps) are
registered centrally in an org-private hub
([Uprava DANGER_FACTS.md](https://github.com/gasyoun/Uprava/blob/main/DANGER_FACTS.md),
org members only); the public-safe subset is mirrored in the generated block of
[AGENTS.md](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/AGENTS.md). Check them
before running anything that writes.
