import { useState } from 'react';

// Choose PDFs, send them to the backend, hand back the manifest.
export default function Pick({ onData }) {
  const [busy, setBusy] = useState(0);
  const [error, setError] = useState(null);

  const send = async (files) => {
    const pdfs = [...files].filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    if (!pdfs.length) { setError('Choose one or more PDF files.'); return; }
    setError(null); setBusy(pdfs.length);
    const form = new FormData();
    pdfs.forEach((f) => form.append('files', f));
    try {
      const res = await fetch('/api/batch', { method: 'POST', body: form });
      if (!res.ok) throw new Error(`The backend answered ${res.status}.`);
      onData(await res.json());
    } catch (e) {
      setError(`Could not read the documents. ${e.message} Is the backend running?`);
      setBusy(0);
    }
  };

  return (
    <div className="scrim pick-scrim">
      <div className="welcome pick" role="dialog" aria-labelledby="pick-title">
        <h2 id="pick-title">Advice Document Filing</h2>
        <p className="welcome-lede">Choose the PDFs to read. They are read by the backend on this computer.
          Nothing is moved, renamed or saved.</p>
        {busy
          ? <p className="pick-busy" role="status">Reading {busy} {busy === 1 ? 'document' : 'documents'}. This can take a minute per document.</p>
          : <label className="btn primary pick-btn">Choose PDFs
              <input type="file" accept="application/pdf,.pdf" multiple hidden onChange={(e) => send(e.target.files)} /></label>}
        {error && <p className="pick-error" role="alert">{error}</p>}
        {!busy && <p className="pick-alt">The full screens appear once the PDFs are read, about a minute each.{' '}
          <a href="demo.html">See them now with sample documents</a>.</p>}
      </div>
    </div>
  );
}
