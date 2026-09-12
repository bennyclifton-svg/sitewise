import { rfpDrafts } from './landing-rfp-data.js';

const icon = paths => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
const fileIcon = icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h6"/>');
const plusIcon = icon('<path d="M12 5v14M5 12h14"/>');
const backIcon = icon('<path d="m12 19-7-7 7-7M5 12h14"/>');
const syncIcon = icon('<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 7a7 7 0 0 1 11.6-2L20 8M4 16l2.3 3A7 7 0 0 0 18 17"/>');
const names = { architect: 'Architect', 'civil-stormwater': 'Civil / stormwater engineer', electrical: 'Electrical engineer', hydraulic: 'Hydraulic engineer' };
const rows = [['architect', 'Architect'], ['planning', 'Town planning'], ['structural', 'Structural'], ['civil-stormwater', names['civil-stormwater']], ['electrical', 'Electrical'], ['hydraulic', 'Hydraulic']];
const draftOrder = ['architect', 'electrical', 'hydraulic', 'civil-stormwater'];

function rfpMarkup(key, draft) {
  return `<article class="sw-rfp" data-rfp="${key}" hidden aria-label="${names[key]} RFP draft">
    <h3>${draft.title}</h3>
    ${draft.sections.map((section, index) => `<section class="sw-control-section sw-rfp-section" data-rfp-section="${index}" data-section-title="${section.title}">
      <h4 class="sw-section-title">${section.title}</h4><div class="sw-thinking" aria-hidden="true"></div>
      <div class="sw-section-reveal"><div>${section.blocks.map(block => `<div class="sw-rfp-block">${block}</div>`).join('')}</div></div>
    </section>`).join('')}
  </article>`;
}

function repositoryEntry(root, key, label, category, title, excerpt) {
  const entry = root.querySelector('[data-output]').cloneNode(true);
  entry.removeAttribute('data-output'); entry.dataset.file = key; entry.dataset.procurementFile = '';
  entry.dataset.sourceTitle = title; entry.dataset.sourceExcerpt = excerpt;
  const button = entry.querySelector('.sw-source');
  button.removeAttribute('data-open-generated'); button.dataset.source = key; button.textContent = label;
  entry.querySelector('.sw-repo-rev').textContent = category === 'RFP' ? '1' : '—';
  entry.querySelector('.sw-repo-rev').removeAttribute('aria-label');
  entry.querySelector('.sw-repo-category').textContent = category;
  entry.querySelector('.sw-bin').setAttribute('aria-label', `Remove ${label} (preview)`);
  entry.hidden = true; root.querySelector('.sw-sources').append(entry);
  return entry;
}

