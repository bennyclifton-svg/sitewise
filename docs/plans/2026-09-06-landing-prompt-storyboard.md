# Landing prompt sequence and animation storyboard

Status: the PMP, Cost Plan and Program scenes are implemented locally in `frontend/public/landing.html`, 6 September 2026. The user approved extending the refined PMP treatment to the next two controls. This preview has not been deployed.

## Current review checkpoint

The refined shells and metallic perimeter are shared across all three scenes. The hero reads “Read. Organise. Update.” with “The New AI Powered Construction Management Platform.” beneath it. The landing automatically cycles Project Plan → Cost Plan → Program, holds each completed result for seven seconds, then makes a soft transition through an empty page and prompt. Select a scene in the navigation or footer to review it on its own indefinitely; Play all restarts the sequence. Pause/resume, replay, Show result, source selection and reduced-motion handling apply to every scene. The runtime is now `landing-sequence.js`; the earlier single-scene runtime has been replaced.

The Cost Plan now follows the supplied v9 screenshot and `CostPlanGrid.tsx` as one continuous spreadsheet, with the August 2026 month selector. Columns are Code, Category, Item, Budget, Approved Contract, Forecast Variations, Approved Variations, Forecast Final Cost, Budget Variance, Claimed to Date, This Month, Remaining and the row-action gutter. The table uses the app's 1,216 px minimum width, 60 px Code column, proportional Category/Item/money columns, 11 px text, 25 px rendered rows, shared cell borders, pale pink header, blue editable values and two decimal places. Subtotals span Category and Item. Horizontal scrolling stays inside this panel, including on mobile; tabs and column headings stay visible during vertical scrolling. The PMP retains its separate no-horizontal-scroll layout. Column headings and category placeholders fade in before 22 items and four subtotals build progressively. The centre document follows the current group; user scrolling pauses playback.

Visible v9 row codes, labels and budgets are transcribed from `Landing/1.3 Cost Plan.png`, including the $158,000 Electrical contract. The final three budgets are outside the supplied capture and remain unknown (a dash); the remaining standard construction labels come from the residential taxonomy. Unknown budgets propagate through budget, variance and remaining totals instead of being treated as zero. The captured v9 register supersedes the earlier adapted QS forecast presentation for this scene. Calculations follow `src/lib/cost-plan.ts`: forecast final cost is approved contract plus forecast and approved variations; budget variance is budget less forecast final cost; remaining is budget less claimed to date. Fees total $96,500; consultants total $225,500 budget, $158,000 approved/forecast and $67,500 variance. No standalone reconciliation cards or cost-basis sublines are added to the captured grid. The FS-26028 source excerpt continues to distinguish a proposal from the appointment recorded in the captured PMP.

The Program follows `ProgramGantt.tsx` and the newer chart attached to the user's programme browser comment. That attachment supersedes the dates in `Landing/1.4 Programme.png` and the earlier adapted QS baseline for this scene. Its 29 activities and milestones comprise 12 Planning, six Procurement and 11 Delivery rows, including the five fire-engineering rows. Activity, Start, Days and add fields use the app's 220 / 88 / 48 / 48 px layout (the last field includes the quiet action gutter), with 24 px rows, 10 px text, calendar icons, 16 px blue bars, endpoint marks, milestone diamonds and dark stage summaries. The axis defaults to Month and covers February 2025 through October 2026, with calendar-accurate grid spacing. It fits the available chart width, retaining the app's 80 px minimum timeline on very narrow screens; horizontal overflow remains inside the programme. The toolbar and header stay visible while the document scrolls.

The saved start dates and durations are transcribed from the new attachment without rescheduling them. Stage summaries are Planning 10 February 2025 / 219 days, Procurement 1 February 2025 / 138 days and Delivery 18 June 2025 / 501 days. The saved practical-completion milestone is 4 October 2026; the commissioning activity begins 7 October and lasts 25 days. Those are separate rows in the supplied saved state, not a newly reconciled baseline. Visible truncated activity names use their readable prefixes and existing project terminology. Global connector paths preserve cross-stage links, including mobilisation to site establishment and DA determination to earthworks; the five-day design lag is labelled. Fields fade in row by row, bars extend and dependency lines draw after their destination activity. Week, Month and Quarter change the axis; Fit to screen restores its horizontal position while retaining the selected scale. Add and export icons remain presentation controls. The earlier explanatory programme paragraph and final summary card have been removed to match the actual chart.

