---
name: readme-standardizer
description: Audit, verify, and rewrite README.md files into a standardized 5-section format (Overview, How It Works, Architecture, Tech Stack, Getting Started) grounded in the actual codebase, while migrating detailed documentation into docs/ using standardized reference templates.
---

# Standardized README & Docs Cleanup Skill

When invoked, inspect the target repository and rewrite `README.md` into the exact five-section layout specified below. Every version number, architectural component, and file link must be verified against the repository before writing.

## Step 1: Codebase Grounding (Mandatory)
Before modifying any files, inspect the repository to gather accurate data:
1. **Dependencies & Versions:** Read manifest and lockfiles (`package.json`, `pyproject.toml`, `requirements.txt`, `Cargo.toml`, `go.mod`, `pom.xml`) to extract exact framework and library versions.
2. **Containers & Infrastructure:** Inspect `Dockerfile`, `docker-compose.yml`, and Kubernetes/Terraform manifests to identify exact Docker base images and tags.
3. **System Flow & Architecture:** Trace entry points, services, databases, queues, and external APIs to map how data flows through the system.
4. **Docs Verification:** Check `docs/` to see if detailed architecture and getting-started Markdown files already exist. Note their exact relative paths.

## Step 2: Required `README.md` Structure
Format `README.md` using these exact five sections in order. Do not add extra top-level sections unless explicitly requested.

### `# <Project Name>`
Include a crisp one-sentence tagline and any valid repository badges right under the title.

### `## Overview`
* Write 2–3 concise sentences explaining what the project does, who it is for, and the core problem it solves.
* Keep it high-level and free of setup commands or deep implementation jargon.

### `## How It Works`
* Explain the end-to-end runtime workflow or lifecycle in 3–5 numbered steps or bullet points.
* Focus on inputs, processing stages, and outputs so a reader understands the operational flow quickly.

### `## Architecture`
* Provide a brief 2–3 sentence summary of the system design (e.g., monolith, microservices, event-driven pipeline).
* Include a clean, high-level **Mermaid diagram** (` ```mermaid `) illustrating major components and data flow.
* End the section with a direct Markdown link to the detailed architecture file in `docs/` (e.g., `For deep-dive component specs and data schemas, see [Detailed Architecture](docs/architecture.md).`).

### `## Tech Stack`
* Present a clean Markdown table or categorized list detailing the exact **Frameworks**, **Core Libraries**, **Databases/Storage**, and **Docker Images** used.
* Always include explicit version numbers or image tags verified in Step 1 (e.g., `Python 3.12`, `FastAPI 0.115.0`, `postgres:16-alpine`).

### `## Getting Started`
* Provide a quick review of prerequisites (e.g., Docker, Node version) and the minimal 2–3 commands needed to run the project locally.
* End the section with a direct Markdown link to the full setup guide in `docs/` (e.g., `For environment variables, local troubleshooting, and deployment steps, see the [Getting Started Guide](docs/getting-started.md).`).

## Step 3: Migrating & Creating `docs/` Sub-Pages
* **Content Migration:** Do not delete deep technical explanations, environment variable tables, or multi-step setup guides removed from `README.md`. Migrate them into `docs/architecture.md` and `docs/getting-started.md`.
* **Use Reference Templates:** Whenever creating or standardizing `docs/architecture.md` or `docs/getting-started.md`, read `references/architecture-template.md` and `references/getting-started-template.md` first and follow their exact section layouts.
* **No Broken Links:** Ensure every link in `README.md` resolves to a valid file on disk.

## Step 4: Summary Report
After updating files, output a concise summary in chat listing:
1. Verified versions and Docker tags added to `Tech Stack`.
2. Sections migrated out of `README.md` into `docs/`.
3. Any configuration gaps or ambiguities found in the codebase.