export function createProcurementScene(root) {
  const files = Object.fromEntries(draftOrder.map(key => {
    const entry = repositoryEntry(root, key === 'civil-stormwater' ? 'procurement' : `rfp-${key}`, `${names[key].replace(' engineer', '')} RFP`, 'RFP', `${names[key]} · RFP v1`, 'Saved Seven Hills Townhouse consultant RFP draft.');
    entry.querySelector('button').dataset.openRfp = key;
    return [key, entry];
  }));
  const references = [
    ['civil-osd', 'OSD tank details', 'C-201 · Below ground OSD tank plan, sections and outlet details', 'The saved RFP requires review, adoption, revision or supersession of the existing below-ground OSD tank and outlet details, including structural and hydraulic interfaces.'],
    ['civil-notes', 'Civil notes', 'C-001 · Civil Notes, Legend and Abbreviations', 'Included in the saved RFP transmittal at revision C.'],
    ['civil-drainage', 'Stormwater plan', 'C-200 · Stormwater Drainage Plan', 'The saved RFP requires coordination with the current stormwater drainage plan and resolution of clashes and documentation gaps.'],
  ].map(([key, label, title, excerpt]) => repositoryEntry(root, key, label, 'Civil', title, excerpt));
  const definition = {
    label: 'Procurement', title: 'Consultant procurement',
    create: 'Draft consultant RFPs from the project plan, with scopes, deliverables and submission requirements.',
    update: 'Review the project plan and civil documents. Update the consultant RFPs.',
    createLabel: 'Create RFPs', updateLabel: 'Update RFPs',
    sources: ['pmp', 'brief', 'planning', 'preda', 'civil-osd', 'civil-notes', 'civil-drainage'],
    output: false,
    markup: `<div data-procurement-register>
      <div class="sw-procurement-tools"><button type="button" disabled>${plusIcon}Add discipline</button><button type="button" disabled>${syncIcon}Sync</button></div>
      <div class="sw-procurement-grid-wrap"><table class="sw-procurement-grid" aria-label="Consultant procurement register">
        <colgroup><col class="sw-discipline-column"><col><col><col><col class="sw-status-column"><col class="sw-row-actions-column"></colgroup>
        <thead><tr>${['Discipline', 'Firm 1', 'Firm 2', 'Firm 3', 'Status'].map(label => `<th scope="col"><span data-column-heading>${label}${label === 'Firm 3' ? plusIcon : ''}</span></th>`).join('')}<th scope="col" aria-label="Actions"></th></tr></thead>
        <tbody class="sw-control-section" data-section-title="Consultants"><tr class="sw-procurement-group"><th colspan="6" scope="rowgroup">Consultants<div class="sw-thinking" aria-hidden="true"></div></th></tr>
        ${rows.map(([key, label]) => `<tr data-build-row="${key}"><th scope="row"><div class="sw-procurement-cell">${label}</div></th>${[1, 2, 3].map(() => '<td><div class="sw-procurement-cell sw-empty-firm">Add firm</div></td>').join('')}<td><div class="sw-procurement-cell sw-procurement-status"><div class="sw-status-segments" aria-label="Not issued"><span>Issued</span><span>Submitted</span><span>Rec.</span><span>Contract</span></div>${rfpDrafts[key] ? `<button type="button" class="sw-rfp-open" data-open-rfp="${key}" data-draft-pending disabled aria-label="Open ${label} RFP draft" title="Open ${label} RFP draft">${fileIcon}</button>` : ''}</div></td><td><span class="sw-procurement-cell sw-row-menu" aria-hidden="true">···</span></td></tr>`).join('')}</tbody>
      </table></div>
      <p class="sw-procurement-ready" data-procurement-ready hidden>4 RFP drafts ready for review</p>
    </div>
    <div data-procurement-reader hidden><div class="sw-rfp-toolbar"><button type="button" data-back-procurement>${backIcon}Procurement</button><span>Draft · v1</span></div>${rfpMarkup('civil-stormwater', rfpDrafts['civil-stormwater'])}</div>`,
    reset() {
      root.querySelectorAll('[data-procurement-file]').forEach(entry => { entry.hidden = true; });
      references.forEach(entry => { entry.hidden = false; });
      definition.content.removeAttribute('data-procurement-exit');
      definition.content.querySelector('[data-procurement-register]').hidden = false;
      definition.content.querySelector('[data-procurement-reader]').hidden = true;
      definition.content.querySelector('[data-procurement-ready]').hidden = true;
      definition.content.querySelectorAll('[data-open-rfp]').forEach(button => { button.disabled = true; button.setAttribute('data-draft-pending', ''); });
      definition.content.querySelectorAll('.sw-rfp-block').forEach(block => block.classList.remove('is-built'));
      definition.content.querySelectorAll('.sw-document-actions button').forEach(button => { button.disabled = true; });
    },
    complete() {
      draftOrder.forEach(readyDraft);
      definition.content.querySelectorAll('.sw-rfp-block').forEach(block => block.classList.add('is-built'));
      definition.content.querySelector('[data-procurement-ready]').hidden = false;
      if (definition.content.querySelector('[data-procurement-reader]').hidden || definition.content.dataset.openRfp !== 'civil-stormwater') openRfp('civil-stormwater');
    },
    buildSteps({ at, actions, reveal, revealHeading, revealRow, follow, highlight, setStage }) {
      const find = selector => definition.content.querySelector(selector);
      const group = find('.sw-procurement-grid tbody');
      actions.push({ at, run: () => { reveal(group); setStage('Procurement · consultant register'); } });
      for (const row of group.querySelectorAll('[data-build-row]')) {
        at += 340;
        actions.push({ at, run: () => { revealRow(row); follow(row); } });
      }
      for (const key of draftOrder) {
        at += 750;
        actions.push({ at, run: () => { readyDraft(key); setStage(`${names[key]} · RFP draft ready`); } });
      }
      at += 650;
      actions.push({ at, run: () => { find('[data-procurement-ready]').hidden = false; } });
      at += 1000;
      actions.push({ at, run: () => definition.content.setAttribute('data-procurement-exit', '') });
      at += 420;
      actions.push({ at, run: () => { openRfp('civil-stormwater'); highlight(null); setStage('Civil / stormwater engineer · preparing RFP'); } });
      const sections = [...find('[data-rfp="civil-stormwater"]').querySelectorAll('.sw-rfp-section')];
      sections.forEach((section, index) => actions.push({ at: at + 100 + index * 220, run: () => revealHeading(section) }));
      at += sections.length * 220 + 600;
      for (const section of sections) {
        actions.push({ at, run: () => { reveal(section); setStage(`Civil RFP · ${section.dataset.sectionTitle}`); } });
        // Wait for the section's expanding layout before moving the reading position.
        actions.push({ at: at + 550, run: () => follow(section.querySelector('.sw-section-title')) });
        at += 240;
        for (const block of section.querySelectorAll('.sw-rfp-block')) {
          actions.push({ at, run: () => block.classList.add('is-built') });
          at += 350;
        }
        at += section.dataset.sectionTitle === 'Services and deliverables' ? 2000 : 600;
      }
      at += 400;
      actions.push({ at, run: () => { follow(sections.find(section => section.dataset.sectionTitle === 'Services and deliverables').querySelector('.sw-section-title')); } });
      return at + 800;
    },
    openRfp,
  };
  function readyDraft(key) {
    files[key].hidden = false;
    const button = definition.content.querySelector(`[data-open-rfp="${key}"]`);
    button.removeAttribute('data-draft-pending'); button.disabled = false;
  }
  function openRfp(key) {
    if (!rfpDrafts[key]) return;
    // Other drafts are opened on demand; the automatic scene only reads the civil RFP.
    if (!definition.content.querySelector(`[data-rfp="${key}"]`)) definition.content.querySelector('[data-procurement-reader]').insertAdjacentHTML('beforeend', rfpMarkup(key, rfpDrafts[key]));
    definition.content.removeAttribute('data-procurement-exit');
    definition.content.querySelector('[data-procurement-register]').hidden = true;
    definition.content.querySelector('[data-procurement-reader]').hidden = false;
    definition.content.querySelectorAll('[data-rfp]').forEach(article => { article.hidden = article.dataset.rfp !== key; });
    definition.content.dataset.openRfp = key;
    definition.content.querySelectorAll('.sw-document-actions button').forEach((button, index) => {
      button.disabled = false;
      button.setAttribute(index ? 'data-copy-rfp' : 'data-download-rfp', '');
      button.setAttribute('aria-label', `${index ? 'Copy' : 'Download'} ${names[key]} RFP`);
    });
    definition.content.querySelector('[data-document]').scrollTop = 0;
  }
  return definition;
}