Validation: eighteen focused tests cover the existing PMP, progressive cost and activity generation, full column order, captured row codes and values, cost calculations and unknown budgets, all saved programme dates/durations, milestone count, dependencies and lag, mid-scene switching, looping, result holds, pause/offscreen behaviour, reduced motion and replay cleanup. Typecheck and lint also pass. Desktop and mobile browser checks confirm compact field alignment and contained scrolling. No production workbench, backend or email changes are part of this preview.

## PMP refinement history

The landing now uses the approved cream, flat composition with a clear document area and three separately rounded, elevated shells: left navigation, right repository and bottom composer. Icons come from the application's installed Lucide set: Settings2, FileText, HandCoins, GanttChart, ClipboardList, MessageSquare and Trash. Navigation labels are Project Profile, Project Plan, Cost Plan, Program and Procurement. The selected project uses the product's pale-blue surface/border and one downward chevron; Chats has the blue message bubble.

The latest browser comments are incorporated: the workspace banner and explanatory subtitle are removed, the navigation starts at the top of the product workspace beneath the hero, and the central panel carries the project name, address, Create PMP and Update PMP controls. Both buttons replay the corresponding local demonstration against the captured project content; they do not write to the live project.

The document now follows the actual Seven Hills PMP captures in `Landing/Plan 01.png` through `Landing/Plan 07.png`, checked against the eight briefing and planning records in `docs/demo-corpus/seven-hills/01-briefing-and-planning/`. Twelve sections include the expanded brief, 20-row consultant register (Demolition Consultant removed following review), accommodation schedule, all eight FFE rows, planning register, programme milestones, detailed construction cost allowances, procurement controls, risk and action tables, and citation key. The consultant register preserves the captured Flux Services appointment and $158,000 ex GST fee; its source citation remains blank because the captured project edit has no supporting document citation. The accommodation mix follows the brief's eight three-bedroom and four four-bedroom feasibility dwellings. Later eleven-dwelling project states are not mixed into this establishment plan.

Citation numbering matches the captured PMP: cost advice [1], client brief [2], handover email [3], deposited plan [4], title search [5], planning advice [6], ground report [7] and pre-DA record [8]. The repository presents these eight sources and the resulting plan in one list.

`landing-pmp.js` implements only the first scene. While the request appears in word groups, the central panel above the composer is empty and the console has a blue perimeter. The completed prompt holds for 2.4 seconds (two seconds longer than the previous revision), then the outline fades as the report starts to appear. After that hold, the project header appears, then twelve blue section headings fade in sequentially at 220ms intervals, each over 420ms, with pale thinking shimmers. All headings are present before content begins populating; the shimmer highlight uses an 8% blue mix. The eight source files highlight in a shuffled order, accumulating selection as each is read. All source highlights remain while the sections populate. On completion the source selections clear and the new plan joins the same document list, highlighted as the result. The scene takes roughly 12.2 seconds, then holds the completed plan indefinitely for inspection. Pause/resume, replay, source citations and Show result work locally. Offscreen/hidden-page playback pauses; reduced motion and absent JavaScript show the completed document.

Next review: assess this working PMP scene's timing and shell fidelity, then extend the agreed treatment to Cost Plan and Program. The full nine-scene cycle remains a later stage. Production prompt progression and hero-line changes across scenes will follow when those scenes are present.

Validation: nine focused behaviour tests pass, as do frontend typecheck and lint. Browser checks cover the empty typing state, three shells, full consultant and FFE registers, citation placement and readable 14px document text. All PMP tables fit the document width without horizontal scrolling. The consultant citation column reserves 64px; below 480px of available table width, register rows stack into labelled fields with citations aligned right. The legacy `landing-prompt.js` is no longer loaded by the landing page. No backend or email work is included in this pass.

### Earlier mockup review

The user requested a visible design checkpoint before committing to the full landing implementation. The conversation contains a separate mockup with three opening scenes (PMP, Cost Plan and Programme), each offering **Populate** and **Result** states and a short, manually started motion sample. The separate Framework stage has been removed following review. The remaining six scenes have not been built.

