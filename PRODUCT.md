# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS frontend served by the FastAPI app (Vercel CDN promotes `public/`); Python FastAPI backend on Vercel serverless; PostgreSQL via asyncpg pooled connections (Vercel Postgres or Neon, `sslmode=require`, cold-start retry built in). No Node build step.

## Users

People who share links: developers, marketers, and support staff, working in a browser at a desk. Their job is to turn a long URL into a shareable code, hand it out, and later read how often and from where it was clicked.

## Product Purpose

Snap turns any long URL into a short, shareable link (for example `https://snap.app/Ab3xYz7`) and tracks every click — count, timestamp, and referrer — surfacing the winners on a dashboard. Success means a user can shorten, share, and read real click data within seconds.

## Positioning

A URL shortener whose redirect and analytics run on the same serverless deployment: click tracking never blocks the redirect, and every number on the dashboard comes from the stored click stream in PostgreSQL — no local files, no stubs.

## Operating Context

Used entirely in a browser. The home page is the tool itself: paste a URL, get a code. The dashboard is a ledger of links ranked by clicks, with a per-link daily timeline and recent-click detail. Codes are random base62 strings and links are permanent. Referrers are captured from the HTTP `Referer` header; direct visits are recorded as `direct`.

## Capabilities and Constraints

- Shorten a URL (http/https only, scheme auto-defaulted to `https://`, whitespace rejected).
- Redirect `GET /{code}` to the target with a 302; each click records count, timestamp, and referrer.
- Analytics: per-link stats, daily click timeline, dashboard of top links and recent clicks.
- Serverless constraint: no local filesystem persistence; all state lives in PostgreSQL.
- Out of scope: authentication, custom slugs, link expiry, bulk import.

## Brand Commitments

Name: "Snap". No pre-existing logo or assets. Visual direction is invented for this build (a paper-and-ink ledger world with punched-tape telemetry details). No invented testimonials, customers, or benchmarks.

## Evidence on Hand

No pre-existing content; all dashboard content is generated at runtime from real stored clicks.

## Product Principles

1. The redirect is sacred: analytics must never delay or break it.
2. Every number on screen comes from a database row, never a hardcoded stub.
3. Collision-safety is a database guarantee (`ON CONFLICT`), not a coin flip.
4. One code, one permanent link; no surprises on the wire.
5. The home page is the tool: shortening happens in the first viewport.

## Accessibility & Inclusion

Target WCAG 2.1 AA: contrast ≥ 4.5:1 for body text, keyboard-operable controls, visible focus rings, `aria-live` for asynchronous results.

## Deployment

Target: Vercel serverless, one project hosting frontend and backend together. Reasoning: the backend is stateless request/response only — short-lived handlers, no background tasks, no local file persistence, no long-running processes — so serverless functions fit, and the serverless-compatible PostgreSQL driver (asyncpg pool against Vercel Postgres or Neon) is used instead of a local SQLite file that would not survive between invocations. Local development runs the identical code path against a local PostgreSQL instance.
