import { useEffect, useState } from 'react';
import { Icon, FileIcon, Confidence, StatusBadge, Type, Finding } from './atoms.jsx';
import { pct, plural } from './model.js';

// Plain-words answer to the two questions a person has first: why here, and how sure.
function Summary({ d, doc, ev }) {
  const t = doc.threshold ?? d.confidence_threshold;   // the backend sets a line per document type
  const dst = doc.destination || {};
  const above = doc.confidence >= t;
  const blocking = doc.flags.find((f) => f.blocks_filing);
  const others = doc.flags.length - (blocking ? 1 : 0);
  return (
    <div className={`summary ${doc.needs_review ? 'held' : ''}`}>
      <h4>In short</h4>
      <p><b>How sure:</b> read as {doc.type_label}, {pct(doc.confidence)}% sure. That is {above ? 'above' : 'below'} the{' '}
        {pct(t)}% line{above ? '.' : ', so the tool will not file it.'}</p>
      {doc.needs_review
        ? <p><b>Why held:</b> {blocking ? blocking.message : (doc.review_reasons || [])[0] || (!above ? 'confidence is below the line.' : 'the tool could not place it with certainty.')}</p>
        : <p><b>Why here:</b> {ev ? <>part of {doc.client}’s {ev.subject} advice ({ev.record_label}, {ev.date || 'undated'}). </> : <>{doc.client ? `${doc.client}’s file, ` : ''}not tied to one piece of advice. </>}
          {dst.path ? <>Proposed folder: {dst.folder.join(' / ')}.</> : <>Not placed yet: {dst.rationale}.</>}</p>}
      {others > 0 && <p><b>Also:</b> {plural(others, 'point', 'points')} worth checking below.</p>}
    </div>
  );
}

// A verdict for the failure log (/review/correction): a reason code, never free
// text, because a free-text box is where a client's name gets typed.
async function sendVerdict(doc, correctType, reason) {
  const res = await fetch('/review/correction', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: doc.document_id, predicted_type: doc.type, correct_type: correctType,
      reason, corrections: [], engine_version: doc.engine_version || null }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `answered ${res.status}`);
}

