// After `vite build`: the pages FastAPI serves from dist/app/.
//   index.html  the demo: the made-up sample folder, plus the public documents
//               read by the real tool (public-data.json, when it exists)
//   live.html   no data: asks for PDFs, and only works when the backend is live
// dist/demo.html is the same demo page, to open straight from disk.
const fs = require('fs');
const page = fs.readFileSync('dist/index.html', 'utf8');
const inline = (data) => page.replace('__DATA__', JSON.stringify(data).replace(/<\//g, '<\\/'));

const demo = JSON.parse(fs.readFileSync('sample-data.json', 'utf8'));
if (fs.existsSync('public-data.json')) Object.assign(demo, JSON.parse(fs.readFileSync('public-data.json', 'utf8')));

fs.mkdirSync('dist/app', { recursive: true });
fs.writeFileSync('dist/app/index.html', inline(demo));
fs.writeFileSync('dist/app/live.html', page.replace('__DATA__', 'null'));
fs.writeFileSync('dist/demo.html', inline(demo));
console.log('pages: app/index.html (' + Object.keys(demo).join(' + ') + '), app/live.html, demo.html');