Proposed layout: a compact centred headline above a wide, flat workspace. Use the actual product cream `#fefcf5`, quiet warm-grey framing and the existing blue action colour. Remove the cadastral map from this direction. Reuse Satoshi Light, Hanken Grotesk and the current SiteWise logo. The mockup's design controls allow comparison with a warm-grey page, a dark workspace, larger document text and different motion durations.

All document titles, headings, table values, dates and citations are browser-rendered selectable text. Essential document/repository text starts at 14px and reflows without scaling the entire workspace. At narrow widths, navigation moves above the artefact and the repository moves below it. The first-look preview uses source-backed synthetic Seven Hills values, while programme spans are explicitly schematic planning assumptions.

The PMP opens directly with all eleven blue section headings and a subtle shimmering line beneath each. Result playback fills the existing sections progressively in normal document flow: sections grow and push later headings below the document viewport. Keep that viewport stable and scrollable; do not shrink the content or substitute an abbreviated result that drops the remaining sections. Citations occupy a consistent right-hand column, including summary tables, paragraphs and the citation key. Source references remain clickable.

The application shell now shows the SiteWise logo, selected project, Project profile, Project plan, Cost plan, Program and Procurement, with Chats below. The document repository uses compact single-line rows: short document title, revision, category and bin icon. It has no date sublines. Source excerpts open only when a document or citation is selected. The composer includes Fast/Thorough toggles, a microphone and an up-arrow send button. Send replays the local demonstration; microphone, deletion, profile and procurement controls are presentation-only at this checkpoint.

Cost and programme scenes begin with their groups and shimmering placeholders, followed by populated results. The headline retains its restrained upward move and fade; playback stops after the selected scene. This is a layout and motion study, not a recording of live agent execution.

Review in stages: settle the overall composition, colour and legibility; implement and review one PMP scene in the actual landing; then extend the agreed treatment to cost/programme and the remaining prompts. Do not start the full nine-scene implementation before the user has reviewed this checkpoint.

Verified for this revision: six scene states, progressive expansion without replacing the PMP, right-column citation placement, repository row structure, full navigation, response-mode selection, send/replay, playback cancellation and design-control updates. Browser layout inspection covers desktop and narrow screens. No production components were changed during this revision.

Content note for the later document-issue scene: the Seven Hills establishment brief explicitly says **no basement**. Use a compatible drawing set when staging that scene, or revise its prompt with the user, rather than presenting basement documents as part of this project's evidence.

## Direction

Start by establishing the project controls: **project management plan → cost plan → programme**. Then move through consultant procurement, trade procurement, tender comparison, drawing issue, invoices and reviewed changes. Remove the consultant-appointment example.

The opening three scenes establish scope and quality requirements, cost and time, using the same project context. Keep their records visibly related: the project plan supplies the scope, cost rows reflect that scope, and programme stages follow its delivery sequence. There is no need to enumerate every output in the prompt itself.

The project profile is the briefing source for the first example. Consultant reports provide supporting evidence. Programme and cost-plan assumptions remain distinguishable from received advice or proposals.

## Revised prompt list

| Order | Example | Exact proposed prompt |
| --- | --- | --- |
| 1 | Project management plan | Read the project profile and consultant reports. Draft the project management plan. |
| 2 | Cost plan | Build the cost plan from the project plan and received proposals. |
| 3 | Programme | Build the programme from the project plan, linking design, approvals, procurement and construction. |
| 4 | Consultant procurement | Draft consultant RFPs from the project plan, with scopes, deliverables and submission requirements. |
| 5 | Trade procurement | Prepare the civil tender pack and shortlist three local firms. |
| 6 | Tender comparison | Compare the builder tenders. Explain price differences and recommend next steps. |
| 7 | Document issue | Select the current basement drawings and prepare a transmittal to the head contractor. |
| 8 | Invoices | Process this month's uploaded invoices and allocate them to the cost plan. |
| 9 | Reviewed changes | Apply the reviewed change advice to the cost plan, programme and project management plan. |

Drawing issue sits after tender comparison and before invoice administration. The final example applies already-reviewed cost and time advice. It does not imply that the agent measures changed drawings and independently derives a cost uplift or delay.

