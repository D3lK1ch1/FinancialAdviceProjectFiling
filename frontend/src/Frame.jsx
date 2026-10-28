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

// Display mode (#11): show the knowledge base's teaching notes, or don't. Only
// hides text on screen, so it can't change a classification, a flag or a
// review (ground rule 4). On by default, like the knowledge base's setting.
export function useTeaching() {
  const read = () => { try { return localStorage.getItem('teaching') !== 'off'; } catch { return true; } };
  const [on, setOn] = useState(read);
  const set = (v) => { setOn(v); try { localStorage.setItem('teaching', v ? 'on' : 'off'); } catch { /* storage optional */ } };
  return [on, set];
}

export function TitleBar({ teaching, onTeaching }) {
  const [theme, setTheme] = useTheme();
  return (
    <div className="titlebar">
      <div className="lights" aria-hidden="true"><i /><i /><i /></div>
      <span className="appmark" aria-hidden="true"><Icon id="cabinet" /></span>
      <span className="appname">Advice Document Filing</span>
      <span className="grow" />
      {onTeaching && (
        <div className="seg" role="group" aria-label="Teaching notes">
          <span className="seg-l">Teaching notes</span>
          <button aria-pressed={teaching} onClick={() => onTeaching(true)}>On</button>
          <button aria-pressed={!teaching} onClick={() => onTeaching(false)}>Off</button>
        </div>
      )}
      <div className="seg" role="group" aria-label="Theme">
        {['auto', 'light', 'dark'].map((m) => (
          <button key={m} aria-pressed={theme === m} onClick={() => setTheme(m)}>{m[0].toUpperCase() + m.slice(1)}</button>
        ))}
      </div>
    </div>
  );
}
