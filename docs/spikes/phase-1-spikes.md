# Phase 1 spikes (2026-11-15)

## 1. fastembed RAM and speed (measured locally)
- Model: `BAAI/bge-small-en-v1.5`, 384 dimensions, ONNX, 1 thread.
- RSS went from 19 MB to 231 MB after loading and 255 MB after embedding 256 texts. That's about **+236 MB**.
- Load time was 11.5 s on the first run, which includes downloading the model. It's faster once cached.
- Throughput: about **154 texts/s** on one thread.

**Decision.** Run local embeddings in the **worker only**, not the api.
- Load the model lazily on first use.
- Size the worker container at about 1 GB RAM within the Northflank Sandbox budget.
- Bake the model into the image at build time (Phase 3), so cold starts don't download it again.
- Gemini embeddings remain plan B.

## 2. Free magic-link email path
| Option | Result |
|---|---|
| Supabase Auth built-in email | **Not viable for public users.** It only delivers to project team members and is rate-limited; custom SMTP is required for production. ([docs](https://supabase.com/docs/guides/auth/auth-smtp), [changelog](https://supabase.com/changelog/29370-supabase-auth-changes-to-default-email-provider)) |
| Resend free | Needs a verified domain to send to arbitrary recipients. |
| **Brevo free** | ~300 emails/day, no card ([Brevo SMTP page](https://www.brevo.com/free-smtp-server/)); individual sender addresses can be verified without a domain (third-party guide, unverified). |

**Caveat.** Sending "From: someone@gmail.com" through a third party fails DMARC alignment at Gmail and Yahoo, so mail will land in spam or be rejected. Real deliverability needs a domain with SPF and DKIM records.

**Decision.**
1. **Telegram Login is the primary sign-in**, with no email dependency.
2. Email magic links ship in Phase 2 via the **Brevo HTTP API**.
3. We get a **free domain** for the sender, either an `is-a.dev` subdomain (GitHub PR) or `eu.org` (slow manual approval). This needs a user action, listed in `docs/runbooks/deploy.md`.
4. Until the domain exists, email login stays behind a feature flag.

## 3. Northflank Sandbox: Redis and pgvector
- [Pricing](https://northflank.com/pricing) says, quoted: "2 services, 2 jobs, and 1 database", "Up to $20/mo of resources", "No card needed", "Always on, no sleeping".
- PostgreSQL, MySQL, MongoDB and Redis are listed as addon types. The Sandbox plan allows 1 addon.
- **Decision:** use the single addon slot for **Redis**. Postgres stays on **Neon** (pgvector 0.8.x confirmed by the earlier research).
- Per-service CPU and RAM limits aren't published. We'll confirm the instance sizes in the dashboard when deploying.

## 4. Tauri v2 + Python sidecar feasibility
On this machine:
- Rust `stable-x86_64-pc-windows-msvc`
- Visual Studio Build Tools 2026 (MSVC)
- WebView2 157

All Tauri v2 prerequisites are present.

Sidecar approach, per the Tauri docs checked during planning:
- PyInstaller exe declared under `bundle.externalBin`, with the target-triple suffix in its name.
- Permission from the shell plugin.
- Updater signed with our own key pair, no paid certificate.

**Decision:** feasible. The full hello-world build moves to the start of Phase 6, where the desktop app is built. It isn't on the critical path for Phases 2–5.