Keep the fixed order. Each scene needs its own prepared starting state, coherent with the stage of the synthetic project. The opening controls may be schematic; do not populate them with later appointment or construction-change evidence before that information is available.

## Corresponding visuals

| Example | Sources and main-panel action | Final readable state |
| --- | --- | --- |
| Project management plan | Highlight the profile and relevant consultant reports. Reveal the PMP structure, then populate the project summary and a selected scope, requirements or risk-control section. Add the draft to the repository. | A useful section of the plan with a source citation. Quality is expressed through actual requirements and controls in the plan. |
| Cost plan | Carry the project scope into Fees, Consultants, Construction and Contingency groups. Populate quoted figures and labelled allowances. Calculate totals once. | Four to six readable rows, their cost basis, and the project total. |
| Programme | Use the same project plan to reveal Planning, Procurement and Delivery groups. Build activity bars, then their supported finish-to-start links and milestones. | Six to eight legible activities and the key milestones. |
| Consultant procurement | Reveal discipline-specific RFP drafts for architecture, planning, structural, civil/stormwater and building services. Open the civil RFP at its project-specific scope and deliverables. | One readable RFP plus the other drafts in the repository. |
| Trade procurement | Select the current scope, drawings and specification. Assemble the civil RFT draft, then populate three candidate firms with their research references. | A prepared pack and potential firms for review. |
| Tender comparison | Select three complete submissions. Populate a compact comparison; highlight a material scope difference and its documented price consequence. Reveal the corresponding next-step recommendation. | Three comparable columns, one consequential finding and the source reference. |
| Document issue | Select the matching current basement drawings across disciplines. Populate the transmittal's document numbers, titles and revisions. | The selected documents beside the prepared transmittal. |
| Invoices | Highlight the eligible invoices. Populate representative register rows, show the Cost Plan allocations and update the claimed-to-date roll-up. | A populated invoice register and its matching cost position. |
| Reviewed changes | Highlight reviewed QS and programme advice. Apply the evidenced forecast change, move the linked programme activities, then update the relevant PMP control. | Updated controls with the advice still attached. |

One central artefact is the focus at a time. Keep the repository as supporting context and match the active navigation item to the displayed artefact. A highlighted source or generated document is sufficient; the whole repository need not move.

## Opening three scenes

The PMP opens with its blue headings already present and a thinking shimmer beneath each. Populate meaningful content directly under those headings, expanding the document naturally, and finish with the top sections readable. There is no separate framework reveal. Do not simulate typing a complete long document.

Carry a recognisable scope item into the cost plan and then into the programme. That continuity explains the connection among the controls without adding more words to the console. Use an item supported across the staged project records; do not create a new relationship solely for the animation.

Suggested timing for each scene:

| Phase | Approximate duration | Behaviour |
| --- | --- | --- |
| Prompt | 1.5–2.5 seconds | Reveal the concise request in word groups. |
| Work | 3–5 seconds | Highlight the source, then show the requested artefact being created or updated. |
| Result | 4–5 seconds | Hold the completed prompt and readable result; stop substantive motion. |
| Transition | About 0.5 seconds | The prompt rises slightly and fades; the next starting state appears. |

Nine scenes would take roughly 90–120 seconds, depending on their individual timing. Visitors should understand the first three controls within the opening half-minute; each later scene must also stand on its own. Provide pause and example selection so seeing a particular capability never requires waiting for the whole loop.

The current script holds prompts for 1.5 seconds and has no corresponding result animation. The longer holds and coordinated result playback belong to the animation implementation, not the small layout change made in this pass.

## Layout

Applied locally:

- Removed the workspace's perspective rotation, transform origin and preserve-3D styling. The workspace now has a flat presentation in CSS.
- Reduced the desktop console minimum height from 11.8 to 8.25 container-width units, a reduction of approximately 30% in its minimum-height setting.
- Reduced the console's internal vertical padding and gap without reducing the text size.
- Updated the landing stylesheet reference so the changed styles can be fetched.

The actual console height can still grow with its content, especially while the original longer prompts remain in the script. Narrow-screen rules continue to allow content-driven height.

