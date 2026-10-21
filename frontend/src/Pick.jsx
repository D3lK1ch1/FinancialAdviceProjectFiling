import { useEffect, useState } from 'react';

// The live page (/app/live.html): choose PDFs and send them to the backend.
// Only works when the backend is set up in live mode; in demo mode it says so
// and offers the demo instead. The backend refuses uploads in demo mode anyway.
export default function Pick({ onData }) {
  const [mode, setMode] = useState(null);
  const [busy, setBusy] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/mode').then((r) => r.json()).then((m) => setMode(m.mode)).catch(() => setMode('unknown'));
  }, []);

  const send = async (files) => {
    const pdfs = [...files].filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    if (!pdfs.length) { setError('Choose one or more PDF files.'); return; }
    setError(null); setBusy(pdfs.length);
    const form = new FormData();
    pdfs.forEach((f) => form.append('files', f));
    try {
      const res = await fetch('/api/batch', { method: 'POST', body: form });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `The backend answered ${res.status}.`);
      onData(await res.json());
    } catch (e) {
      setError(`Could not read the documents. ${e.message}`);
      setBusy(0);
    }
  };

  return (
    <div className="scrim pick-scrim">
      <div className="welcome pick" role="dialog" aria-labelledby="pick-title">
        <h2 id="pick-title">Advice Document Filing</h2>
        {mode === 'live' ? <>
          <p className="welcome-lede">Choose the PDFs to read. They are read on this computer.
            Nothing is moved, renamed or saved.</p>
          {busy
            ? <p className="pick-busy" role="status">Reading {busy} {busy === 1 ? 'document' : 'documents'}. This can take a minute per document.</p>
            : <label className="btn primary pick-btn">Choose PDFs
                <input type="file" accept="application/pdf,.pdf" multiple hidden onChange={(e) => send(e.target.files)} /></label>}
          {error && <p className="pick-error" role="alert">{error}</p>}
        </> : <>
          <p className="welcome-lede">{mode === null ? 'Checking…' : 'Uploading is switched off. This is a demo, so it only shows sample and public documents.'}</p>
          <a className="btn primary pick-btn" href="./">Open the demo</a>
        </>}
      </div>
    </div>
  );
}
