import { useEffect, useState } from 'react';
import { Icon } from './atoms.jsx';

// The sections in the sidebar, in order. Shared by the upload screen (shown
// greyed out until documents are read) and the app.
export const VIEWS = { overview: 'Overview', events: 'Advice events', review: 'Needs review', tree: 'Folder tree', log: 'Filing log', about: 'About' };
export const NAV = [['overview', 'grid'], ['events', 'layers'], ['review', 'alert'], ['tree', 'folder'], ['log', 'check']];

function useTheme() {
  // Light by default; Auto follows the computer's setting. Storage is optional.
  const read = () => { try { return localStorage.getItem('theme') || 'light'; } catch { return 'light'; } };
  const [mode, setMode] = useState(read);
  useEffect(() => {
    const el = document.documentElement;
    try { localStorage.setItem('theme', mode); } catch { /* storage optional */ }
    mode === 'auto' ? el.removeAttribute('data-theme') : el.setAttribute('data-theme', mode);
  }, [mode]);
  return [mode, setMode];
}

export function TitleBar() {
  const [theme, setTheme] = useTheme();
  return (
    <div className="titlebar">
      <div className="lights" aria-hidden="true"><i /><i /><i /></div>
      <span className="appmark" aria-hidden="true"><Icon id="cabinet" /></span>
      <span className="appname">Advice Document Filing</span>
      <span className="grow" />
      <div className="seg" role="group" aria-label="Theme">
        {['auto', 'light', 'dark'].map((m) => (
          <button key={m} aria-pressed={theme === m} onClick={() => setTheme(m)}>{m[0].toUpperCase() + m.slice(1)}</button>
        ))}
      </div>
    </div>
  );
}