function Verdict({ doc, decision, server, onDecide }) {
  const canRecord = server.mode === 'live' && !!doc.document_id && !!server.options;
  const [rejecting, setRejecting] = useState(false);
  const [type, setType] = useState('');
  const [reason, setReason] = useState('');
  const [status, setStatus] = useState(null);
  useEffect(() => { setRejecting(false); setType(''); setReason(''); setStatus(null); }, [doc.doc_id]);

  const record = async (correctType, code) => {
    if (!canRecord) return;
    try { await sendVerdict(doc, correctType, code); setStatus('Recorded in the failure log.'); }
    catch (e) { setStatus(`Not recorded: ${e.message}`); }
  };
  const approve = () => {
    onDecide('approve');
    setRejecting(false);
    // Only a held document's approval says something: the tool was right and held it anyway.
    if (doc.needs_review && doc.type) record(doc.type, server.options.approve_reason);
  };
  const reject = () => {
    if (!canRecord) { onDecide('reject'); return; }
    setRejecting(true);
  };
  const submit = () => { onDecide('reject'); setRejecting(false); record(type, reason); };

  return (
    <div className="insp-foot">
      <div className="acts">
        <button className="btn yes" aria-pressed={decision === 'approve'} onClick={approve}><Icon id="check" />Approve</button>
        <button className="btn no" aria-pressed={decision === 'reject'} onClick={reject}><Icon id="x" />Reject</button>
      </div>
      {rejecting && (
        <div className="verdict">
          <label>What is it?
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="">Choose a type</option>
              {server.options.document_types.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></label>
          <label>Why was it wrong?
            <select value={reason} onChange={(e) => setReason(e.target.value)}>
              <option value="">Choose a reason</option>
              {server.options.reject_reasons.map((r) => <option key={r.code} value={r.code} title={r.meaning}>{r.code.replace(/_/g, ' ')}</option>)}
            </select></label>
          <button className="btn sm primary" disabled={!type || !reason} onClick={submit}>Record</button>
        </div>
      )}
      <small>{status || (canRecord
        ? (decision ? (decision === 'approve' ? 'Approved.' : 'Rejected.') : 'A person decides. Verdicts go to the failure log.')
        : (decision ? `${decision === 'approve' ? 'Approved' : 'Rejected'}. Not recorded: demo.` : 'A person decides. Not recorded: demo.'))}</small>
    </div>
  );
}

export default function Inspector({ d, doc, decision, server, onDecide, onStep, onClose }) {
  if (!doc) {
    return (
      <aside className="insp" aria-label="Document details">
        <div className="insp-empty"><div><Icon id="file" /><div>Select a document to see why it was placed where it was.</div></div></div>
      </aside>
    );
  }
  const list = d.documents;
  const i = list.indexOf(doc);
  const dst = doc.destination || {};
  const ev = d.events.find((e) => e.event_id === doc.event_id);

  return (
    <aside className="insp" aria-label="Document details">
      <div className="insp-head">
        <div className="insp-nav">
          <button className="ibtn" title="Previous" disabled={i <= 0} onClick={() => onStep(-1)}><Icon id="up" /></button>
          <button className="ibtn" title="Next" disabled={i >= list.length - 1} onClick={() => onStep(1)}><Icon id="down" /></button>
          <span>{i + 1} of {list.length}</span><span className="grow" />
          <button className="ibtn" title="Close" onClick={onClose}><Icon id="x" /></button>
        </div>
        <div className="insp-title"><FileIcon doc={doc} />
          <div style={{ minWidth: 0 }}><b>{doc.source_name}</b>
            <div className="tags"><Type>{doc.type_label}</Type><StatusBadge doc={doc} /></div>
          </div>
        </div>
      </div>

      <div className="insp-body">
        <Summary d={d} doc={doc} ev={ev} />

        <div className="isec"><h4>Classification</h4>
          <dl className="kv">
            <dt>Type</dt><dd>{doc.type_label}{doc.category && <small>{doc.category}</small>}</dd>
            {doc.stages && doc.stages.length > 0 && <><dt>Step</dt><dd>{doc.stages.join(' · ')}</dd></>}
            <dt>Confidence</dt><dd><Confidence doc={doc} threshold={doc.threshold ?? d.confidence_threshold} /></dd>
            <dt>Extraction</dt><dd>{doc.extraction_quality != null && <>{pct(doc.extraction_quality)}% quality · </>}{plural(doc.pages, 'page', 'pages')}</dd>
          </dl>
          {doc.classification_evidence && <div className="evidence" style={{ marginTop: 8 }}>{doc.classification_evidence}</div>}
        </div>

        <div className="isec"><h4>Client and advice event</h4>
          <dl className="kv">
            <dt>Client</dt><dd>{doc.client || 'none'}{doc.client_provenance && <small>{doc.client_provenance}</small>}</dd>
            <dt>Dated</dt><dd>{doc.date || 'undated'}{doc.date_provenance && <small>{doc.date_provenance}</small>}</dd>
            <dt>Event</dt><dd>{ev ? <>{ev.subject} · {ev.record_label}<small>{ev.date || 'undated'}</small></> : 'none'}</dd>
            {doc.attachment_reason && <><dt>Grouped</dt><dd>{doc.attachment_reason}</dd></>}
          </dl>
        </div>

        <div className="isec"><h4>Worth checking</h4>
          {doc.flags.length
            ? doc.flags.map((f) => <Finding key={f.id} f={f} />)
            : <div className="none"><Icon id="check" />Nothing to check</div>}
        </div>

        <div className="isec"><h4>{doc.needs_review ? 'Held in' : 'Proposed filing'}</h4>
          {dst.path && <span className="path">{dst.path}</span>}
          {dst.rationale && <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--mute)' }}>{dst.rationale}</p>}
        </div>
      </div>

      <Verdict doc={doc} decision={decision} server={server || {}} onDecide={onDecide} />
    </aside>
  );
}
