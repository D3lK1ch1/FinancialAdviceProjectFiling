import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import Pick from './Pick.jsx';
import { setData } from './model.js';
import './styles.css';

// The page carries no data: it asks for PDFs, sends them to /api/batch, and
// shows what came back. "New batch" goes back to the upload screen; the key
// gives each batch a fresh App, so nothing from the last one carries over.
function Root() {
  const [batch, setBatch] = useState(0);
  if (!batch) return <Pick onData={(data) => { setData(data); setBatch((n) => n + 1); }} />;
  return <App key={batch} onNewBatch={() => setBatch(0)} />;
}

createRoot(document.getElementById('root')).render(<Root />);
