// UI structure: CostPlanGrid / ProgramGantt and Landing/1.3–1.4 captures.
// Visible v9 rows are transcribed from Landing/1.3 Cost Plan.png.
// Budgets below the capture are unknown; never turn an uncaptured value into zero.
// Row shape: code, item, budget, approved contract, forecast variations,
// approved variations, claimed to date, this month. Optional amounts default to zero.
export const costGroups = [
  { id: 'fees', title: 'Fees and charges', rows: [
    [1, 'Architect-PM architect / PM fee', 60000],
    [2, 'DA and CC authority fees', 15000],
    [3, 'BASIX certificate fee', 500],
    [4, 'Sydney Water / infrastructure', 1000],
    [5, 'Levies and statutory', 20000],
  ] },
  { id: 'consultant-fees', title: 'Consultants', rows: [
    [8, 'Structural engineer', 24000],
    [9, 'Geotechnical engineer', 7500],
    [10, 'Surveyor', 9000],
    [11, 'Hydraulic / wastewater', 12000],
    [12, 'BASIX / energy assessor', 5000],
    [13, 'Principal certifier', 10000],
    [28, 'Electrical', 158000, 158000],
  ] },
  { id: 'construction', title: 'Construction', rows: [
    [14, 'Preliminaries', 970500],
    [15, 'Siteworks and demolition', 776500],
    [16, 'Footings and slab', 485000],
    [17, 'Framing and roof', 1649500],
    [18, 'External envelope and lockup', 1649500],
    [19, 'Internal linings and joinery', 1067500],
    [20, 'Kitchen and bathrooms', 582000],
    [21, 'Building services', null],
    [22, 'Finishes and external works', null],
  ] },
  { id: 'contingency', title: 'Contingency', rows: [
    [27, 'Design development contingency', null],
  ] },
];

// Same calculation as src/lib/cost-plan.ts: lineRollup.
export function costRollup([, , budget, approved = 0, forecastVariations = 0, approvedVariations = 0, claimed = 0, thisMonth = 0]) {
  const forecast = approved + forecastVariations + approvedVariations;
  return { budget, approved, forecastVariations, approvedVariations, forecast,
    variance: budget == null ? null : budget - forecast, claimed, thisMonth,
    remaining: budget == null ? null : budget - claimed };
}

export function costTotals(group) {
  const rows = group.rows.map(costRollup);
  return Object.fromEntries(Object.keys(rows[0]).map(key => [key,
    rows.some(row => row[key] == null) ? null : rows.reduce((sum, row) => sum + row[key], 0),
  ]));
}

export const projectCostTotals = costTotals({ rows: costGroups.flatMap(group => group.rows) });

// Saved programme supplied with the browser comment, September 2026.
// Preserve its dates and durations rather than rescheduling it to the earlier QS brief.
// Row shape: key, activity, start, duration in calendar days.
export const programmeGroups = [
  { id: 'planning', title: 'Planning', start: '2025-02-10', days: 219, rows: [
    ['establish', 'Project establishment and consultant appointments', '2025-02-10', 47],
    ['concept', 'Concept and schematic design', '2025-03-29', 52],
    ['da-docs', 'Design development and DA documentation', '2025-05-25', 30],
    ['assessment', 'DA assessment – Blacktown City Council', '2025-06-24', 85],
    ['consultants-complete', 'Consultant appointments complete', '2025-03-29', 0],
    ['pre-da', 'Pre-DA meeting', '2025-04-09', 0],
    ['da-approval', 'DA determination', '2025-09-17', 0],
    ['fire-appoint', 'Appoint fire engineer', '2025-02-10', 46],
    ['fire-performance', 'Prepare fire engineering performance solution', '2025-02-10', 109],
    ['fire-brigade', 'Engage with brigade rider / fire engineering review', '2025-05-30', 41],
    ['fire-authority', 'Complete NSW policy and authority requirements', '2025-07-10', 55],
    ['fire-complete', 'Fire engineering package complete and accepted', '2025-02-10', 0],
  ] },
  { id: 'procurement', title: 'Procurement', start: '2025-02-01', days: 138, rows: [
    ['cc-docs', 'Construction documentation and CC', '2025-02-01', 56],
    ['builder-tender', 'Construct-only builder tender (AS 4000)', '2025-03-29', 29],
    ['evaluate', 'Tender evaluation and contract award', '2025-04-27', 28],
    ['mobilise', 'Mobilisation to construction start', '2025-05-25', 24],
    ['tender-close', 'Builder tender close', '2025-04-24', 0],
    ['award', 'Contract award', '2025-06-19', 0],
  ] },
  { id: 'delivery', title: 'Delivery', start: '2025-06-18', days: 501, rows: [
    ['site', 'Site establishment and preliminaries', '2025-06-18', 14],
    ['earthworks', 'Demolition, earthworks and remediation', '2025-09-17', 35],
    ['foundations', 'Substructure and foundations', '2025-10-22', 42],
    ['structure', 'Structure and upper floors', '2025-12-03', 105],
    ['envelope', 'Envelope, roofing, windows and doors', '2026-03-18', 56],
    ['services', 'Hydraulic, electrical and mechanical services', '2026-05-13', 42],
    ['fitout', 'Internal finishes and fitout', '2026-06-24', 105],
    ['external', 'External works, OSD, landscaping and subdivision', '2026-06-24', 95],
    ['commission', 'Commissioning, defects and practical completion', '2026-10-07', 25],
    ['start', 'Construction start', '2026-04-13', 0],
    ['pc', 'Practical completion', '2026-10-04', 0],
  ] },
];

// Visible connectors in the supplied chart. The 5-day design lag is retained.
export const programmeDependencies = [
  ['establish', 'concept'], ['concept', 'da-docs', 5], ['da-docs', 'assessment'],
  ['establish', 'consultants-complete'], ['fire-performance', 'fire-brigade'],
  ['fire-brigade', 'fire-authority'], ['fire-authority', 'earthworks'],
  ['da-approval', 'earthworks'], ['cc-docs', 'builder-tender'],
  ['builder-tender', 'evaluate'], ['evaluate', 'mobilise'], ['mobilise', 'site'],
  ['site', 'earthworks'], ['earthworks', 'foundations'], ['foundations', 'structure'],
  ['structure', 'envelope'], ['envelope', 'services'], ['services', 'fitout'],
  ['services', 'external'], ['fitout', 'commission'], ['external', 'commission'],
];
export const programmeStart = '2025-02-01';
export const programmeEnd = '2026-11-01';
export const dayNumber = value => Date.parse(`${value}T00:00:00Z`) / 86400000;
export const addDays = (value, days) => new Date((dayNumber(value) + days) * 86400000).toISOString().slice(0, 10);
export const duration = row => row[3];
export const finish = row => addDays(row[2], duration(row));
export const position = value => (dayNumber(value) - dayNumber(programmeStart)) / (dayNumber(programmeEnd) - dayNumber(programmeStart)) * 100;