For the animation phase, retire the persistent prompt-history lane and use that space for the active artefact. Keep the current prompt visible through execution and the result hold, then lift and fade it once. On mobile, give the prompt and artefact the available width rather than reducing a complete desktop workspace to unreadable scale.

The outer device, navigation and background should stay still. Motion belongs to the project information: rows populate, values change, bars extend, links connect and documents become available.

## Existing images and what they provide

The `Landing` folder contains useful full-interface references. Inspected in this pass:

| File | Use |
| --- | --- |
| `Landing/1.2 Plan.png` | Full light-mode PMP, including the centre panel, source citations and right-hand repository. |
| `Landing/1.3 Cost Plan.png` | Full light-mode Cost Plan and its column structure. |
| `Landing/1.4 Programme.png` | Full light-mode programme, bars, dependencies and milestones. |
| `Landing/chat invoices.png` | Invoice prompt bar only; it does not show the processed invoice register. |

Previously inspected assets include `frontend/public/landing-assets/product/cost-dark.png`, `programme-dark.png` and `chat-console-dark.png`. These provide the dark presentation already used by the landing. The light screenshots can guide structure and content; keep the final animation's theme consistent rather than changing theme between examples.

Other available files include `Landing/1.5 Procurement.png`, `Landing/dark procurement.png`, `Landing/Plan 01.png` through `Plan 07.png`, and several `chat …` crops. Inspect those before requesting replacements. A filename alone does not establish that it contains the completed output.

There is enough material to design the opening plan/cost/programme sequence. Before implementing later scenes, identify or capture a readable invoice register, completed tender comparison/report, representative consultant RFP and transmittal. Additional screenshots should match the final theme and synthetic project state. Preserve supplied originals and do not edit captured figures or statuses to simulate successful product execution.

## Capability boundaries

- Invoices update canonical invoice allocations and derived claimed totals. Booking must not imply payment or change the original budget/approved contract.
- Consultant RFPs and transmittals are prepared drafts. Issuing correspondence is a separate action.
- Tender recommendations must use the validated comparison route and controlled report language. Distinguish clarification steps from an appointment decision.
- Potential firms are research leads. Their presence in a shortlist does not establish capacity, availability or willingness to tender.
- The trade workflow exists in the MCP bridge, but `start_trade_procurement` was absent from the inspected direct Pi tool allowlist. Verify actual runtime exposure before public animation of this end-to-end prompt.
- Programme tools support linked scheduling; do not introduce critical-path, resource-optimisation or contractual-entitlement claims.
- The reviewed-change scene can use the Seven Hills QS/programme advice with its fictional $68,500 forecast variation and ten-calendar-day adjustment. The application must produce the demonstrated result from the prepared state. Figures come from supporting advice, not an inferred quantity take-off from revised drawings.
- Keep the Council inbox RFI and EOT assessment examples outside this sequence until their end-to-end behaviour is validated. Email reliability was identified by the user as unfinished.

## Implementation and verification

Build the later result animations in the existing landing page using HTML, CSS, SVG and the browser's Web Animations API. No new animation dependency is required. Reuse the product's visual structure and use a single controller to coordinate each prompt, source highlight, artefact change and hold.

Provide reduced-motion static results, accessible prompt/result text, pause/resume and example selection. Pause offscreen and when the tab is hidden. Keep a visible synthetic-demonstration label and do not portray animation timing as measured live execution speed.

The initial implementation target is now **PMP, Cost Plan and Programme**, in that order. The appointment scene and the earlier change-first recommendation are removed.

This pass is based on current source and supplied images. Fresh browser visual verification remains outstanding because the browser rejected local-file access in this session. The layout edits do not constitute validation of live project workflows.

Local checks: lint passed; the layout detector returned no findings; the edited HTML/CSS passed the whitespace check. Typecheck was blocked by an unrelated string/template-literal type mismatch in `frontend/src/pages/ProcurementReviewPage.tsx:52`, which this pass did not modify.

Relevant implementation evidence: `frontend/public/landing.html`; `frontend/public/landing-assets/landing-story.css`; `frontend/public/landing-assets/landing-prompt.js`; `backend/app/agent/workspace_instructions.py`; `backend/app/agent/pi_process.py`; `backend/app/mcp_bridge/server.py`; `data/tender/report_language.yaml`; and `docs/demo-corpus/seven-hills/`.
