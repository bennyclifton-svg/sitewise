---
title: Cockpit Refresh Optimization
date: 2026-06-08
status: implemented
---

# Cockpit Refresh Optimization

## Goal

Make the project cockpit useful quickly after a browser refresh by reducing request fan-out, payload size, and avoidable backend work.

## Non-goals

- Do not change Create PMP generation.
- Do not change Create Cost Plan generation.
- Do not change the hybrid document compiler path.
- Do not change retrieval quality or workflow output contracts.

## Implemented

- Added lightweight timing visibility for protected request handling and cockpit bootstrap.
- Added one cockpit bootstrap endpoint for first-screen project data.
- Return evidence and draft summaries on initial load.
- Lazy-load full evidence content and draft markdown only when those views are opened.
- Keep chat loading behind first dashboard paint.
- Added dashboard-oriented indexes for common project/evidence/platform knowledge queries.

## Target

The workbench shell should render from one lightweight backend response. Larger panels can continue loading after the shell is visible.
