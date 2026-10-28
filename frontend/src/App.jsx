import { useEffect, useRef, useState } from 'react';
import { Icon } from './atoms.jsx';
import Inspector from './Inspector.jsx';
import { NAV, TitleBar, VIEWS, useTeaching } from './Frame.jsx';
import { Overview, Events, Review, Tree, Log, About } from './views.jsx';
import { manifest, statusOf, initials, batchable, oneClick, startLine, plural } from './model.js';

const WITH_INSPECTOR = ['events', 'review', 'tree', 'log'];

const viewFromHash = () => (VIEWS[location.hash.slice(1)] ? location.hash.slice(1) : 'overview');

function useWide() {
  const [wide, setWide] = useState(() => window.innerWidth > 1100);
  useEffect(() => {
    const on = () => setWide(window.innerWidth > 1100);
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, []);
  return wide;
}

export default function App({ onNewBatch }) {
  const [view, setView] = useState(viewFromHash);
  const [selected, setSelected] = useState(null);
  const [client, setClient] = useState(null);       // Advice events shows only this client's documents
  const [decisions, setDecisions] = useState({});   // in memory only: nothing is written yet
  const [log, setLog] = useState([]);               // the filing log: in memory only, like decisions
  const [teaching, setTeaching] = useTeaching();
  const wide = useWide();
  const scrollRef = useRef(null);

  const d = manifest();
  const doc = selected && d.documents.find((x) => x.doc_id === selected);

  useEffect(() => {
    const on = () => setView(viewFromHash());
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = 0; }, [view]);

  const step = (n) => {
    const i = d.documents.findIndex((x) => x.doc_id === selected) + n;
    if (d.documents[i]) setSelected(d.documents[i].doc_id);
  };
  useEffect(() => {
    const on = (e) => {
      if (e.target.closest && e.target.closest('select')) return;
      if (e.key === 'Escape') setSelected(null);
      if (selected && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) { e.preventDefault(); step(e.key === 'ArrowDown' ? 1 : -1); }
    };
    document.addEventListener('keydown', on);
    return () => document.removeEventListener('keydown', on);
  });
  useEffect(() => {
    if (!selected) return;
    const el = document.querySelector(`.view:not([hidden]) [data-doc="${selected}"]`);
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
  }, [selected]);

  const go = (v) => { location.hash = v; };
  const showClient = (c) => { setClient(c); go('events'); };
  const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const record = (e) => setLog((l) => [...l, { id: l.length + 1, at: now(), ...e }]);
  // Automatic batch filing (review_policy.one_click, decided 21 Oct): every
  // document at or above the line with nothing to check is filed as soon as it
  // is read, and logged. Anything else is flagged for a person. A document a
  // person has undone is never filed again by the batch.
  const [line, setLine] = useState(() => startLine(d));
  // The review options from the knowledge base. Verdicts go to the failure log
  // once these have loaded, for documents the tool read (they carry a document_id).
  const [server, setServer] = useState({ options: null });
  useEffect(() => {
    fetch('/review/options').then((r) => r.json())
      .then((o) => setServer({ options: o }))
      .catch(() => setServer({ options: null }));
  }, []);
  const decided = useRef({});
  const undone = useRef(new Set());
  decided.current = decisions;
  useEffect(() => {
    const floor = oneClick(d).floor;
    const ids = d.documents
      .filter((x) => !decided.current[x.doc_id] && !undone.current.has(x.doc_id) && batchable(x, line, floor))
      .map((x) => x.doc_id);
    if (!ids.length) return;
    setDecisions((m) => ({ ...m, ...Object.fromEntries(ids.map((id) => [id, 'approve'])) }));
    record({ kind: 'auto', level: line, ids, decision: 'approve' });
  }, [line]);
  // Undo clears the decisions that entry made and marks it undone; the log keeps it.
  const undoEntry = (id) => {
    const e = log.find((x) => x.id === id);
    if (!e) return;
    setDecisions((m) => { const n = { ...m }; e.ids.forEach((d0) => { if (n[d0] === e.decision) delete n[d0]; }); return n; });
    e.ids.forEach((d0) => undone.current.add(d0));
    setLog((l) => l.map((x) => (x.id === id ? { ...x, undone: true } : x)));
  };
  const decide = (k) => {
    const same = decisions[selected] === k;
    setDecisions((m) => ({ ...m, [selected]: same ? undefined : k }));
    if (!same) record({ kind: 'single', ids: [selected], decision: k });
  };
  const showInspector = WITH_INSPECTOR.includes(view) && (doc || wide);

  const perClient = {};
  d.documents.forEach((x) => { if (x.client) perClient[x.client] = (perClient[x.client] || 0) + 1; });
  const n = d.batch.documents;
  const ok = d.documents.filter((x) => statusOf(x) === 'ok').length;
  const warn = d.documents.filter((x) => statusOf(x) === 'warn').length;
  const live = log.filter((e) => !e.undone).length;
  const sub = { log: plural(live, 'entry', 'entries'), events: `${d.events.length} events · ${n} documents`, review: `${d.batch.needs_review} held`, tree: 'Proposed filing' }[view] || '';
  const counts = { events: d.events.length, review: d.batch.needs_review, tree: n, log: live };
  const viewProps = { d, selected, onSelect: setSelected, decisions, line, onLine: setLine, log };

  return (
    <div className="window" role="application" aria-label="Advice Document Filing">
      <TitleBar teaching={teaching} onTeaching={setTeaching} />

      <div className="banner" role="note">
        <span className="demo-tag">Proposals only</span>
        <div className="msg">
          <b>Read on this computer.</b>
          <span>Nothing is moved, renamed or saved yet. Approving here only shows what would happen.</span>
        </div>
      </div>

      <div className="body">
        <nav className="side" aria-label="Sections">
          <h6>Batch</h6>
          {NAV.map(([v, ic]) => (
            <a key={v} className="nav" href={`#${v}`} aria-current={view === v ? 'page' : undefined}>
              <Icon id={ic} />{VIEWS[v]}
              {counts[v] ? <span className={`count ${v === 'review' ? 'warn' : ''}`}>{counts[v]}</span> : null}
            </a>
          ))}
          <button className="nav" onClick={onNewBatch}><Icon id="file" />New batch</button>
          <h6>Clients</h6>
          {!Object.keys(perClient).length && <span className="nav off side-hint">No client name found in these documents.</span>}
          {Object.keys(perClient).sort().map((c) => (
            <button key={c} className="client" aria-pressed={client === c} onClick={() => showClient(client === c ? null : c)}>
              <span className="av">{initials(c)}</span>{c}<span className="count">{perClient[c]}</span>
            </button>
          ))}
          <h6>Help</h6>
          <a className="nav" href="#about" aria-current={view === 'about' ? 'page' : undefined}><Icon id="info" />About</a>
          <div className="foot">
            <b>{ok} of {n} ready to file</b>
            <div className="meter">
              <i style={{ width: `${ok / n * 100}%`, background: 'var(--ok)' }} />
              <i style={{ width: `${warn / n * 100}%`, background: 'var(--warn)' }} />
              <i style={{ width: `${(n - ok - warn) / n * 100}%`, background: 'var(--bad)' }} />
            </div>
            {d.batch.needs_review} held for review · line at {Math.round(d.confidence_threshold * 100)}%
          </div>
        </nav>

        <div className="sheet">
          <main className="main">
            <div className="toolbar">
              <h2>{VIEWS[view]}</h2>
              <span className="sub">{sub}</span>
            </div>

            <div className="scroll" ref={scrollRef}>
              <section className="view" hidden={view !== 'overview'}><Overview d={d} go={go} /></section>
              <section className="view" hidden={view !== 'events'}><Events {...viewProps} client={client} onClient={setClient} /></section>
              <section className="view" hidden={view !== 'review'}><Review {...viewProps} /></section>
              <section className="view" hidden={view !== 'tree'}><Tree {...viewProps} /></section>
              <section className="view" hidden={view !== 'log'}><Log {...viewProps} log={log} onUndo={undoEntry} /></section>
              <section className="view" hidden={view !== 'about'}><About /></section>

              <footer>
                <span className="kb"><Icon id="shield" /><span>Knowledge base v{d.knowledge_base_version}</span></span> · Australia, Corporations Act 2001, ASIC.
                Not legal advice.
              </footer>
            </div>
          </main>

          {showInspector && (
            <Inspector d={d} doc={doc} decision={decisions[selected]} server={server} teaching={teaching}
              onDecide={decide} onStep={step} onClose={() => setSelected(null)} />
          )}
        </div>
      </div>
    </div>
  );
}
