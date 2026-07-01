import { existsSync, readFileSync } from 'node:fs';

const requiredFiles = [
  'index.html',
  'src/main.jsx',
  'src/App.jsx',
  'src/App.css',
  'vite.config.js',
];

const missing = requiredFiles.filter((file) => !existsSync(new URL(`../${file}`, import.meta.url)));
if (missing.length) {
  console.error(`Missing frontend files: ${missing.join(', ')}`);
  process.exit(1);
}

const app = readFileSync(new URL('../src/App.jsx', import.meta.url), 'utf8');
const requiredSnippets = [
  'US Newstrade Breakout',
  'Nicht handeln',
  'Stop Loss',
  'CRV',
  'emotion_before',
  'spread_per_unit',
  'Watchlist Import',
  'parseTradingViewWatchlist',
  'Datei laden',
  'Trade starten',
  'Trade abschliessen',
  'Laufende Trades',
  'manual_journal_drafts.json',
  'loadJournalDraft',
  'Aktiv bearbeiten',
  'journalActionStatus',
  'Event verarbeiten',
];

const absent = requiredSnippets.filter((snippet) => !app.includes(snippet));
if (absent.length) {
  console.error(`Missing required UI snippets: ${absent.join(', ')}`);
  process.exit(1);
}

console.log('Frontend structure OK');
