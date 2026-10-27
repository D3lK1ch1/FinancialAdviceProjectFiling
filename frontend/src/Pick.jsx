import { useState } from 'react';
import { Icon } from './atoms.jsx';
import { NAV, TitleBar, VIEWS } from './Frame.jsx';

// The first screen at /: drop or choose PDFs, and they go to /api/batch. The
// sidebar is shown greyed out, so a person sees what they will get once the
// documents are read.
export default function Pick({ onData }) {
  const [busy, setBusy] = useState(0);
  const [error, setError] = useState(null);
  const [over, setOver] = useState(false);

  const send = async (files) => {
    const pdfs = [...files].filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    if (!pdfs.length) { setError('Choose one or more PDF files.'); return; }
    setError(null); setBusy(pdfs.length);
    const form = new FormData();
    pdfs.forEach((f) => form.append('files', f));
    try {
      const res = await fetch('/api/batch', { method: 'POST', body: form });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `The app answered ${res.status}.`);
      onData(await res.json());
    } catch (e) {
      setError(`Could not read the documents. ${e.message}`);
      setBusy(0);
    }
  };
  const drop = (e) => { e.preventDefault(); setOver(false); if (!busy) send(e.dataTransfer.files); };

  return (
    <div className="window" role="application" aria-label="Advice Document Filing">
      <TitleBar />
      <div className="body">
        <nav className="side" aria-label="Sections">
          <h6>Batch</h6>
          {NAV.map(([v, ic]) => <span key={v} className="nav off" aria-disabled="true"><Icon id={ic} />{VIEWS[v]}</span>)}
          <h6>Clients</h6>
          <span className="nav off side-hint">Found in the documents once they are read.</span>
        </nav>
        <div className="sheet">
          <main className="main">
            <div className="toolbar"><h2>Add documents</h2></div>
            <div className="scroll">
              <div className="pad">
                <label className={`drop ${over ? 'over' : ''} ${busy ? 'busy' : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setOver(true); }}
                  onDragLeave={() => setOver(false)} onDrop={drop}>
                  <Icon id="file" />
                  {busy
                    ? <b role="status">Reading {busy} {busy === 1 ? 'document' : 'documents'}. This can take about a minute each.</b>
                    : <>
                        <b>Drop PDFs here, or choose files</b>
                        <span>They are read on this computer. Nothing is moved, renamed or saved.</span>
                        <span className="btn primary">Choose PDFs</span>
                      </>}
                  <input type="file" accept="application/pdf,.pdf" multiple hidden disabled={!!busy}
                    onChange={(e) => send(e.target.files)} />
                </label>
                {error && <p className="pick-error" role="alert">{error}</p>}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
