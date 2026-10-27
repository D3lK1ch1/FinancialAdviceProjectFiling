import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import Pick from './Pick.jsx';
import { setData } from './model.js';
import './styles.css';

const root = createRoot(document.getElementById('root'));
const start = (data) => { setData(data); root.render(<App />); };

// The demo build carries its data; the build Python serves (/app/) does not,
// so it asks for documents first and sends them to /api/batch.
if (window.DATA) start(window.DATA);
else root.render(<Pick onData={start} />);
