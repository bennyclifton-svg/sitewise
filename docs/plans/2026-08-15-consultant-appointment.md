# Consultant Appointment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When the user accepts a fee-proposal recommendation (or nominates a firm and sum), SiteWise adopts that proposal: confirm the fee, write it to the Cost Plan Approved Contract (committed) for the already-classified discipline, and mark the PMP Consultants register as appointed.

**Architecture:** Do not ask Pi to hunt artefact schema. Add a single mutation tool, `appoint_consultant`, that resolves the fee proposal from a selected/named document or from firm + discipline + nominated fee, then updates typed Cost Plan state, shared consultant facts, and the PMP Consultants table in Python.

**Tech Stack:** FastAPI MCP tool, typed Cost Plan (`committed` = workbook "Approved Contract"), shared project knowledge (`kind=consultant`), PMP Consultants register patch.

---

## Why the agent gets stuck

1. Instructions tell Pi to `get_cost_plan` / `get_artefact_blocks` then construct operations. That is a schema hunt.
2. Residential Cost Plan scaffold has no Town Planner or Civil row. PMP house roster does. Matching fails.
3. Typed field is `committed`; the workbook column is **Approved Contract**. The agent looks for "awarded contract sum".
4. `refresh_cost_plan` refuses to choose among competing same-discipline proposals, and its extractor only knows four kinds in a different fee-proposal format.
5. "Accept that recommendation" / "appoint Verity" may not even mint mutation tools.

## Behaviour

- Discipline comes from document metadata first (`Town Planning`, `Architectural`, …). Do not rematch from filename when metadata is present.
- Fee comes from the proposal total (ex GST) unless the user nominates a sum.
- Cost Plan: set `committed` on the matching consultant/fee row; add the row if the scaffold omitted it.
- PMP: set Firm, Fee, Status=`Appointed` on the Consultants register row for that discipline.
- One tool call. Pi must not inspect repository files or invent item keys.
