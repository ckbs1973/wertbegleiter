import { useCallback, useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'tradingfreaks-focus-desk-v3';
const SANDBOX_STORAGE_KEY = 'tradingfreaks-focus-desk-v3-sandbox';
const SANDBOX_FLAG_KEY = 'wertbegleiter-sandbox-mode';

const setupOptions = [
  'US Newstrade Breakout',
  'Rectangle Scalping',
  'Premarket High/Low',
  'US Newstrade Reversal',
  'Reversal ohne News',
  'FX Wirtschaftsdaten',
  'FX Trendlinie',
  'DAX Abpraller',
  'SR Reversal',
];

const fallbackAssetSymbols = [
  'NVDA',
  'TSLA',
  'AAPL',
  'MSFT',
  'META',
  'AMD',
  'DE40',
  'US500',
  'EURUSD',
  'GBPUSD',
  'USDJPY',
  'XAUUSD',
  'XAGUSD',
  'UKOIL',
];

const preCheckDefinitions = [
  {
    name: '1. Trading Setup',
    detail: 'Markt, Zeiteinheit, Stil und Strategie sind eindeutig definiert.',
    evidence: 'TradingPlan.pdf: Trading Setup',
  },
  {
    name: '2. Beste Gelegenheit',
    detail: 'Timing, Level, Chartbild, Kontext und Katalysator passen zum Setup.',
    evidence: 'TradingPlan.pdf: Beste Gelegenheit',
  },
  {
    name: '3. Trade Management',
    detail: 'Entry, Stop Loss, Take Profit/Exit, Risiko und CRV sind geplant.',
    evidence: 'TradingPlan.pdf + Gebote fuers Trading',
  },
  {
    name: '4. Ueberzeugung & Disziplin',
    detail: 'Ueberzeugung 1-10, kein FOMO, kein Revenge, mentale Lage stabil.',
    evidence: 'TradingPlan.pdf: Ueberzeugungs-Level',
  },
  {
    name: '5. Journal vorbereitet',
    detail: 'Kriterien, Chartbild, Kommentare und Review-Felder sind vorbereitet.',
    evidence: 'TF Journal-Vorlagen',
  },
];

const checklist = preCheckDefinitions.map((item) => item.name);

const morningTimeline = [
  { time: '08:00', title: 'Daily Update', detail: 'Kalender, Wochenplan, Oil, USD, Yields, Tech' },
  { time: '10:00-12:00', title: 'Europa ORB', detail: 'DE40, EURUSD, USDJPY, XAU/XAG' },
  { time: '15:25', title: 'US Open Prep', detail: 'Futures, Semis, Micron, News-Filter' },
  { time: '15:30-15:35', title: 'No Trade', detail: 'erste US-Open-Kerze nur beobachten' },
  { time: '16:30-18:00', title: 'US Momentum', detail: 'Pullback, Retest, failed Breakout' },
  { time: '21:59', title: 'Close', detail: 'Intraday Positionen schliessen' },
];

const defaultContext = {
  account_equity: 10000,
  default_risk_percent: 1,
  trades_taken_today: 0,
  max_trades_per_day: 5,
  target_min_trades: 2,
  target_max_trades: 5,
  loss_streak: 0,
  psychology_ready: true,
  bored_or_fomo: false,
  revenge_risk: false,
  daily_loss_limit_reached: false,
  weekly_loss_limit_reached: false,
  correlated_exposure_warning: false,
};

const defaultJournal = {
  emotion_before: 'Neutral',
  emotion_during: '',
  emotion_after: '',
  confidence_level: 5,
  stress_level: 2,
  focus_level: 4,
  screenshot_before: '',
  screenshot_after: '',
  exit_price: '',
  exit_reason: '',
  realized_r: '',
  result_money: '',
  fees: '',
  slippage: '',
  rule_compliant: true,
  violated_rule: '',
  what_went_well: '',
  improvement: '',
  review: '',
};

const defaultBacktestCosts = {
  spread_per_unit: 0.02,
  slippage_per_unit: 0.01,
};

const defaultTradeFilters = {
  mode: 'live',
  periodType: 'all',
  periodValue: '',
  market: 'all',
};

function isSandboxModeRequested() {
  try {
    const params = new URLSearchParams(window.location.search);
    return params.get('sandbox') === '1' || window.localStorage.getItem(SANDBOX_FLAG_KEY) === '1';
  } catch {
    return false;
  }
}

const sourceLinks = {
  xPro: 'https://tweetdeck.x.com/',
  xSearch: 'https://x.com/search',
  seekingAlpha: 'https://seekingalpha.com/market-news/top-news',
  investingCalendar: 'https://www.investing.com/economic-calendar-',
  forexLive: 'https://www.forexlive.com/',
  tradingView: 'https://www.tradingview.com/',
};

const importExample = `###STOCK CFD,GBEBROKERS:NVDA,GBEBROKERS:TSLA,GBEBROKERS:AAPL,GBEBROKERS:MSFT,###INDEX CFD,GBEBROKERS:DE40,GBEBROKERS:US500,###Forex,GBEBROKERS:EURUSD,GBEBROKERS:GBPUSD,###COMMODITY CFD,GBEBROKERS:XAUUSD,GBEBROKERS:XAGUSD,GBEBROKERS:UKOIL`;
const SCREENSHOT_MAX_WIDTH = 1400;
const SCREENSHOT_MAX_HEIGHT = 1000;
const SCREENSHOT_JPEG_QUALITY = 0.78;

const importedJournalSources = [
  {
    url: '/data/trade_history_gbe_2026-05-20_reconstructed_trades.csv',
    type: 'reconstructed',
    label: 'GBE/TradingView Orderverlauf',
  },
  {
    url: '/data/gbe_monthly_closed_trades.csv',
    type: 'monthly',
    label: 'GBE Monatsberichte',
  },
  {
    url: '/data/gbe_eod_2026-06-24_account_16291_journal_import.csv',
    type: 'eod',
    label: 'GBE EOD Report 16291',
  },
  {
    url: '/data/gbe_eod_2026-06-26_end_of_day_report_16291_journal_import.csv',
    type: 'eod',
    label: 'GBE EOD Report 16291 | 2026-06-26',
  },
];

const chatUpdateFeedUrl = '/data/chatgpt_trading_updates.json';
const liveFeedStatusUrl = '/data/live_feed_status.json';
const liveAdapterConfigStatusUrl = '/data/live_adapter_config_status.json';
const manualJournalDraftsUrl = '/data/manual_journal_drafts.json';
const journalStoreApiUrl = 'http://127.0.0.1:8000/api/journal/store';
const LIVE_STATUS_FILE_STALE_AFTER_SECONDS = 20;

const tradingViewCaptureCommands = {
  open:
    'python3 tools/capture_tradingview_event.py --event-type opened --trade-id btc-paper-1 --symbol BTCUSD --market crypto --direction long --entry 60000 --stop-loss 59500 --take-profit 61000 --size 0.1 --copy',
  close:
    'python3 tools/capture_tradingview_event.py --event-type closed_take_profit --trade-id btc-paper-1 --symbol BTCUSD --market crypto --exit-price 61000 --copy',
};

const liveBridgeCards = [
  {
    title: 'Kurse',
    source: 'TradingView/Broker Kurse',
    stale: '5s',
    config: 'LIVE_PRICE_JSON_PATH=reports/live_sources/tradingview_price.json oder TRADINGVIEW_BRIDGE_URL=https://...',
    payload: '{"bridge_type":"price","symbol":"BTCUSD","last":60447.98}',
    connect: 'TradingView-Webhook, Broker-API oder lokaler Bridge-Prozess erforderlich.',
    link: sourceLinks.tradingView,
  },
  {
    title: 'Orders',
    source: 'TradingView/Broker Orders',
    stale: '5s',
    config: 'LIVE_ORDER_JSON_PATH=reports/live_sources/tradingview_orders.json oder BROKER_EVENT_STREAM_URL=https://...',
    payload: '{"bridge_type":"order","event_type":"opened","trade_id":"paper-1","symbol":"BTCUSD"}',
    connect: 'Orderstream oder manuell erzeugte TradingView/Broker-Events erforderlich.',
    link: sourceLinks.tradingView,
  },
  {
    title: 'Kalender',
    source: 'Wirtschaftskalender',
    stale: '15m',
    config: 'LIVE_CALENDAR_JSON_PATH=reports/live_sources/economic_calendar.json oder ECONOMIC_CALENDAR_API_URL=https://...',
    payload: '{"bridge_type":"calendar","events":[{"title":"US PCE","impact":"high"}]}',
    connect: 'Kalender-JSON/API mit Zeitstempel und High-Impact-Events erforderlich.',
    link: sourceLinks.investingCalendar,
  },
  {
    title: 'News',
    source: 'News/Squawk/X Pro',
    stale: '60s',
    config: 'LIVE_NEWS_FEED_URL=https://investinglive.com/feed/ oder NEWSQUAWK_API_URL/X_PRO_LIST_URL',
    payload: '{"bridge_type":"news","items":[{"headline":"Squawk heartbeat"}]}',
    connect: 'ForexLive/InvestingLive RSS ist verbunden; Newsquawk/X-Pro kann spaeter als schnellerer Feed gesetzt werden.',
    link: sourceLinks.xPro,
  },
];

function makeTradeEventExample(eventType = 'opened') {
  const timestamp = new Date().toISOString();
  const isClose = String(eventType).startsWith('closed');
  return JSON.stringify(
    isClose
      ? {
          event_type: eventType,
          source: 'tradingview_paper',
          trade_id: 'btc-paper-1',
          symbol: 'BTCUSD',
          timestamp,
          exit_price: eventType === 'closed_stop_loss' ? 59500 : 61000,
          fees: 0,
          slippage: 0,
          screenshot_path: '',
          note: 'Trade wurde in TradingView/Broker geschlossen. Review ergaenzen.',
        }
      : {
          event_type: 'opened',
          source: 'tradingview_paper',
          trade_id: 'btc-paper-1',
          symbol: 'BTCUSD',
          market: 'crypto',
          timestamp,
          direction: 'long',
          entry: 60000,
          stop_loss: 59500,
          take_profit: 61000,
          size: 0.1,
          screenshot_path: '',
          note: 'TradingView/Paper-Event importiert. Setup-Check und Review manuell pruefen.',
        },
    null,
    2,
  );
}

function makeConditions(passed = false) {
  return checklist.map((name) => ({ name, passed, required: true }));
}

function makeCandidate(overrides = {}) {
  return {
    candidate_id: `candidate-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    symbol: '',
    catalyst: '',
    setup_name: 'US Newstrade Breakout',
    market: 'us_stock',
    direction: 'conditional',
    style: 'scalping',
    planned_time: '15:45',
    entry: '',
    stop_loss: '',
    take_profit: '',
    unit_value: 1,
    risk_percent: 1,
    notes: '',
    conditions: makeConditions(false),
    ...overrides,
  };
}

const defaultCandidates = [
  makeCandidate({
    candidate_id: 'focus-nvda',
    symbol: 'NVDA',
    catalyst: 'Morning Brief | Stock News',
    notes: 'Nur bei marktrelevanter News, Gap/Opening Drive, VWAP-Seite und enger Konsolidierung pruefen.',
  }),
  makeCandidate({
    candidate_id: 'focus-de40',
    symbol: 'DE40',
    market: 'index',
    setup_name: 'DAX Abpraller',
    planned_time: '09:15',
    catalyst: 'H4/D1 Zone',
    notes: 'Nur an vorbereiteter Zone und ohne nahes Risikoevent pruefen.',
  }),
  makeCandidate({
    candidate_id: 'focus-xagusd',
    symbol: 'XAGUSD',
    market: 'commodity',
    setup_name: 'SR Reversal',
    planned_time: '09:30',
    catalyst: 'Metallblock | USD/Yields | Gold/Silber-Ratio',
    notes: 'Silber immer mit Gold, USD/Yields, China-/Industriebezug und doppelter Metall-Exposure pruefen.',
  }),
];

function normalizeCandidate(candidate) {
  const normalizedConditions = checklist.map((name) => {
    const saved = candidate?.conditions?.find((condition) => condition.name === name);
    return { name, passed: Boolean(saved?.passed), required: true };
  });
  return makeCandidate({
    ...candidate,
    candidate_id: candidate?.candidate_id || `candidate-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    conditions: normalizedConditions,
  });
}

function candidateFocusKey(candidate) {
  const symbol = String(candidate?.symbol || '').trim().toUpperCase();
  return symbol ? `symbol:${symbol}` : `id:${candidate?.candidate_id || Math.random()}`;
}

function dedupeCandidates(candidates, preferredId = '') {
  const byKey = new Map();
  const order = [];
  candidates.forEach((candidate) => {
    const key = candidateFocusKey(candidate);
    if (!byKey.has(key)) {
      byKey.set(key, candidate);
      order.push(key);
      return;
    }
    if (candidate.candidate_id === preferredId) {
      byKey.set(key, candidate);
    }
  });
  return order.map((key) => byKey.get(key));
}

function normalizeJournalDraft(draft) {
  if (draft?.imported || draft?.lifecycle_status) return draft;
  const looksOpen = Boolean(draft?.screenshot_before) && !draft?.screenshot_after && !draft?.realized_r && !draft?.result_money;
  return {
    ...draft,
    lifecycle_status: looksOpen ? 'open' : 'closed',
    status: looksOpen ? 'Trade laeuft' : draft?.status || 'Review offen',
    started_at: draft?.started_at || draft?.sort_key || new Date().toISOString(),
    closed_at: looksOpen ? '' : draft?.closed_at || '',
  };
}

function makeSandboxJournalDraft() {
  const now = new Date().toISOString();
  return {
    draft_id: 'sandbox-open-btcusd',
    external_trade_id: 'sandbox-btcusd-1',
    account_mode: 'live',
    date: todayLabel(),
    symbol: 'BTCUSD',
    market: 'crypto',
    setup: 'SR Reversal / Sandbox-Test',
    status: 'Trade laeuft',
    lifecycle_status: 'open',
    started_at: now,
    closed_at: '',
    direction: 'long',
    planned_time: '09:30',
    entry: '60000',
    stop_loss: '59500',
    take_profit: '61000',
    risk_amount: '100.00',
    position_size: '0.20',
    planned_crv: '2.00',
    failed_conditions: ['Sandbox: 5 Pre-Checks manuell testen'],
    emotion_before: 'Neutral',
    emotion_during: '',
    emotion_after: '',
    confidence_level: 5,
    stress_level: 2,
    focus_level: 4,
    screenshot_before: '',
    screenshot_after: '',
    exit_price: '',
    exit_reason: '',
    realized_r: '',
    result_money: '',
    fees: '',
    slippage: '',
    rule_compliant: false,
    violated_rule: 'Sandbox-Test ohne echte Setup-Freigabe',
    what_went_well: '',
    improvement: 'Button-Flows, R-Berechnung, Screenshots und Abschluss testen.',
    review: 'Sandbox-Trade. Keine Anlageberatung, keine Orderfreigabe.',
    completion: 25,
    source: 'Sandbox-Testmodus',
    sandbox: true,
    information_only: true,
    sort_key: now,
  };
}

function loadInitialState(storageKey = STORAGE_KEY, sandboxMode = false) {
  try {
    const saved = JSON.parse(window.localStorage.getItem(storageKey));
    if (saved?.context && saved?.candidates?.length) {
      const candidates = dedupeCandidates(saved.candidates.map(normalizeCandidate), saved.activeId);
      const journalDrafts = (saved.journalDrafts || []).map(normalizeJournalDraft);
      const activeJournalDraftId = saved.activeJournalDraftId || journalDrafts.find((draft) => draft.lifecycle_status === 'open')?.draft_id || '';
      return {
        context: { ...defaultContext, ...saved.context },
        candidates,
        activeId: candidates.some((candidate) => candidate.candidate_id === saved.activeId)
          ? saved.activeId
          : candidates[0].candidate_id,
        journal: { ...defaultJournal, ...saved.journal },
        journalDrafts,
        activeJournalDraftId,
        backtestCosts: { ...defaultBacktestCosts, ...saved.backtestCosts },
        importText: saved.importText || '',
        tradeEventText: saved.tradeEventText || makeTradeEventExample(),
        activeView: saved.activeView || 'guide',
      };
    }
  } catch {
    // Keep a fresh desk when local browser data is stale.
  }
  const sandboxDraft = sandboxMode ? makeSandboxJournalDraft() : null;
  return {
    context: defaultContext,
    candidates: defaultCandidates,
    activeId: defaultCandidates[0].candidate_id,
    journal: sandboxDraft ? journalFromDraft(sandboxDraft) : defaultJournal,
    journalDrafts: sandboxDraft ? [sandboxDraft] : [],
    activeJournalDraftId: sandboxDraft?.draft_id || '',
    backtestCosts: defaultBacktestCosts,
    importText: '',
    tradeEventText: makeTradeEventExample(),
    activeView: sandboxMode ? 'journal' : 'guide',
  };
}

function toNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function display(value, digits = 2) {
  return Number.isFinite(value) ? value.toFixed(digits) : '0.00';
}

function percentOf(value, total) {
  if (!total) return 0;
  return Math.max(0, Math.min(100, (value / total) * 100));
}

function percentWidth(value, total) {
  return `${percentOf(value, total)}%`;
}

function todayLabel() {
  return new Intl.DateTimeFormat('de-DE', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date());
}

function timeToMinutes(value) {
  const [hours, minutes] = String(value).split(':').map((part) => Number(part));
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return 0;
  return hours * 60 + minutes;
}

function normalizeDirection(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (['short', 'sell', 's'].includes(normalized)) return 'short';
  if (['long', 'buy', 'l'].includes(normalized)) return 'long';
  return 'conditional';
}

function directionLabel(value) {
  if (value === 'long') return 'Long';
  if (value === 'short') return 'Short';
  return 'Bedingt';
}

function marketLabel(value) {
  const labels = {
    us_stock: 'US-Aktie',
    forex: 'FX',
    index: 'Index',
    commodity: 'Rohstoff',
    crypto: 'Krypto-CFD',
  };
  return labels[value] || 'Watchlist';
}

function statusLabel(status) {
  if (status === 'Manuelle Pruefung') return 'Manuelle Pruefung';
  return status;
}

function inferImportDefaults(group, symbol, exchange) {
  const groupName = String(group || '').toUpperCase();
  const symbolName = String(symbol || '').toUpperCase();

  if (groupName.includes('STOCK')) {
    return {
      market: 'us_stock',
      setup_name: 'US Newstrade Breakout',
      planned_time: '15:45',
      style: 'scalping',
      notes: 'News, Gap, VWAP, RVOL, Opening Drive und M1-Liquiditaet pruefen.',
    };
  }
  if (groupName.includes('FOREX')) {
    return {
      market: 'forex',
      setup_name: 'FX Trendlinie',
      planned_time: '09:00',
      style: 'daytrading',
      notes: 'Sentiment, Risikoevents, Spread und H4/D1-Level pruefen.',
    };
  }
  if (groupName.includes('INDEX') || ['DE40', 'DJ30', 'US500', 'USTEC', 'UK100'].includes(symbolName)) {
    return {
      market: 'index',
      setup_name: symbolName === 'DE40' ? 'DAX Abpraller' : 'SR Reversal',
      planned_time: '09:15',
      style: 'scalping',
      notes: 'H4/D1/W1-Zonen, Risk-On/Risk-Off und Eventnaehe pruefen.',
    };
  }
  if (groupName.includes('COMMODITY') || ['XAGUSD', 'XAUUSD', 'UKOIL'].includes(symbolName)) {
    return {
      market: 'commodity',
      setup_name: 'SR Reversal',
      planned_time: '09:30',
      style: 'daytrading',
      notes: symbolName === 'XAGUSD'
        ? 'Silber immer mit Gold, USD/Yields, China-/Industriebezug und doppelter Metall-Exposure pruefen.'
        : 'Volatilitaet, Spread, USD/Yields und starke Zonen pruefen.',
    };
  }
  if (groupName.includes('KRYPTO') || ['BTCUSD', 'ETHUSD', 'ADAUSD', 'XRPUSD'].includes(symbolName)) {
    return {
      market: 'crypto',
      setup_name: 'SR Reversal',
      planned_time: '09:30',
      style: 'daytrading',
      notes: 'Nur beobachten, bis Spread, Volatilitaet und Setup sauber klassifiziert sind.',
    };
  }
  return {
    market: 'us_stock',
    setup_name: 'US Newstrade Breakout',
    planned_time: '15:45',
    style: 'scalping',
    notes: exchange ? `Importiert von ${exchange}. Setup manuell klassifizieren.` : 'Importiert. Setup manuell klassifizieren.',
  };
}

function candidateFromSymbolToken(token, group, index) {
  const cleanToken = String(token || '').trim();
  const [exchange, rawSymbol] = cleanToken.includes(':') ? cleanToken.split(':') : ['', cleanToken];
  const symbol = (rawSymbol || exchange).replace(/[^A-Za-z0-9._-]/g, '').toUpperCase();
  const defaults = inferImportDefaults(group, symbol, exchange);
  return makeCandidate({
    candidate_id: `tv-${Date.now()}-${index}`,
    symbol,
    catalyst: [group, exchange].filter(Boolean).join(' | '),
    setup_name: defaults.setup_name,
    market: defaults.market,
    planned_time: defaults.planned_time,
    style: defaults.style,
    notes: defaults.notes,
  });
}

function parseTradingViewWatchlist(text) {
  const tokens = text.split(',').map((token) => token.trim()).filter(Boolean);
  const candidates = [];
  let group = 'Watchlist';
  tokens.forEach((token) => {
    if (token.startsWith('###')) {
      group = token.replace(/^#+/, '').trim() || 'Watchlist';
      return;
    }
    if (token.includes(':')) candidates.push(candidateFromSymbolToken(token, group, candidates.length));
  });
  return candidates;
}

function splitImportRow(row) {
  if (row.includes('\t')) return row.split('\t').map((part) => part.trim());
  if (row.includes(';')) return row.split(';').map((part) => part.trim());
  if (row.includes(',')) return row.split(',').map((part) => part.trim());
  const [symbol, ...rest] = row.trim().split(/\s+/);
  return [symbol, '', '', '', '', '', '', rest.join(' ')];
}

function parseWatchlistImport(text) {
  const commaTokens = text.split(',').map((token) => token.trim()).filter(Boolean);
  const looksLikeTradingViewExport =
    commaTokens.length > 2 && commaTokens.some((token) => token.startsWith('###') || /^[A-Z0-9_]+:[A-Z0-9._-]+$/i.test(token));
  if (looksLikeTradingViewExport) return parseTradingViewWatchlist(text);

  return text
    .split(/\r?\n/)
    .map((row) => row.trim())
    .filter(Boolean)
    .filter((row) => !row.startsWith('#'))
    .map((row, index) => {
      const parts = splitImportRow(row);
      const rawSymbol = String(parts[0] || '').toUpperCase();
      const [exchange, symbolPart] = rawSymbol.includes(':') ? rawSymbol.split(':') : ['', rawSymbol];
      const symbol = symbolPart || exchange;
      const defaults = inferImportDefaults('', symbol, exchange);
      return makeCandidate({
        candidate_id: `import-${Date.now()}-${index}`,
        symbol,
        setup_name: parts[1] || defaults.setup_name,
        market: defaults.market,
        direction: normalizeDirection(parts[2]),
        planned_time: parts[3] || defaults.planned_time,
        entry: parts[4] || '',
        stop_loss: parts[5] || '',
        take_profit: parts[6] || '',
        catalyst: parts[7] || (exchange ? `Exchange: ${exchange}` : ''),
        notes: parts[8] || parts[7] || defaults.notes,
      });
    });
}

function buildAssetOptions(currentCandidates, currentImportText = '') {
  const options = new Map();
  const addOption = (candidate, source) => {
    const symbol = String(candidate?.symbol || '').trim().toUpperCase();
    if (!symbol) return;
    const defaults = inferImportDefaults('', symbol, '');
    options.set(symbol, {
      symbol,
      market: candidate.market || defaults.market,
      setup_name: candidate.setup_name || defaults.setup_name,
      planned_time: candidate.planned_time || defaults.planned_time,
      unit_value: candidate.unit_value || defaults.unit_value,
      catalyst: candidate.catalyst || defaults.catalyst || source,
      notes: candidate.notes || defaults.notes || '',
      source,
    });
  };

  currentCandidates.forEach((candidate) => addOption(candidate, 'Aktuelle Watchlist'));
  if (currentImportText.trim()) {
    parseWatchlistImport(currentImportText).forEach((candidate) => addOption(candidate, 'Import-Vorschau'));
  }
  fallbackAssetSymbols.forEach((symbol) => addOption({ symbol, ...inferImportDefaults('', symbol, '') }, 'Standardliste'));

  return [...options.values()].sort(
    (a, b) => scoreCandidatePriority(b) - scoreCandidatePriority(a) || a.symbol.localeCompare(b.symbol),
  );
}

function assetCandidatePatch(option) {
  return {
    symbol: option.symbol,
    market: option.market,
    setup_name: option.setup_name,
    planned_time: option.planned_time,
    unit_value: option.unit_value,
    catalyst: option.catalyst,
    notes: option.notes,
  };
}

function uniqueSymbols(list) {
  return [...new Set(list.map((candidate) => String(candidate.symbol || '').trim().toUpperCase()).filter(Boolean))];
}

function buildSearchUrl(query) {
  return `${sourceLinks.xSearch}?q=${encodeURIComponent(query)}&src=typed_query&f=live`;
}

function buildNewsDeckColumns(currentCandidates) {
  const stockSymbols = uniqueSymbols(currentCandidates.filter((candidate) => candidate.market === 'us_stock')).slice(0, 10);
  const fxSymbols = uniqueSymbols(currentCandidates.filter((candidate) => candidate.market === 'forex')).slice(0, 12);
  const indexSymbols = uniqueSymbols(currentCandidates.filter((candidate) => candidate.market === 'index')).slice(0, 10);
  const commoditySymbols = uniqueSymbols(currentCandidates.filter((candidate) => candidate.market === 'commodity')).slice(0, 10);
  const stockQuery = stockSymbols.length
    ? `(${stockSymbols.map((symbol) => `$${symbol}`).join(' OR ')}) (earnings OR guidance OR upgrade OR downgrade OR acquisition OR buyback OR "short report") -filter:replies`
    : '(earnings OR guidance OR upgrade OR downgrade OR acquisition) -filter:replies';
  const fxQuery = fxSymbols.length
    ? `(${fxSymbols.join(' OR ')}) (CPI OR NFP OR Fed OR ECB OR BoE OR BoJ OR rates OR PMI) -filter:replies`
    : '(CPI OR NFP OR Fed OR ECB OR BoE OR BoJ OR rates OR PMI) -filter:replies';
  const indexQuery = indexSymbols.length
    ? `(${indexSymbols.join(' OR ')}) (DAX OR Nasdaq OR futures OR yield OR risk-on OR risk-off) -filter:replies`
    : '(DAX OR Nasdaq OR futures OR yield OR risk-on OR risk-off) -filter:replies';
  const metalsQuery = '(XAUUSD OR XAGUSD OR silver OR gold OR oil OR Brent OR WTI) (USD OR yields OR China OR risk-off OR Hormuz) -filter:replies';

  return [
    {
      title: 'US Stock Catalysts',
      source: 'X Pro / TweetDeck',
      symbols: stockSymbols,
      query: stockQuery,
      url: buildSearchUrl(stockQuery),
      blocker: 'Mixed News, fehlende Preisreaktion oder Volatilitaet ohne Momentum.',
    },
    {
      title: 'Stock Confirmation',
      source: 'Seeking Alpha',
      symbols: stockSymbols,
      query: 'Earnings, Guidance, Up-/Downgrades, Uebernahmen, Short-Attacken',
      url: sourceLinks.seekingAlpha,
      blocker: 'Headline nicht marktrelevant oder bereits eingepreist.',
    },
    {
      title: 'FX Macro Pulse',
      source: 'X Pro / ForexLive',
      symbols: fxSymbols,
      query: fxQuery,
      url: buildSearchUrl(fxQuery),
      blocker: 'Nahe Risikoevents, gemischte Daten oder Sentiment-Konflikt.',
    },
    {
      title: 'Risk Calendar',
      source: 'Investing.com',
      symbols: fxSymbols,
      query: 'CPI, Arbeitsmarkt, Zentralbanken, PMIs, Wachstum',
      url: sourceLinks.investingCalendar,
      blocker: 'Eventzeit, Spread oder Slippage-Risiko unklar.',
    },
    {
      title: 'Index Risk Tone',
      source: 'X Pro / ForexLive',
      symbols: indexSymbols,
      query: indexQuery,
      url: buildSearchUrl(indexQuery),
      blocker: 'Keine starke H4/D1/W1-Zone oder Risikoevent in direkter Naehe.',
    },
    {
      title: 'Metals / Oil Stress',
      source: 'X Pro / ForexLive',
      symbols: commoditySymbols.length ? commoditySymbols : ['XAUUSD', 'XAGUSD', 'UKOIL'],
      query: metalsQuery,
      url: buildSearchUrl(metalsQuery),
      blocker: 'Keine doppelte Metall-Exposure; kein Blind-Long in XAUEUR, wenn XAUUSD klar gegenlaeuft.',
    },
  ];
}

function directionThesis(candidate) {
  if (candidate.market === 'us_stock') {
    return 'Long nur bei positiver News, Opening Drive und Kurs ueber VWAP; Short nur bei negativer News und Kurs unter VWAP.';
  }
  if (candidate.market === 'forex') {
    return 'Richtung erst nach stark-gegen-schwach, Sentiment, Kalenderpruefung und Momentum.';
  }
  if (candidate.market === 'index') {
    return 'Richtung nur am vorbereiteten H4/D1/W1-Level mit sauberem Abpraller oder Breakout.';
  }
  if (candidate.market === 'commodity') {
    return 'Richtung nur nach USD/Yields-, Gold/Silber-, Oel-/Geopolitik- und Spread-Bestaetigung.';
  }
  return 'Richtung bleibt offen, bis Marktphase, Level, Spread und Momentum bestaetigt sind.';
}

function timeWindow(candidate) {
  if (candidate.market === 'us_stock') return '15:30 Opening Drive, 15:45-20:00 Scalping-Fenster';
  if (candidate.market === 'forex') return 'Nach Kalendercheck, nicht direkt vor Risikoevents';
  if (candidate.market === 'index') return 'Europa-Session und US-Impuls, nur an markanten Zonen';
  if (candidate.market === 'commodity') return '08:00 Kontextblock, 10:00-12:00 und 16:30-18:00 nur mit Bestaetigung';
  return 'Nur nach Spread- und Volatilitaetscheck';
}

function scoreCandidatePriority(candidate) {
  const symbol = String(candidate.symbol || '').toUpperCase();
  const stockPriority = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'GOOG', 'NKE', 'PYPL'];
  if (candidate.market === 'us_stock') return 100 - Math.max(0, stockPriority.indexOf(symbol)) * 3;
  if (candidate.market === 'index') return 70;
  if (candidate.market === 'forex') return 55;
  if (candidate.symbol === 'XAGUSD') return 54;
  if (candidate.market === 'commodity') return 45;
  return 30;
}

function contextBlockers(context) {
  const blockers = [];
  if (toNumber(context.trades_taken_today) >= toNumber(context.max_trades_per_day)) blockers.push('Max Trades erreicht');
  if (!context.psychology_ready) blockers.push('Psychologie blockiert');
  if (context.bored_or_fomo) blockers.push('Langeweile/FOMO');
  if (context.revenge_risk) blockers.push('Revenge-Risiko');
  if (context.daily_loss_limit_reached) blockers.push('Tagesverlustlimit');
  if (context.weekly_loss_limit_reached) blockers.push('Wochenverlustlimit');
  if (toNumber(context.loss_streak) >= 3) blockers.push('Verlustserie >= 3');
  return blockers;
}

function evaluateCandidate(candidate, context) {
  const failed = [];
  const warnings = [];
  const blockers = contextBlockers(context);
  const entry = toNumber(candidate.entry);
  const stop = toNumber(candidate.stop_loss);
  const target = toNumber(candidate.take_profit);
  const unitValue = toNumber(candidate.unit_value) || 1;
  const riskPercent = toNumber(candidate.risk_percent || context.default_risk_percent);
  const riskAmount = (toNumber(context.account_equity) * riskPercent) / 100;
  const riskPerUnit = Math.abs(entry - stop) * unitValue;
  const positionSize = riskPerUnit > 0 ? riskAmount / riskPerUnit : 0;
  const plannedReward = Math.abs(target - entry) * unitValue * positionSize;
  const crv = riskAmount > 0 ? plannedReward / riskAmount : 0;
  const plannedMinutes = timeToMinutes(candidate.planned_time);

  if (!candidate.symbol.trim()) failed.push('Symbol fehlt');
  if (candidate.direction === 'conditional') failed.push('Richtung noch nicht bestaetigt');
  candidate.conditions.forEach((condition) => {
    if (condition.required && !condition.passed) failed.push(condition.name);
  });
  if (riskPercent > 1) warnings.push('Risiko ueber 1%');
  if (riskPercent > 5) failed.push('Risiko ueber 5%');
  if (!entry || !stop) failed.push('Stop Loss/Risiko unvollstaendig');
  if (!target) failed.push('Take Profit oder Exit-Regel fehlt');
  if (candidate.direction === 'long' && entry && stop && stop >= entry) failed.push('Long Stop Loss muss unter Entry liegen');
  if (candidate.direction === 'short' && entry && stop && stop <= entry) failed.push('Short Stop Loss muss ueber Entry liegen');
  if (candidate.direction === 'long' && entry && target && target <= entry) failed.push('Long Take Profit muss ueber Entry liegen');
  if (candidate.direction === 'short' && entry && target && target >= entry) failed.push('Short Take Profit muss unter Entry liegen');
  if (!Number.isFinite(crv) || crv < 1) failed.push('CRV >= 1:1');
  if (candidate.market === 'us_stock' && candidate.style === 'scalping') {
    if (plannedMinutes < 15 * 60 + 30) failed.push('US-Hauptsession noch nicht offen');
    if (plannedMinutes >= 15 * 60 + 30 && plannedMinutes < 15 * 60 + 35) {
      failed.push('Keine erste 5-Minuten-Kerze im US-Open handeln');
    }
    if (plannedMinutes > 20 * 60) failed.push('Nach 20:00 kein neuer Scalp');
  }
  if (context.correlated_exposure_warning) warnings.push('Korrelation pruefen');

  const uniqueFailed = [...new Set(failed)];
  const uniqueWarnings = [...new Set(warnings)];
  const passedCount = candidate.conditions.filter((condition) => condition.passed).length;
  const completionScore = Math.round((passedCount / candidate.conditions.length) * 100);
  let status = 'Nur beobachten';
  if (blockers.length) status = 'Blockiert';
  else if (!uniqueFailed.length) status = 'Manuelle Pruefung';

  return {
    status,
    failed: [...new Set([...blockers, ...uniqueFailed])],
    warnings: uniqueWarnings,
    riskAmount,
    riskPerUnit,
    positionSize,
    plannedReward,
    crv: Number.isFinite(crv) ? crv : 0,
    completionScore,
  };
}

function Field({ label, children, compact = false }) {
  return (
    <label className={`field ${compact ? 'compact' : ''}`}>
      <span>{label}</span>
      {children}
    </label>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

function PreCheckToggle({ condition, definition, onChange }) {
  return (
    <label className={`preCheckToggle ${condition.passed ? 'passed' : ''}`}>
      <input type="checkbox" checked={condition.passed} onChange={(event) => onChange(event.target.checked)} />
      <span>
        <strong>{condition.name}</strong>
        <small>{definition?.detail || 'TradingFreaks Pre-Check manuell pruefen.'}</small>
        <em>{definition?.evidence || 'TradingFreaks Schulungsunterlagen'}</em>
      </span>
    </label>
  );
}

function ScreenshotDropZone({ label, value, onChange }) {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const hasImage = String(value || '').startsWith('data:image/');

  const handleFile = async (file) => {
    if (!file) return;
    setError('');
    try {
      const dataUrl = await compressScreenshot(file);
      onChange(dataUrl);
    } catch (issue) {
      setError(issue.message || 'Screenshot konnte nicht gelesen werden.');
    }
  };

  const handlePaste = (event) => {
    const imageFile = imageFileFromClipboard(event);
    if (imageFile) {
      event.preventDefault();
      handleFile(imageFile);
      return;
    }
    const pastedText = event.clipboardData?.getData('text/plain');
    if (pastedText) onChange(pastedText.trim());
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragActive(false);
    handleFile(event.dataTransfer?.files?.[0]);
  };

  return (
    <section
      className={`screenshotDropZone ${dragActive ? 'dragActive' : ''} ${value ? 'hasValue' : ''}`}
      onDragEnter={(event) => {
        event.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
      onPaste={handlePaste}
      tabIndex="0"
    >
      <div className="screenshotHeader">
        <strong>{label}</strong>
        <span>{hasImage ? 'Bild gespeichert' : value ? 'Link/Pfad gespeichert' : 'Screenshot einfuegen'}</span>
      </div>
      {hasImage && <img src={value} alt={label} />}
      {!hasImage && value && <code>{value}</code>}
      {!value && <span className="screenshotPlaceholder">Copy/Paste oder Drag & Drop</span>}
      <div className="screenshotActions">
        <label className="fileButton">
          Bild waehlen
          <input type="file" accept="image/*" onChange={(event) => handleFile(event.target.files?.[0])} />
        </label>
        {value && (
          <button type="button" className="ghostButton" onClick={() => onChange('')}>
            Entfernen
          </button>
        )}
      </div>
      {error && <small className="screenshotError">{error}</small>}
    </section>
  );
}

function inputProps(value, onChange, step = '0.01') {
  return {
    type: 'number',
    step,
    value,
    onChange: (event) => onChange(event.target.value),
  };
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Datei konnte nicht gelesen werden.'));
    reader.readAsDataURL(file);
  });
}

function loadImage(dataUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('Bild konnte nicht geladen werden.'));
    image.src = dataUrl;
  });
}

async function compressScreenshot(file) {
  if (!file?.type?.startsWith('image/')) throw new Error('Nur Bilddateien werden unterstuetzt.');
  const dataUrl = await fileToDataUrl(file);
  const image = await loadImage(dataUrl);
  const scale = Math.min(1, SCREENSHOT_MAX_WIDTH / image.width, SCREENSHOT_MAX_HEIGHT / image.height);
  const width = Math.max(1, Math.round(image.width * scale));
  const height = Math.max(1, Math.round(image.height * scale));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, width, height);
  context.drawImage(image, 0, 0, width, height);
  return canvas.toDataURL('image/jpeg', SCREENSHOT_JPEG_QUALITY);
}

function imageFileFromClipboard(event) {
  const items = Array.from(event.clipboardData?.items || []);
  const imageItem = items.find((item) => item.type?.startsWith('image/'));
  return imageItem?.getAsFile() || null;
}

function statusClass(status) {
  if (status === 'Manuelle Pruefung') return 'ok';
  if (status === 'Blockiert' || status === 'Trading Pause') return 'danger';
  return 'watch';
}

function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;
  const input = String(text || '');

  for (let index = 0; index < input.length; index += 1) {
    const char = input[index];
    const next = input[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      index += 1;
      continue;
    }
    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }
    if (char === ',' && !inQuotes) {
      row.push(cell);
      cell = '';
      continue;
    }
    if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') index += 1;
      row.push(cell);
      if (row.some((value) => String(value).trim())) rows.push(row);
      row = [];
      cell = '';
      continue;
    }
    cell += char;
  }

  row.push(cell);
  if (row.some((value) => String(value).trim())) rows.push(row);
  return rows;
}

function csvToObjects(text) {
  const rows = parseCsvRows(text);
  const header = rows[0]?.map((name) => String(name || '').trim()) || [];
  return rows.slice(1).map((row) =>
    Object.fromEntries(header.map((name, index) => [name, String(row[index] || '').trim()])),
  );
}

function csvBoolean(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return ['true', 'ja', 'yes', '1'].includes(normalized);
}

function parseCsvNumber(value) {
  const text = String(value ?? '').trim();
  if (!text) return null;
  const parsed = Number(text.replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : null;
}

function parseJournalNumber(value) {
  const text = String(value ?? '').trim();
  if (!text) return null;
  const cleaned = text
    .replace(/\s/g, '')
    .replace(/(EUR|USD|CHF|GBP|R)/gi, '')
    .replace(/'/g, '');
  const normalized = cleaned.includes(',') && cleaned.includes('.')
    ? cleaned.replace(/\./g, '').replace(',', '.')
    : cleaned.replace(',', '.');
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function amountLabel(value) {
  const parsed = parseCsvNumber(value);
  return parsed === null ? '' : display(parsed);
}

function entryDate(value) {
  return String(value || '').slice(0, 10) || 'Datum offen';
}

function entryTime(value) {
  return String(value || '').slice(11, 16) || '--:--';
}

function compactImportedSymbol(value) {
  return String(value || '')
    .trim()
    .toUpperCase()
    .replace(/\.OQ$/, '')
    .replace(/\.N$/, '')
    .replace(/\.C$/i, '');
}

function marketFromImportedSymbol(symbol) {
  const clean = compactImportedSymbol(symbol);
  if (['DE40', 'DAX', 'DJ30', 'USTEC', 'US500', 'JP225', 'F40'].includes(clean)) return 'index';
  if (['XAUUSD', 'XAGUSD', 'XAUEUR', 'UKOIL', 'USOIL'].includes(clean)) return 'commodity';
  if (['BTCUSD', 'ETHUSD', 'SOLUSD', 'BCHUSD', 'BTCEUR'].includes(clean)) return 'crypto';
  if (/^[A-Z]{6}$/.test(clean)) return 'forex';
  return 'us_stock';
}

function tradeAccountMode(entry) {
  const explicitMode = String(entry.account_mode || entry.accountMode || entry.mode || '').toLowerCase();
  if (explicitMode.includes('live') || explicitMode.includes('echt')) return 'live';
  if (explicitMode.includes('paper') || explicitMode.includes('test') || explicitMode.includes('demo')) return 'paper';
  if (explicitMode.includes('import') || explicitMode.includes('archiv') || explicitMode.includes('archive')) return 'import';
  if (entry.imported || entry.source_import_id) return 'import';
  const source = String(entry.source || '').toLowerCase();
  const draftId = String(entry.draft_id || '').toLowerCase();
  const externalTradeId = String(entry.external_trade_id || '').toLowerCase();
  if (
    source.includes('paper') ||
    source.includes('demo') ||
    source.includes('tradingview_paper') ||
    draftId.includes('paper') ||
    externalTradeId.includes('paper')
  ) {
    return 'paper';
  }
  if (source.includes('import') || source.includes('gbe') || source.includes('brokerreport')) return 'import';
  return 'live';
}

function tradeAccountModeLabel(mode) {
  if (mode === 'live') return 'Echt/Live';
  if (mode === 'paper') return 'Paper/Test';
  if (mode === 'import') return 'Import/Archiv';
  return 'Alle';
}

function tradeModeEmptyText(mode) {
  if (mode === 'live') return 'Noch keine Echtgeld-Trades im aktiven Journal. Paper/Test und Brokerimporte liegen im Archivfilter.';
  if (mode === 'paper') return 'Keine Paper-/Testtrades fuer diese Filterauswahl.';
  if (mode === 'import') return 'Keine importierten Archivtrades fuer diese Filterauswahl.';
  return 'Keine Trades fuer diese Filterauswahl.';
}

function liveReadinessItems(evaluations = [], configAdapters = []) {
  const bySource = new Map((evaluations || []).map((item) => [item.source_name, item]));
  const configBySource = new Map((configAdapters || []).map((item) => [item.source_name, item]));
  return liveBridgeCards.map((card) => {
    const evaluation = bySource.get(card.source);
    const config = configBySource.get(card.source);
    const status = evaluation?.status || 'missing';
    const ready = status === 'live';
    const configured = Boolean(config?.configured);
    const configStatus = config?.status || 'missing_config';
    return {
      ...card,
      status,
      ready,
      configured,
      configStatus,
      configMessage: config?.message || 'Keine Adapter-Konfiguration gefunden.',
      locationMasked: config?.location_masked || '',
      fileExists: config?.file_exists,
      message: evaluation?.message || 'Quelle ist noch nicht angebunden.',
      details: evaluation?.details || [],
      nextStep: ready
        ? 'Live angebunden. Frischegrenze weiter ueberwachen.'
        : config?.next_step || `${card.config} in .env setzen und Adapter starten.`,
    };
  });
}

function setupFromImportedSymbol(symbol) {
  const market = marketFromImportedSymbol(symbol);
  if (market === 'index') return compactImportedSymbol(symbol) === 'DE40' ? 'DAX Abpraller / Import Review' : 'SR Reversal / Import Review';
  if (market === 'commodity') return 'SR Reversal / Rohstoff-Review';
  if (market === 'forex') return 'FX Trendlinie / Event-Review';
  if (market === 'us_stock') return 'US Newstrade / Setup manuell pruefen';
  return 'Import Review';
}

function importedFailedConditions({ hasStopLoss, hasTakeProfit, crv, slCorrectSide = true }) {
  const failed = ['TF-Setup-Checkliste fehlt', 'Screenshots/Emotionen nachtragen'];
  if (!hasStopLoss) failed.push('Stop Loss nicht dokumentiert');
  if (!hasTakeProfit) failed.push('Take Profit oder Exit-Regel nicht dokumentiert');
  if (crv !== null && crv < 1) failed.push('CRV unter 1:1');
  if (crv === null) failed.push('CRV nicht belastbar dokumentiert');
  if (!slCorrectSide) failed.push('Stop Loss Seite pruefen');
  return failed;
}

function historyTradeToJournalDraft(row, index, sourceLabel) {
  const symbol = compactImportedSymbol(row.symbol);
  const crv = parseCsvNumber(row.recorded_crv);
  const hasStopLoss = csvBoolean(row.has_recorded_sl);
  const hasTakeProfit = csvBoolean(row.has_recorded_tp);
  const slCorrectSide = row.sl_on_correct_side ? csvBoolean(row.sl_on_correct_side) : true;
  const sortKey = row.exit_time || row.entry_time || `${entryDate(row.entry_time)} ${entryTime(row.entry_time)}`;
  return {
    draft_id: `import-history-${row.entry_order || row.exit_order || index}`,
    date: entryDate(row.entry_time || row.exit_time),
    symbol,
    market: marketFromImportedSymbol(symbol),
    setup: setupFromImportedSymbol(symbol),
    status: 'Review offen',
    direction: normalizeDirection(row.direction),
    planned_time: entryTime(row.entry_time),
    risk_amount: '',
    position_size: amountLabel(row.qty),
    planned_crv: crv === null ? '--' : display(crv),
    failed_conditions: importedFailedConditions({ hasStopLoss, hasTakeProfit, crv, slCorrectSide }),
    emotion_before: '',
    emotion_during: '',
    emotion_after: '',
    confidence_level: '',
    stress_level: '',
    focus_level: '',
    screenshot_before: '',
    screenshot_after: '',
    realized_r: '',
    result_money: amountLabel(row.net_profit),
    fees: amountLabel((parseCsvNumber(row.commission) || 0) + (parseCsvNumber(row.swap) || 0)),
    slippage: '',
    rule_compliant: false,
    violated_rule: 'Import ohne vollstaendiges TradingFreaks-Journal',
    what_went_well: '',
    improvement: 'Setup-Kriterien, Screenshots, Emotionen, RiskPlan und Review nachtragen.',
    review: `${sourceLabel}: ${row.result_type || 'Ausfuehrung'}; Entry ${row.entry || '-'}, Exit ${row.exit || '-'}.`,
    completion: 35,
    source: sourceLabel,
    imported: true,
    information_only: true,
    sort_key: sortKey,
  };
}

function monthlyTradeToJournalDraft(row, index, sourceLabel) {
  const symbol = compactImportedSymbol(row.symbol);
  const hasStopLoss = String(row.source_note || '').toLowerCase().includes('[sl');
  const sortKey = row.exit_time || row.entry_time || `${entryDate(row.entry_time)} ${entryTime(row.entry_time)}`;
  return {
    draft_id: `import-monthly-${row.order_id || index}`,
    date: entryDate(row.entry_time || row.exit_time),
    symbol,
    market: marketFromImportedSymbol(symbol),
    setup: setupFromImportedSymbol(symbol),
    status: 'Review offen',
    direction: normalizeDirection(row.direction),
    planned_time: entryTime(row.entry_time),
    risk_amount: '',
    position_size: amountLabel(row.qty),
    planned_crv: '--',
    failed_conditions: importedFailedConditions({ hasStopLoss, hasTakeProfit: false, crv: null }),
    emotion_before: '',
    emotion_during: '',
    emotion_after: '',
    confidence_level: '',
    stress_level: '',
    focus_level: '',
    screenshot_before: '',
    screenshot_after: '',
    realized_r: '',
    result_money: amountLabel(row.net_profit),
    fees: amountLabel((parseCsvNumber(row.commission) || 0) + (parseCsvNumber(row.swap) || 0)),
    slippage: '',
    rule_compliant: false,
    violated_rule: 'Import ohne vollstaendiges TradingFreaks-Journal',
    what_went_well: '',
    improvement: 'TP/CRV, Setup-Kriterien, Screenshots und Emotionen aus TradingView/Journalkontext ergaenzen.',
    review: `${sourceLabel}: ${row.source_file || 'Monatsbericht'}; Entry ${row.entry || '-'}, Exit ${row.exit || '-'}.`,
    completion: 25,
    source: sourceLabel,
    imported: true,
    information_only: true,
    sort_key: sortKey,
  };
}

function eodTradeToJournalDraft(row, index, sourceLabel) {
  const symbol = compactImportedSymbol(row.symbol);
  const failed = [
    row.criteria_failed,
    row.violated_rule,
    !row.stop_loss ? 'Stop Loss nicht im Brokerreport enthalten' : '',
    !row.take_profit ? 'Take Profit nicht im Brokerreport enthalten' : '',
    !row.planned_crv ? 'CRV nicht im Brokerreport enthalten' : '',
  ].filter(Boolean);
  const sortKey = row.exit_time_berlin || row.entry_time_berlin || `${row.trade_date_berlin} ${row.trade_time_berlin}`;
  return {
    draft_id: `import-eod-${row.account_no || 'account'}-${row.symbol || index}-${row.entry_time_utc || index}`,
    date: row.trade_date_berlin || entryDate(row.entry_time_berlin),
    symbol,
    market: row.market || marketFromImportedSymbol(symbol),
    setup: row.setup || setupFromImportedSymbol(symbol),
    status: 'Review offen',
    direction: normalizeDirection(row.direction),
    planned_time: String(row.trade_time_berlin || '').slice(0, 5) || entryTime(row.entry_time_berlin),
    risk_amount: amountLabel(row.risk_amount),
    position_size: amountLabel(row.position_size),
    planned_crv: row.planned_crv || '--',
    failed_conditions: failed.length ? failed : importedFailedConditions({ hasStopLoss: false, hasTakeProfit: false, crv: null }),
    emotion_before: row.emotion_before || '',
    emotion_during: row.emotion_during || '',
    emotion_after: row.emotion_after || '',
    confidence_level: row.confidence_level || '',
    stress_level: '',
    focus_level: '',
    screenshot_before: row.screenshot_before || '',
    screenshot_after: row.screenshot_after || '',
    realized_r: row.realized_r || '',
    result_money: amountLabel(row.result_money),
    fees: amountLabel((parseCsvNumber(row.commission) || 0) + (parseCsvNumber(row.swap) || 0)),
    slippage: row.slippage || '',
    rule_compliant: false,
    violated_rule: row.violated_rule || 'Brokerreport ohne vollstaendigen TF-Kontext',
    what_went_well: '',
    improvement: row.improvement_next_trade || 'TF-Pflichtfelder und Screenshots nachtragen.',
    review: row.review || `${sourceLabel}: Ausfuehrungsdaten importiert, TF-Kontext offen.`,
    completion: 30,
    source: sourceLabel,
    imported: true,
    information_only: true,
    sort_key: sortKey,
  };
}

function journalDraftsFromCsv(text, source) {
  const rows = csvToObjects(text);
  if (source.type === 'reconstructed') return rows.map((row, index) => historyTradeToJournalDraft(row, index, source.label));
  if (source.type === 'monthly') return rows.map((row, index) => monthlyTradeToJournalDraft(row, index, source.label));
  return rows.map((row, index) => eodTradeToJournalDraft(row, index, source.label));
}

function sortJournalEntries(entries) {
  return [...entries].sort((a, b) => String(b.sort_key || b.date || '').localeCompare(String(a.sort_key || a.date || '')));
}

function mergeJournalEntries(journalDrafts, importedEntries) {
  const copiedImportIds = new Set(journalDrafts.map((draft) => draft.source_import_id).filter(Boolean));
  return sortJournalEntries([
    ...journalDrafts,
    ...importedEntries.filter((entry) => !copiedImportIds.has(entry.draft_id)),
  ]);
}

function reviewQueuePriority(entry) {
  if (entry.lifecycle_status === 'open' || entry.status === 'Trade laeuft') return 0;
  if (entry.status === 'Review offen') return 1;
  if (entry.imported) return 2;
  if (entry.status === 'Abgeschlossen') return 4;
  return 3;
}

function sortReviewQueueEntries(entries) {
  return [...entries].sort((a, b) => {
    const priorityDiff = reviewQueuePriority(a) - reviewQueuePriority(b);
    if (priorityDiff) return priorityDiff;
    return String(b.sort_key || b.date || '').localeCompare(String(a.sort_key || a.date || ''));
  });
}

function isActionableReviewEntry(entry) {
  if (entry.imported) return false;
  if (entry.lifecycle_status === 'open' || entry.status === 'Trade laeuft') return true;
  if (entry.status === 'Review offen') return true;
  if (entry.status !== 'Abgeschlossen') return true;
  return !entry.realized_r || !entry.screenshot_before || !entry.screenshot_after || !entry.review;
}

function entryDateObject(entry) {
  const candidates = [entry.sort_key, entry.date].filter(Boolean);
  for (const value of candidates) {
    const text = String(value).trim();
    const isoMatch = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (isoMatch) {
      const [, year, month, day] = isoMatch;
      return new Date(Number(year), Number(month) - 1, Number(day));
    }
    const germanMatch = text.match(/^(\d{2})\.(\d{2})\.(\d{4})/);
    if (germanMatch) {
      const [, day, month, year] = germanMatch;
      return new Date(Number(year), Number(month) - 1, Number(day));
    }
    const parsed = new Date(text);
    if (!Number.isNaN(parsed.getTime())) return parsed;
  }
  return null;
}

function pad2(value) {
  return String(value).padStart(2, '0');
}

function isoWeekKey(date) {
  if (!date) return '';
  const utc = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = utc.getUTCDay() || 7;
  utc.setUTCDate(utc.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(utc.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((utc - yearStart) / 86400000) + 1) / 7);
  return `${utc.getUTCFullYear()}-W${pad2(week)}`;
}

function periodKeyForEntry(entry, periodType) {
  const date = entryDateObject(entry);
  if (!date) return '';
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  if (periodType === 'week') return isoWeekKey(date);
  if (periodType === 'month') return `${year}-${pad2(month)}`;
  if (periodType === 'quarter') return `${year}-Q${Math.floor((month - 1) / 3) + 1}`;
  if (periodType === 'year') return String(year);
  return 'all';
}

function periodLabel(key, periodType) {
  if (!key || key === 'all') return 'Alle Zeitraeume';
  if (periodType === 'week') return `KW ${key.split('-W')[1]} / ${key.split('-W')[0]}`;
  if (periodType === 'month') {
    const [year, month] = key.split('-');
    return `${month}.${year}`;
  }
  if (periodType === 'quarter') return key.replace('-Q', ' Q');
  return key;
}

function tradeFilterOptions(entries, periodType) {
  if (periodType === 'all') return [];
  return [...new Set(entries.map((entry) => periodKeyForEntry(entry, periodType)).filter(Boolean))]
    .sort((a, b) => b.localeCompare(a));
}

function filterJournalEntries(entries, filters) {
  return entries.filter((entry) => {
    if (filters.mode && filters.mode !== 'all' && tradeAccountMode(entry) !== filters.mode) return false;
    if (filters.market !== 'all' && (entry.market || marketFromImportedSymbol(entry.symbol)) !== filters.market) return false;
    if (filters.periodType === 'all') return true;
    if (!filters.periodValue) return true;
    return periodKeyForEntry(entry, filters.periodType) === filters.periodValue;
  });
}

function uniqueValues(list, key) {
  return [...new Set(list.map((item) => item[key]).filter(Boolean))].sort();
}

function filterChatUpdates(updates, filters) {
  return updates.filter((update) => {
    if (filters.session !== 'all' && update.session !== filters.session) return false;
    if (filters.asset !== 'all' && !(update.assets || []).includes(filters.asset)) return false;
    if (filters.theme !== 'all' && !(update.themes || []).includes(filters.theme)) return false;
    return true;
  });
}

function isTodayUpdate(update) {
  const updateKey = berlinDateKey(update?.sort_key || update?.exported_at || update?.timestamp);
  const todayKey = berlinDateKey(new Date().toISOString());
  return Boolean(updateKey && updateKey === todayKey);
}

function berlinDateKey(value) {
  if (!value) return '';
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Europe/Berlin',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(date);
  }
  const germanMatch = String(value).match(/(\d{2})\.(\d{2})\.(\d{4})/);
  if (germanMatch) return `${germanMatch[3]}-${germanMatch[2]}-${germanMatch[1]}`;
  const isoMatch = String(value).match(/(\d{4}-\d{2}-\d{2})/);
  return isoMatch ? isoMatch[1] : '';
}

function dateKeyLabel(key) {
  const match = String(key || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return key || '--';
  return `${match[3]}.${match[2]}.${match[1]}`;
}

function updateTimeValue(update) {
  const candidates = [update?.sort_key, update?.exported_at, update?.timestamp].filter(Boolean);
  for (const value of candidates) {
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) return date.getTime();
    const germanMatch = String(value).match(/(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/);
    if (germanMatch) {
      const [, day, month, year, hour = '0', minute = '0'] = germanMatch;
      return new Date(`${year}-${month}-${day}T${pad2(Number(hour))}:${minute}:00+02:00`).getTime();
    }
  }
  return 0;
}

function latestUpdateFreshness(updates) {
  const latest = [...updates].sort((a, b) => updateTimeValue(b) - updateTimeValue(a))[0];
  const latestKey = berlinDateKey(latest?.sort_key || latest?.exported_at || latest?.timestamp);
  const todayKey = berlinDateKey(new Date().toISOString());
  return {
    latest,
    latestKey,
    todayKey,
    isToday: Boolean(latestKey && latestKey === todayKey),
  };
}

function chatCoverageItems(feed, updates) {
  if (Array.isArray(feed?.chat_coverage) && feed.chat_coverage.length) return feed.chat_coverage;
  const grouped = new Map();
  updates.forEach((update) => {
    const title = update.canonical_chat_title || update.chat_title || 'Unbekannter Chat';
    const existing = grouped.get(title) || {
      canonical_title: title,
      title: update.chat_title || title,
      url: update.chat_url || '',
      required: Boolean(update.required_chat_source),
      status: 'imported',
      latest_timestamp: '',
      latest_sort_key: '',
      update_count: 0,
      sessions: [],
      assets: [],
      themes: [],
    };
    existing.update_count += 1;
    if (!existing.latest_sort_key || String(update.sort_key || '') > existing.latest_sort_key) {
      existing.latest_sort_key = update.sort_key || '';
      existing.latest_timestamp = update.timestamp || '';
    }
    existing.sessions = [...new Set([...existing.sessions, update.session].filter(Boolean))].sort();
    existing.assets = [...new Set([...existing.assets, ...(update.assets || [])])].sort();
    existing.themes = [...new Set([...existing.themes, ...(update.themes || [])])].sort();
    grouped.set(title, existing);
  });
  return [...grouped.values()].sort((a, b) => Number(b.required) - Number(a.required) || a.canonical_title.localeCompare(b.canonical_title));
}

function chatCoverageClass(item) {
  if (!item || item.status === 'missing') return 'danger';
  const latestKey = berlinDateKey(item.latest_sort_key || item.latest_timestamp || item.exported_at);
  const todayKey = berlinDateKey(new Date().toISOString());
  if (item.required && latestKey && latestKey !== todayKey) return 'watch';
  return 'ok';
}

function latestCoverageKey(items) {
  const latest = [...items]
    .filter((item) => item.status !== 'missing')
    .sort((a, b) => updateTimeValue({ sort_key: b.latest_sort_key, timestamp: b.latest_timestamp, exported_at: b.exported_at }) -
      updateTimeValue({ sort_key: a.latest_sort_key, timestamp: a.latest_timestamp, exported_at: a.exported_at }))[0];
  return berlinDateKey(latest?.latest_sort_key || latest?.latest_timestamp || latest?.exported_at);
}

function coverageStatusText(item) {
  if (item.status === 'missing') return 'Fehlt';
  const statusClass = chatCoverageClass(item);
  if (statusClass === 'watch') return 'Import veraltet';
  return item.required ? 'Pflicht-Chat aktiv' : 'Zusatzquelle aktiv';
}

function secondsSince(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return Math.max(0, (Date.now() - date.getTime()) / 1000);
}

function chatIdeaSetup(symbol, update) {
  const defaults = inferImportDefaults('', symbol, '');
  const themes = update.themes || [];
  if (defaults.market === 'us_stock') {
    return update.session === 'US Open' || themes.includes('Tech/AI/Semis')
      ? 'US Newstrade Breakout'
      : 'Rectangle Scalping';
  }
  if (defaults.market === 'forex') {
    return themes.includes('Kalender/Event') || update.session === 'Breaking News'
      ? 'FX Wirtschaftsdaten'
      : 'FX Trendlinie';
  }
  if (defaults.market === 'index') {
    return symbol === 'DE40' ? 'DAX Abpraller' : 'SR Reversal';
  }
  if (defaults.market === 'commodity') return 'SR Reversal';
  return defaults.setup_name;
}

function chatIdeaPlannedTime(update) {
  if (update.session === 'Daily Update') return '08:30';
  if (update.session === 'Europe Session') return '10:15';
  if (update.session === 'US Open') return '15:45';
  const match = String(update.timestamp || '').match(/(\d{1,2}):(\d{2})/);
  if (!match) return '15:45';
  const minutes = Math.min(21 * 60 + 30, Number(match[1]) * 60 + Number(match[2]) + 15);
  return `${pad2(Math.floor(minutes / 60))}:${pad2(minutes % 60)}`;
}

function chatIdeaScore(update, updateIndex) {
  const sessionScore = {
    'Breaking News': 24,
    'US Open': 22,
    'Europe Session': 18,
    'Daily Update': 14,
  }[update.session] || 10;
  const sourceScore = update.required_chat_source ? 18 : update.external_context ? -8 : 4;
  const updateKey = berlinDateKey(update.sort_key || update.exported_at || update.timestamp);
  const todayKey = berlinDateKey(new Date().toISOString());
  const todayBonus = updateKey === todayKey ? 90 : 0;
  const historicalPenalty = updateKey && updateKey !== todayKey ? 45 : 0;
  return (
    Math.max(0, 90 - updateIndex) +
    todayBonus -
    historicalPenalty +
    sessionScore +
    sourceScore +
    (update.required_checks || []).length * 8 +
    (update.themes || []).length * 4 +
    (update.assets || []).length * 2 -
    (update.blockers || []).length * 3
  );
}

function buildChatTradeIdeas(updates) {
  const grouped = new Map();
  updates.forEach((update, updateIndex) => {
    (update.assets || []).forEach((symbol) => {
      const defaults = inferImportDefaults('', symbol, '');
      const setupName = chatIdeaSetup(symbol, update);
      const key = `${symbol}-${update.session}-${setupName}`;
      const existing = grouped.get(key);
      const score = chatIdeaScore(update, updateIndex);
      const idea = {
        idea_id: key,
        symbol,
        market: defaults.market,
        setup_name: setupName,
        session: update.session,
        planned_time: chatIdeaPlannedTime(update),
        timestamp: update.timestamp,
        score,
        source_chat: update.chat_title,
        source_type: update.required_chat_source ? 'ChatGPT Pflicht-Update-Chat' : update.external_context ? 'Tagesaktueller Zusatzkontext' : 'ChatGPT Zusatzkontext',
        update_id: update.id,
        themes: update.themes || [],
        required_checks: update.required_checks || [],
        blockers: update.blockers || [],
        summary: update.summary,
      };
      if (!existing || idea.score > existing.score) grouped.set(key, idea);
    });
  });
  return [...grouped.values()]
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);
}

function chatIdeaToCandidate(idea) {
  return makeCandidate({
    candidate_id: `chat-idea-${Date.now()}-${idea.symbol}-${Math.random().toString(16).slice(2)}`,
    symbol: idea.symbol,
    market: idea.market,
    setup_name: idea.setup_name,
    direction: 'conditional',
    planned_time: idea.planned_time,
    catalyst: `ChatGPT ${idea.session} | ${idea.timestamp}`,
    notes: [
      `Potentieller Pruefkandidat aus ${idea.source_chat} (${idea.source_type}).`,
      `Themen: ${idea.themes.join(', ') || 'manuell pruefen'}.`,
      `Pflichtchecks: ${idea.required_checks.join(' | ') || 'aus Update ableiten'}.`,
      `Blocker: ${idea.blockers.join(' | ') || 'keine harte Blockerkennung im Text'}.`,
      `Kontext: ${idea.summary}`,
    ].join('\n'),
    conditions: makeConditions(false),
  });
}

function updateAssetToTradeIdea(update, symbol, updateIndex = 0) {
  const defaults = inferImportDefaults('', symbol, '');
  return {
    idea_id: `selected-update-${update.id}-${symbol}`,
    symbol,
    market: defaults.market,
    setup_name: chatIdeaSetup(symbol, update),
    session: update.session,
    planned_time: chatIdeaPlannedTime(update),
    timestamp: update.timestamp,
    score: chatIdeaScore(update, updateIndex),
    source_chat: update.chat_title,
    source_type: update.required_chat_source
      ? 'ChatGPT Pflicht-Update-Chat'
      : update.external_context
        ? 'Tagesaktueller Zusatzkontext'
        : 'ChatGPT Zusatzkontext',
    update_id: update.id,
    themes: update.themes || [],
    required_checks: update.required_checks || [],
    blockers: update.blockers || [],
    summary: update.summary,
  };
}

async function loadImportedJournalTrades() {
  const batches = await Promise.all(
    importedJournalSources.map(async (source) => {
      try {
        const response = await fetch(source.url);
        if (!response.ok) return [];
        const text = await response.text();
        return journalDraftsFromCsv(text, source);
      } catch {
        return [];
      }
    }),
  );
  const seen = new Set();
  return sortJournalEntries(batches.flat()).filter((entry) => {
    if (seen.has(entry.draft_id)) return false;
    seen.add(entry.draft_id);
    return true;
  });
}

async function loadManualJournalDrafts() {
  try {
    const response = await fetch(manualJournalDraftsUrl);
    if (!response.ok) return [];
    const payload = await response.json();
    const drafts = Array.isArray(payload) ? payload : payload.drafts || [];
    return drafts.map(normalizeJournalDraft);
  } catch {
    return [];
  }
}

async function requestChatUpdateFeed() {
  const response = await fetch(`${chatUpdateFeedUrl}?refresh=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Update feed failed: ${response.status}`);
  const feed = await response.json();
  return { updates: [], generated_at: '', update_count: 0, chat_count: 0, chat_coverage: [], ...feed };
}

async function requestLiveFeedStatus() {
  const response = await fetch(`${liveFeedStatusUrl}?refresh=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Live status failed: ${response.status}`);
  return response.json();
}

async function requestLiveAdapterConfigStatus() {
  const response = await fetch(`${liveAdapterConfigStatusUrl}?refresh=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Live adapter config failed: ${response.status}`);
  return response.json();
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 1800) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function requestJournalStore() {
  const response = await fetchWithTimeout(`${journalStoreApiUrl}?refresh=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Journal store failed: ${response.status}`);
  return response.json();
}

async function saveJournalStore(payload) {
  const response = await fetchWithTimeout(
    journalStoreApiUrl,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    },
    3000,
  );
  if (!response.ok) throw new Error(`Journal store save failed: ${response.status}`);
  return response.json();
}

function parseRealizedR(value) {
  const text = String(value ?? '').trim();
  if (!text) return null;
  const parsed = Number(text.replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : null;
}

function journalCompletion(journal) {
  const required = [
    journal.emotion_before,
    journal.screenshot_before,
    journal.screenshot_after,
    journal.realized_r,
    journal.review,
  ];
  if (!journal.rule_compliant) required.push(journal.violated_rule);
  const filled = required.filter((value) => String(value || '').trim()).length;
  return Math.round((filled / required.length) * 100);
}

function draftStatusLabel(status) {
  if (status === 'Trade laeuft') return 'Trade laeuft';
  if (status === 'Abgeschlossen') return 'Abgeschlossen';
  return statusLabel(status);
}

function reviewQueueStatusLabel(entry) {
  if (entry.lifecycle_status === 'open' || entry.status === 'Trade laeuft') return 'Laufend';
  if (entry.status === 'Abgeschlossen') return 'Abgeschlossen';
  if (entry.imported) return 'Import-Review offen';
  if (entry.status === 'Review offen') return 'Review offen';
  return draftStatusLabel(entry.status);
}

function reviewQueueStatusClass(entry) {
  if (entry.lifecycle_status === 'open' || entry.status === 'Trade laeuft') return 'watch';
  if (entry.status === 'Abgeschlossen') return 'ok';
  if (entry.imported || entry.status === 'Review offen') return 'danger';
  return statusClass(entry.status);
}

function journalFromDraft(draft) {
  if (!draft) return defaultJournal;
  return {
    emotion_before: draft.emotion_before || defaultJournal.emotion_before,
    emotion_during: draft.emotion_during || '',
    emotion_after: draft.emotion_after || '',
    confidence_level: draft.confidence_level || defaultJournal.confidence_level,
    stress_level: draft.stress_level || defaultJournal.stress_level,
    focus_level: draft.focus_level || defaultJournal.focus_level,
    screenshot_before: draft.screenshot_before || '',
    screenshot_after: draft.screenshot_after || '',
    exit_price: draft.exit_price || '',
    exit_reason: draft.exit_reason || '',
    realized_r: draft.realized_r || '',
    result_money: draft.result_money || '',
    fees: draft.fees || '',
    slippage: draft.slippage || '',
    rule_compliant: typeof draft.rule_compliant === 'boolean' ? draft.rule_compliant : true,
    violated_rule: draft.violated_rule || '',
    what_went_well: draft.what_went_well || '',
    improvement: draft.improvement || '',
    review: draft.review || '',
  };
}

function editableReviewDraftFromImported(importedDraft) {
  const now = new Date().toISOString();
  return {
    ...importedDraft,
    draft_id: `review-${importedDraft.draft_id}`,
    source_import_id: importedDraft.draft_id,
    imported: false,
    status: 'Review offen',
    lifecycle_status: 'closed',
    started_at: importedDraft.started_at || importedDraft.sort_key || now,
    closed_at: importedDraft.closed_at || importedDraft.sort_key || '',
    source: `${importedDraft.source || 'Import'} | Review bearbeitbar`,
    failed_conditions: [
      'Aus Import in bearbeitbaren Review uebernommen',
      ...(importedDraft.failed_conditions || []),
    ],
    completion: Math.max(importedDraft.completion || 0, journalCompletion(journalFromDraft(importedDraft))),
    sort_key: importedDraft.sort_key || now,
    information_only: true,
  };
}

function eventDateParts(timestamp) {
  const date = new Date(timestamp || Date.now());
  const safeDate = Number.isNaN(date.getTime()) ? new Date() : date;
  return {
    iso: safeDate.toISOString(),
    date: new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(safeDate),
    time: safeDate.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }),
  };
}

function normalizeExternalTradeEvent(rawPayload) {
  const payload = rawPayload?.event && typeof rawPayload.event === 'object' ? rawPayload.event : rawPayload;
  if (!payload || typeof payload !== 'object') throw new Error('Event muss ein JSON-Objekt sein.');
  return {
    ...payload,
    event_type: String(payload.event_type || payload.type || '').trim(),
    trade_id: String(payload.trade_id || payload.order_id || payload.id || '').trim(),
    symbol: compactImportedSymbol(payload.symbol || payload.ticker || ''),
    direction: normalizeDirection(payload.direction || payload.side),
    market: payload.market || marketFromImportedSymbol(payload.symbol || payload.ticker || ''),
  };
}

function plannedCrvFromEvent(event) {
  const entry = toNumber(event.entry);
  const stop = toNumber(event.stop_loss);
  const take = toNumber(event.take_profit);
  if (!entry || !stop || !take) return '--';
  const risk = Math.abs(entry - stop);
  const reward = Math.abs(take - entry);
  if (!risk || !reward) return '--';
  return display(reward / risk);
}

function realizedRFromEventDraft(event, draft) {
  const exit = toNumber(event.exit_price || event.price);
  const entry = toNumber(draft.entry);
  const stop = toNumber(draft.stop_loss);
  if (!exit || !entry || !stop || entry === stop) return '';
  const risk = Math.abs(entry - stop);
  const rawR = draft.direction === 'short' ? (entry - exit) / risk : (exit - entry) / risk;
  return Number.isFinite(rawR) ? display(rawR) : '';
}

function realizedRFromJournalFacts(facts = {}) {
  const money = parseJournalNumber(facts.result_money);
  const riskAmount = parseJournalNumber(facts.risk_amount);
  if (money !== null && riskAmount !== null && Math.abs(riskAmount) > 0) {
    return money / Math.abs(riskAmount);
  }

  const exit = parseJournalNumber(facts.exit_price);
  const entry = parseJournalNumber(facts.entry);
  const stop = parseJournalNumber(facts.stop_loss);
  if (exit !== null && entry !== null && stop !== null && entry !== stop) {
    const riskPerUnit = Math.abs(entry - stop);
    const rawR = facts.direction === 'short' ? (entry - exit) / riskPerUnit : (exit - entry) / riskPerUnit;
    return Number.isFinite(rawR) ? rawR : null;
  }

  const exitReason = String(facts.exit_reason || '').toLowerCase();
  if (exitReason.includes('stop loss')) return -1;

  const plannedCrv = parseJournalNumber(facts.planned_crv);
  if (exitReason.includes('take profit') && plannedCrv !== null) return plannedCrv;

  return null;
}

function realizedRLabelFromJournalFacts(facts = {}) {
  const realized = realizedRFromJournalFacts(facts);
  return realized === null ? '' : display(realized);
}

function exitReasonFromEventType(eventType) {
  if (eventType === 'closed_stop_loss') return 'Stop Loss';
  if (eventType === 'closed_take_profit') return 'Take Profit';
  if (eventType === 'closed_manual') return 'Manuell geschlossen';
  return 'Trade geschlossen';
}

function findDraftByExternalTradeId(drafts, tradeId) {
  if (!tradeId) return null;
  const expectedDraftId = `event-${tradeId}`;
  return drafts.find((draft) => draft.external_trade_id === tradeId || draft.draft_id === expectedDraftId) || null;
}

function buildJournalMetrics(drafts) {
  const realized = drafts.map((draft) => parseRealizedR(draft.realized_r)).filter((value) => value !== null);
  const knownCompliance = drafts.filter((draft) => typeof draft.rule_compliant === 'boolean');
  const compliant = knownCompliance.filter((draft) => draft.rule_compliant === true).length;
  const avgR = realized.length ? realized.reduce((sum, value) => sum + value, 0) / realized.length : 0;
  const ruleRate = knownCompliance.length ? (compliant / knownCompliance.length) * 100 : 0;
  const wins = realized.filter((value) => value > 0).length;
  const winRate = realized.length ? (wins / realized.length) * 100 : 0;
  const blockers = drafts.reduce((sum, draft) => sum + (draft.failed_conditions?.length || 0), 0);
  return { avgR, ruleRate, winRate, blockers, count: drafts.length, knownCompliance: knownCompliance.length };
}

function setupGuide(candidate) {
  const setup = candidate?.setup_name || '';
  const guides = {
    'US Newstrade Breakout': {
      focus: 'News-Katalysator plus Opening Drive, VWAP-Seite und enge Konsolidierung.',
      entry: 'Entry nahe Ausbruchslevel nach Momentum und Volumenbestaetigung.',
      confirmations: ['News eindeutig', 'Kurs in News-Richtung', 'VWAP-Seite stimmt', 'Korrektur max. 1/3', 'RVOL > 1,5'],
      blockers: ['Mixed News', 'nur Volatilitaet', 'Entry zu weit weg', 'kein Stop/TP', 'US Open erste 5 Min.'],
      exit: 'TP/Exit vor Trade; Intraday spaetestens Handelsschluss.',
    },
    'Rectangle Scalping': {
      focus: 'Trendfortsetzung nach klarer Momentumstrecke und horizontaler Seitwaertsphase.',
      entry: 'Buy/Sell Stop knapp ausserhalb der Rectangle-Kante.',
      confirmations: ['Momentum vor Korrektur', 'mind. 6 Kerzen', 'horizontal klar', 'Korrektur max. 1/3', 'SL andere Rectangle-Seite'],
      blockers: ['Volatilitaet ohne Richtung', 'schraeges Pattern', 'illiquider M1', 'CRV < 1:1'],
      exit: 'CRV 1:1, optional Teilverkauf oder EMA9-Trailing.',
    },
    'Premarket High/Low': {
      focus: 'US-Aktie mit News, sauberer Vorboersenstruktur und starkem Opening Drive.',
      entry: 'Durchbruch durch vorboersliches Hoch/Tief nahe am Level.',
      confirmations: ['News-Katalysator', 'Gap > 3%', 'Opening Drive', 'Konsolidierung vor Level', 'M1 liquide'],
      blockers: ['Vormarkt-Trade', 'kein Katalysator', 'Entry weit vom Level', 'Gaps im M1'],
      exit: 'CRV ca. 1:1, SL an lokaler Struktur, Intraday schliessen.',
    },
    'US Newstrade Reversal': {
      focus: 'Rueckkehr Richtung News/VWAP nach Uebertreibung gegen die erwartete Richtung.',
      entry: 'Boden/Top, Reversal-Formation, EMA9 oder starker H4/D1/W1-Level.',
      confirmations: ['deutlich weg vom VWAP', 'Boden/Top erkennbar', 'Platz bis Ziel', 'CRV >= 1:1'],
      blockers: ['ungeordnete Bewegung', 'Hoffnungs-Entry', 'kein Platz zum VWAP', 'kein Stop'],
      exit: 'VWAP oder naechstes technisches Level.',
    },
    'Reversal ohne News': {
      focus: 'Technische Mean-Reversion bei liquider US-Aktie ohne News und ohne starkes News-Volumen.',
      entry: 'EMA9-Schluss plus Folgekerze mit neuem Hoch/Tief.',
      confirmations: ['kein News-Indiz', 'weit vom VWAP', 'Fib-Ziel frei', 'CRV > 1:1', 'nur einmal pro Aktie/Tag'],
      blockers: ['relevante News', 'nach 20:00 neuer Trade', 'kein 38,2%-Platz', 'Long/Short-Ungleichgewicht'],
      exit: '50%-Retracement oder VWAP, je nachdem was naeher liegt.',
    },
    'FX Wirtschaftsdaten': {
      focus: 'G8/G10-Risikoevent erst nach Veroeffentlichung und eindeutiger Datenreaktion.',
      entry: 'Market ins Momentum oder Ruecklauf, z. B. 38,2% der initialen Bewegung.',
      confirmations: ['grosse Erwartungsabweichung', 'Daten eindeutig', 'Momentum > 20 Pips', 'kein Vorab-Trade'],
      blockers: ['gemischte Daten', 'kein Momentum', 'Buy/Sell Stop gleichzeitig', 'Spread unklar'],
      exit: 'Scalp/Daytrade meist 20-50 Pips, CRV ca. 1:1.',
    },
    'FX Trendlinie': {
      focus: 'Abpraller am dritten Auflagepunkt einer H4/D1/W1-Trendlinie.',
      entry: 'Buy/Sell Limit 5-10 Pips vor der Trendlinie.',
      confirmations: ['mind. zwei Auflagepunkte', 'ruhiger Markt', 'kein Risikoevent', 'Sentiment nicht extrem dagegen'],
      blockers: ['subjektive Linie', 'frische News', 'Spread zu hoch', 'Event am selben Tag'],
      exit: 'SL/TP 20-50 Pips, offene Limits taggleich loeschen.',
    },
    'DAX Abpraller': {
      focus: 'Technischer Abpraller an starker H4/D1/W1-Unterstuetzung oder Widerstand.',
      entry: 'Limit ca. 10-15 Punkte vor Zone.',
      confirmations: ['starke Zone', 'Kalender geprueft', 'kein nahes Risikoevent', 'CRV >= 1:1'],
      blockers: ['schwache Zone', 'News-nahe', 'kein Screenshot', 'keine klare SL/TP-Planung'],
      exit: 'Scalp ca. 50 Punkte, Daytrade ca. 100 Punkte, je nach Plan.',
    },
    'SR Reversal': {
      focus: 'Abpraller oder Reversal an starken historischen H4/D1/W1-Zonen.',
      entry: 'Limit oder bestaetigter Reversal-Einstieg nahe Zone.',
      confirmations: ['Zone < 0,5% entfernt', 'kein Event 24h', 'M5-Bestaetigung', 'CRV >= 1:1'],
      blockers: ['Eventnaehe', 'unklares Level', 'Spread/Kosten zu hoch', 'kein Stop'],
      exit: 'FX 20-50 Pips, Index 50-200 Punkte, immer mit geplantem Exit.',
    },
  };
  return guides[setup] || guides['SR Reversal'];
}

function buildJournalSteps(journal, activeResult) {
  return [
    {
      label: 'Plan',
      done: activeResult.failed.length === 0,
      detail: activeResult.failed.length ? firstBlockingReason(activeResult) : 'Setup, Risiko und CRV vollstaendig.',
    },
    {
      label: 'Vorher-Bild',
      done: Boolean(journal.screenshot_before),
      detail: journal.screenshot_before ? 'Screenshot vorhanden.' : 'Chart vor Trade einfuegen.',
    },
    {
      label: 'Ergebnis',
      done: Boolean(journal.realized_r || journal.result_money),
      detail: journal.realized_r || journal.result_money ? 'Ergebnis erfasst.' : 'R oder Geldbetrag eintragen.',
    },
    {
      label: 'Nachher-Bild',
      done: Boolean(journal.screenshot_after),
      detail: journal.screenshot_after ? 'Screenshot vorhanden.' : 'Chart nach Trade einfuegen.',
    },
    {
      label: 'Review',
      done: Boolean(journal.review && (journal.rule_compliant || journal.violated_rule)),
      detail: journal.review ? 'Review begonnen.' : 'Kurzes Fazit und Regelcheck erfassen.',
    },
  ];
}

function buildReviewInsights(entries) {
  const actionEntries = entries.filter((entry) => !entry.imported);
  const importEntries = entries.filter((entry) => entry.imported);
  const withMoney = entries
    .map((entry) => ({ entry, money: parseCsvNumber(entry.result_money) }))
    .filter(({ money }) => money !== null);
  const totalMoney = withMoney.reduce((sum, item) => sum + item.money, 0);
  const winners = withMoney.filter(({ money }) => money > 0).length;
  const losers = withMoney.filter(({ money }) => money < 0).length;
  const runningReviews = actionEntries.filter((entry) => entry.lifecycle_status === 'open' || entry.status === 'Trade laeuft').length;
  const editableReviews = actionEntries.filter((entry) => entry.status === 'Review offen').length;
  const importReviews = importEntries.filter((entry) => entry.status !== 'Abgeschlossen').length;
  const completedReviews = actionEntries.filter((entry) => entry.status === 'Abgeschlossen').length;
  const openReviews = actionEntries.filter(isActionableReviewEntry).length;
  const noScreenshots = actionEntries.filter((entry) => !entry.screenshot_before || !entry.screenshot_after).length;
  const noRealizedR = actionEntries.filter((entry) => !entry.realized_r).length;
  const importNoScreenshots = importEntries.filter((entry) => !entry.screenshot_before || !entry.screenshot_after).length;
  const importNoRealizedR = importEntries.filter((entry) => !entry.realized_r).length;
  const symbolMap = withMoney.reduce((map, { entry, money }) => {
    const symbol = entry.symbol || 'UNDEFINED';
    const current = map.get(symbol) || { symbol, trades: 0, net: 0, losses: 0 };
    current.trades += 1;
    current.net += money;
    if (money < 0) current.losses += 1;
    map.set(symbol, current);
    return map;
  }, new Map());
  const symbols = [...symbolMap.values()].sort((a, b) => a.net - b.net);
  const weakestSymbols = symbols.slice(0, 5);
  const mostActiveSymbols = [...symbolMap.values()].sort((a, b) => b.trades - a.trades).slice(0, 5);
  const blockerSource = actionEntries.length ? actionEntries : entries;
  const blockerMap = blockerSource.reduce((map, entry) => {
    (entry.failed_conditions || []).forEach((condition) => {
      map.set(condition, (map.get(condition) || 0) + 1);
    });
    return map;
  }, new Map());
  const topBlockers = [...blockerMap.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count]) => ({ name, count }));

  return {
    totalMoney,
    winners,
    losers,
    winRateCash: withMoney.length ? (winners / withMoney.length) * 100 : 0,
    moneySample: withMoney.length,
    openReviews,
    runningReviews,
    editableReviews,
    importReviews,
    actionEntries: actionEntries.length,
    importedEntries: importEntries.length,
    completedReviews,
    noScreenshots,
    noRealizedR,
    importNoScreenshots,
    importNoRealizedR,
    weakestSymbols,
    mostActiveSymbols,
    topBlockers,
  };
}

function technicalTradeRating(entry) {
  const failed = entry.failed_conditions || [];
  const joinedFailed = failed.join(' | ').toLowerCase();
  const hasScreenshots = Boolean(entry.screenshot_before && entry.screenshot_after);
  const hasResult = Boolean(entry.realized_r || entry.result_money);

  if (joinedFailed.includes('verlust groesser') || joinedFailed.includes('metall-exposure')) {
    return {
      label: 'Risiko auffaellig',
      className: 'danger',
      reason: failed.find((item) => item.includes('Verlust groesser') || item.includes('Metall-Exposure')) || 'Positions-/Risikoreview erforderlich.',
    };
  }
  if (entry.imported) {
    return {
      label: 'Technisch offen',
      className: 'watch',
      reason: 'Brokerdaten enthalten keine Chart-Setups, Screenshots, Emotionen und vollstaendige SL/TP/CRV-Planung.',
    };
  }
  if (entry.rule_compliant === false) {
    return {
      label: 'Regelabweichung',
      className: 'danger',
      reason: entry.violated_rule || failed[0] || 'Regelabweichung pruefen.',
    };
  }
  if (!hasScreenshots) {
    return {
      label: 'Doku offen',
      className: 'watch',
      reason: 'Vorher-/Nachher-Screenshot fehlt.',
    };
  }
  if (!hasResult) {
    return {
      label: 'Ergebnis offen',
      className: 'watch',
      reason: 'R oder Geld-Ergebnis fehlt.',
    };
  }
  if (failed.length) {
    return {
      label: 'Blocker offen',
      className: 'watch',
      reason: failed[0],
    };
  }
  return {
    label: 'Dokumentiert',
    className: 'ok',
    reason: 'Journalfelder fuer Review ausreichend gefuellt.',
  };
}

function resultClass(entry) {
  const money = parseCsvNumber(entry.result_money);
  if (money === null) return 'watch';
  if (money > 0) return 'ok';
  if (money < 0) return 'danger';
  return 'watch';
}

function resultLabel(entry) {
  if (entry.result_money) return `${entry.result_money} EUR`;
  if (entry.realized_r) return `${entry.realized_r} R`;
  return '--';
}

function hasTradeTicket(candidate) {
  return Boolean(candidate?.entry && candidate?.stop_loss && candidate?.take_profit);
}

function buildDailyWorkflow({ activeCandidate, activeResult, context, contextIssues, journalScore, reviewInsights }) {
  const hasSymbol = Boolean(activeCandidate?.symbol?.trim());
  const hasSetup = Boolean(activeCandidate?.setup_name);
  const hasDirection = activeCandidate?.direction !== 'conditional';
  const ticketReady = hasTradeTicket(activeCandidate) && activeResult.riskPerUnit > 0 && activeResult.crv >= 1;
  const preChecksReady = activeResult.completionScore === 100;
  const manualReviewReady = activeResult.status === 'Manuelle Pruefung';
  return [
    {
      id: 'day',
      title: 'Tagesstatus pruefen',
      view: 'desk',
      done: contextIssues.length === 0,
      action: contextIssues.length ? contextIssues[0] : 'Tageslimits und Psychologie blockieren nicht.',
      detail: 'Wenn Tagesverlust, Wochenverlust, FOMO, Revenge oder Verlustserie aktiv sind: keine neue Pruefung starten.',
    },
    {
      id: 'asset',
      title: 'Asset und Setup waehlen',
      view: 'desk',
      done: hasSymbol && hasSetup,
      action: hasSymbol && hasSetup ? `${activeCandidate.symbol} | ${activeCandidate.setup_name}` : 'Watchlist importieren oder Asset manuell waehlen.',
      detail: 'Hier wird entschieden, welches TradingFreaks-Setup ueberhaupt zur Marktlage passt.',
    },
    {
      id: 'direction',
      title: 'Long/Short nur bei Bestaetigung',
      view: 'desk',
      done: hasDirection,
      action: hasDirection ? directionLabel(activeCandidate.direction) : 'Richtung bleibt Bedingt, bis Setup und Marktphase klar sind.',
      detail: 'Long/Short ist erst pruefbar, wenn Momentum, Zone, VWAP/Level oder Eventreaktion zur Setup-Logik passen.',
    },
    {
      id: 'ticket',
      title: 'Entry, Stop, Ziel, Risiko',
      view: 'desk',
      done: ticketReady,
      action: ticketReady ? `CRV ${display(activeResult.crv)} | Risiko ${display(activeResult.riskAmount)}` : 'Entry, Stop Loss, Take Profit und CRV >= 1:1 eintragen.',
      detail: 'Kein Stop Loss oder kein Exit-Plan bedeutet: nicht handeln.',
    },
    {
      id: 'checks',
      title: '5 Pre-Checks abschliessen',
      view: 'desk',
      done: preChecksReady,
      action: `${activeResult.completionScore}% erledigt`,
      detail: 'Trading Setup, beste Gelegenheit, Trade Management, Disziplin und Journal-Vorbereitung muessen vollstaendig sein.',
    },
    {
      id: 'decision',
      title: 'Entscheidung lesen',
      view: 'desk',
      done: manualReviewReady,
      action: statusLabel(activeResult.status),
      detail: manualReviewReady ? 'Nur manuelle Pruefung, keine Orderfreigabe.' : firstBlockingReason(activeResult),
    },
    {
      id: 'journal',
      title: 'Trade dokumentieren',
      view: 'journal',
      done: journalScore >= 80,
      action: `${journalScore}% Journal-Fortschritt`,
      detail: 'Vorher-Bild, Ergebnis, Nachher-Bild, Regelcheck und Review erfassen.',
    },
    {
      id: 'review',
      title: 'Muster auswerten',
      view: 'review',
      done: reviewInsights.openReviews === 0,
      action: `${reviewInsights.openReviews} aktive Nacharbeiten`,
      detail: 'Schwache Symbole, haeufige Blocker und Dokumentationsluecken fuer die naechste Woche pruefen.',
    },
  ];
}

function currentWorkflowStep(steps) {
  return steps.find((step) => !step.done) || steps[steps.length - 1];
}

function directionDecisionCards(candidate, guide) {
  const shared = ['Entry nahe Level', 'Stop Loss geplant', 'Take Profit/Exit geplant', 'CRV >= 1:1', '5 Pre-Checks vollstaendig'];
  if (candidate.market === 'us_stock' && candidate.setup_name.includes('News')) {
    return {
      long: ['Positive News', 'Kurs ueber VWAP', 'Momentum nach oben', 'enge Konsolidierung', ...shared],
      short: ['Negative News', 'Kurs unter VWAP', 'Momentum nach unten', 'enge Konsolidierung', ...shared],
      observe: ['Mixed News', 'kein Momentum', 'nur Volatilitaet', 'Entry zu weit weg'],
    };
  }
  if (candidate.market === 'index' || candidate.setup_name.includes('DAX')) {
    return {
      long: ['Starke Unterstuetzung', 'Abprall oder Reclaim', 'kein nahes Risikoevent', ...shared],
      short: ['Starker Widerstand', 'Ablehnung oder Breakdown', 'kein nahes Risikoevent', ...shared],
      observe: ['Zone schwach', 'Eventnaehe', 'kein sauberer Abprall', 'CRV unklar'],
    };
  }
  if (candidate.market === 'forex' || candidate.setup_name.includes('FX')) {
    return {
      long: ['Starke Basiswaehrung', 'schwache Gegenwaehrung', 'Eventreaktion eindeutig', 'Momentum bestaetigt', ...shared],
      short: ['Schwache Basiswaehrung', 'starke Gegenwaehrung', 'Eventreaktion eindeutig', 'Momentum bestaetigt', ...shared],
      observe: ['gemischte Daten', 'Spread hoch', 'Sentiment-Konflikt', 'kein Momentum'],
    };
  }
  return {
    long: [guide.confirmations[0], 'Support/Reversal bestaetigt', 'Momentum oder Ruecklauf sauber', ...shared].filter(Boolean),
    short: [guide.confirmations[0], 'Widerstand/Reversal bestaetigt', 'Momentum oder Ruecklauf sauber', ...shared].filter(Boolean),
    observe: guide.blockers,
  };
}

function viewLabel(view) {
  const labels = {
    guide: 'Heute',
    desk: 'Pruefen',
    updates: 'Live & News',
    journal: 'Journal',
    trades: 'Trades',
    review: 'Review',
    help: 'Hilfe',
  };
  return labels[view] || view;
}

function firstBlockingReason(result) {
  return result.failed[0] || result.warnings[0] || 'Bereit fuer manuelle Pruefung';
}

function shortSetupName(value) {
  return String(value || '')
    .replace('US Newstrade ', 'US News ')
    .replace('Rectangle Scalping', 'Rectangle')
    .replace('Wirtschaftsdaten', 'Daten')
    .replace('Premarket High/Low', 'Premarket H/L');
}

export default function App() {
  const sandboxMode = useMemo(isSandboxModeRequested, []);
  const storageKey = sandboxMode ? SANDBOX_STORAGE_KEY : STORAGE_KEY;
  const initial = useMemo(() => loadInitialState(storageKey, sandboxMode), [sandboxMode, storageKey]);
  const [context, setContext] = useState(initial.context);
  const [candidates, setCandidates] = useState(initial.candidates);
  const [activeId, setActiveId] = useState(initial.activeId);
  const [journal, setJournal] = useState(initial.journal);
  const [journalDrafts, setJournalDrafts] = useState(initial.journalDrafts || []);
  const [activeJournalDraftId, setActiveJournalDraftId] = useState(initial.activeJournalDraftId || '');
  const [importedJournalTrades, setImportedJournalTrades] = useState([]);
  const [chatUpdateFeed, setChatUpdateFeed] = useState({ updates: [], generated_at: '', update_count: 0, chat_count: 0, chat_coverage: [] });
  const [backtestCosts, setBacktestCosts] = useState(initial.backtestCosts || defaultBacktestCosts);
  const [importText, setImportText] = useState(initial.importText || '');
  const [tradeEventText, setTradeEventText] = useState(initial.tradeEventText || makeTradeEventExample());
  const [tradeEventStatus, setTradeEventStatus] = useState('');
  const [journalActionStatus, setJournalActionStatus] = useState('');
  const [activeView, setActiveView] = useState(initial.activeView || 'guide');
  const [candidateAssetDraft, setCandidateAssetDraft] = useState('');
  const [tradeFilters, setTradeFilters] = useState(defaultTradeFilters);
  const [chatUpdateFilters, setChatUpdateFilters] = useState({ session: 'all', asset: 'all', theme: 'all' });
  const [selectedUpdateId, setSelectedUpdateId] = useState('');
  const [updatesDetailsOpen, setUpdatesDetailsOpen] = useState(false);
  const [chatUpdateAutoRefresh, setChatUpdateAutoRefresh] = useState(true);
  const [chatUpdateRefresh, setChatUpdateRefresh] = useState({ status: 'idle', checked_at: '', error: '' });
  const [liveFeedStatus, setLiveFeedStatus] = useState({ live_status: null, generated_at: '', next_step: '' });
  const [liveAdapterConfigStatus, setLiveAdapterConfigStatus] = useState({ adapters: [], configured_count: 0, missing_count: 4, warnings: [] });
  const [liveFeedRefresh, setLiveFeedRefresh] = useState({ status: 'idle', checked_at: '', error: '' });
  const [savedAt, setSavedAt] = useState('');
  const [maintenanceStatus, setMaintenanceStatus] = useState('');
  const [journalStoreStatus, setJournalStoreStatus] = useState({ status: 'unchecked', checked_at: '', draft_count: 0, error: '' });

  const activeCandidate = candidates.find((candidate) => candidate.candidate_id === activeId) || candidates[0];
  const focusedSymbols = useMemo(
    () => new Set(candidates.map((candidate) => String(candidate.symbol || '').trim().toUpperCase()).filter(Boolean)),
    [candidates],
  );
  const assetOptions = useMemo(() => buildAssetOptions(candidates, importText), [candidates, importText]);
  const evaluations = useMemo(
    () => candidates.map((candidate) => ({ candidate, result: evaluateCandidate(candidate, context) })),
    [candidates, context],
  );
  const rankedEvaluations = useMemo(
    () => [...evaluations].sort((a, b) => scoreCandidatePriority(b.candidate) - scoreCandidatePriority(a.candidate)),
    [evaluations],
  );
  const newsDeckColumns = useMemo(() => buildNewsDeckColumns(candidates), [candidates]);
  const activeResult = evaluateCandidate(activeCandidate, context);
  const focusCandidates = useMemo(
    () => [...candidates].sort((a, b) => scoreCandidatePriority(b) - scoreCandidatePriority(a)).slice(0, 5),
    [candidates],
  );
  const visibleJournalEntries = useMemo(
    () => mergeJournalEntries(journalDrafts, importedJournalTrades),
    [journalDrafts, importedJournalTrades],
  );
  const liveJournalEntries = useMemo(
    () => visibleJournalEntries.filter((entry) => tradeAccountMode(entry) === 'live'),
    [visibleJournalEntries],
  );
  const archiveJournalEntries = useMemo(
    () => visibleJournalEntries.filter((entry) => tradeAccountMode(entry) !== 'live'),
    [visibleJournalEntries],
  );
  const reviewQueueEntries = useMemo(
    () => sortReviewQueueEntries(liveJournalEntries.filter(isActionableReviewEntry)),
    [liveJournalEntries],
  );
  const runningJournalDrafts = useMemo(
    () => journalDrafts.filter((draft) => tradeAccountMode(draft) === 'live' && (draft.lifecycle_status === 'open' || draft.status === 'Trade laeuft')),
    [journalDrafts],
  );
  const activeJournalDraft = useMemo(
    () => journalDrafts.find((draft) => draft.draft_id === activeJournalDraftId) || null,
    [journalDrafts, activeJournalDraftId],
  );
  const tradePeriodOptions = useMemo(
    () => tradeFilterOptions(visibleJournalEntries, tradeFilters.periodType),
    [visibleJournalEntries, tradeFilters.periodType],
  );
  const filteredJournalEntries = useMemo(
    () => filterJournalEntries(visibleJournalEntries, tradeFilters),
    [visibleJournalEntries, tradeFilters],
  );
  const activeGuide = useMemo(() => setupGuide(activeCandidate), [activeCandidate]);
  const journalSteps = useMemo(() => buildJournalSteps(journal, activeResult), [journal, activeResult]);
  const reviewInsights = useMemo(() => buildReviewInsights(liveJournalEntries), [liveJournalEntries]);
  const manualCount = evaluations.filter(({ result }) => result.status === 'Manuelle Pruefung').length;
  const watchCount = evaluations.filter(({ result }) => result.status === 'Nur beobachten').length;
  const blockedCount = evaluations.filter(({ result }) => result.status === 'Blockiert').length;
  const slotsRemaining = Math.max(0, toNumber(context.max_trades_per_day) - toNumber(context.trades_taken_today));
  const contextIssues = contextBlockers(context);
  const dayStatus = contextIssues.length ? 'Trading Pause' : manualCount ? 'Manuelle Pruefung' : 'Nur beobachten';
  const journalScore = journalCompletion(journal);
  const journalMetrics = useMemo(() => buildJournalMetrics(liveJournalEntries), [liveJournalEntries]);
  const filteredJournalMetrics = useMemo(() => buildJournalMetrics(filteredJournalEntries), [filteredJournalEntries]);
  const chatUpdates = chatUpdateFeed.updates || [];
  const currentDayChatUpdates = useMemo(() => chatUpdates.filter(isTodayUpdate), [chatUpdates]);
  const filteredChatUpdates = useMemo(
    () => filterChatUpdates(chatUpdates, chatUpdateFilters),
    [chatUpdates, chatUpdateFilters],
  );
  const selectedChatUpdate = useMemo(
    () => chatUpdates.find((update) => update.id === selectedUpdateId) || filteredChatUpdates[0] || chatUpdates[0] || null,
    [chatUpdates, filteredChatUpdates, selectedUpdateId],
  );
  const selectedUpdateIsToday = selectedChatUpdate ? isTodayUpdate(selectedChatUpdate) : false;
  const latestChatUpdates = chatUpdates.slice(0, 5);
  const chatSessions = useMemo(() => uniqueValues(chatUpdates, 'session'), [chatUpdates]);
  const chatAssets = useMemo(() => [...new Set(chatUpdates.flatMap((update) => update.assets || []))].sort(), [chatUpdates]);
  const chatThemes = useMemo(() => [...new Set(chatUpdates.flatMap((update) => update.themes || []))].sort(), [chatUpdates]);
  const chatTradeIdeas = useMemo(() => buildChatTradeIdeas(currentDayChatUpdates), [currentDayChatUpdates]);
  const chatUpdateFreshness = useMemo(() => latestUpdateFreshness(chatUpdates), [chatUpdates]);
  const latestUpdateDateLabel = dateKeyLabel(chatUpdateFreshness.latestKey);
  const chatCoverage = useMemo(() => chatCoverageItems(chatUpdateFeed, chatUpdates), [chatUpdateFeed, chatUpdates]);
  const requiredChatCoverage = useMemo(() => chatCoverage.filter((source) => source.required), [chatCoverage]);
  const optionalChatCoverage = useMemo(() => chatCoverage.filter((source) => !source.required), [chatCoverage]);
  const requiredChatCount = chatUpdateFeed.required_chat_count || requiredChatCoverage.length || 4;
  const coveredRequiredChatCount = chatUpdateFeed.covered_required_chat_count ?? requiredChatCoverage.filter((source) => source.status !== 'missing').length;
  const missingRequiredChats = chatUpdateFeed.missing_required_chats || requiredChatCoverage.filter((source) => source.status === 'missing').map((source) => source.canonical_title);
  const requiredChatLatestKey = latestCoverageKey(requiredChatCoverage);
  const requiredChatTodayKey = berlinDateKey(new Date().toISOString());
  const requiredChatsAreToday = Boolean(requiredChatLatestKey && requiredChatLatestKey === requiredChatTodayKey);
  const requiredChatCoverageText = `${coveredRequiredChatCount}/${requiredChatCount} Update-Chats`;
  const dailyWorkflow = useMemo(
    () => buildDailyWorkflow({ activeCandidate, activeResult, context, contextIssues, journalScore, reviewInsights }),
    [activeCandidate, activeResult, context, contextIssues, journalScore, reviewInsights],
  );
  const activeWorkflowStep = currentWorkflowStep(dailyWorkflow);
  const directionCards = useMemo(() => directionDecisionCards(activeCandidate, activeGuide), [activeCandidate, activeGuide]);
  const journalSaveLabel = activeJournalDraft
    ? activeJournalDraft.lifecycle_status === 'closed'
      ? 'Review speichern'
      : 'Laufenden Trade speichern'
    : 'Trade starten';
  const activeJournalSymbol = activeJournalDraft?.symbol || activeCandidate.symbol || 'UNDEFINED';
  const activeJournalRisk = activeJournalDraft?.risk_amount || display(activeResult.riskAmount);
  const activeJournalPositionSize = activeJournalDraft?.position_size || display(activeResult.positionSize);
  const activeJournalPlannedCrv = activeJournalDraft?.planned_crv || display(activeResult.crv);
  const activeJournalEntry = activeJournalDraft?.entry || activeCandidate.entry || '--';
  const activeJournalStopLoss = activeJournalDraft?.stop_loss || activeCandidate.stop_loss || '--';
  const activeJournalTakeProfit = activeJournalDraft?.take_profit || activeCandidate.take_profit || '--';
  const activeJournalExit = activeJournalDraft?.exit_price || journal.exit_price || '--';
  const chatUpdateRefreshLabel = chatUpdateRefresh.checked_at
    ? new Date(chatUpdateRefresh.checked_at).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
    : '--';
  const chatUpdateRefreshText = missingRequiredChats.length
    ? 'Chats fehlen'
    : !requiredChatsAreToday && requiredChatCoverage.length
      ? 'Chat-Export alt'
      : !chatUpdateFreshness.isToday && chatUpdates.length
        ? 'Nicht tagesaktuell'
    : ({
    idle: 'Noch nicht geladen',
    loading: 'Lade Updates',
    refreshing: 'Auto-Refresh',
    ok: 'Aktuell',
    error: 'Fehler',
  }[chatUpdateRefresh.status] || 'Aktualisierung');
  const chatUpdateRefreshClass = chatUpdateRefresh.status === 'error' || missingRequiredChats.length || (!chatUpdateFreshness.isToday && chatUpdates.length)
    ? 'danger'
    : (!requiredChatsAreToday && requiredChatCoverage.length)
      ? 'watch'
      : chatUpdateRefresh.status === 'ok'
      ? 'ok'
      : 'watch';
  const chatUpdateRefreshBusy = ['loading', 'refreshing'].includes(chatUpdateRefresh.status);
  const liveStatus = liveFeedStatus.live_status || {};
  const liveStatusFileAgeSeconds = secondsSince(liveFeedStatus.generated_at || liveStatus.generated_at);
  const liveStatusFileIsStale = liveStatusFileAgeSeconds !== null && liveStatusFileAgeSeconds > LIVE_STATUS_FILE_STALE_AFTER_SECONDS;
  const liveReadiness = useMemo(
    () => liveReadinessItems(liveStatus.evaluations || [], liveAdapterConfigStatus.adapters || []),
    [liveStatus.evaluations, liveAdapterConfigStatus.adapters],
  );
  const liveReadinessMissing = liveReadiness.filter((item) => !item.ready);
  const liveOverallStatus = liveStatusFileIsStale ? 'status_stale' : liveStatus.overall_status || 'not_configured';
  const liveStatusText = {
    second_fresh: 'Sekundenfrisch',
    partly_live: 'Teilweise live',
    not_live: 'Nicht live',
    not_configured: 'Nicht konfiguriert',
    status_stale: 'Status stale',
  }[liveOverallStatus] || liveOverallStatus;
  const liveStatusClass = liveOverallStatus === 'second_fresh' ? 'ok' : liveOverallStatus === 'partly_live' ? 'watch' : 'danger';
  const liveDraftCount = journalDrafts.filter((draft) => tradeAccountMode(draft) === 'live').length;
  const paperDraftCount = journalDrafts.filter((draft) => tradeAccountMode(draft) === 'paper').length;
  const importedDraftCount = importedJournalTrades.length;
  const goLiveBlockers = [
    liveReadinessMissing.length ? `${liveReadinessMissing.length} Live-Quellen fehlen` : '',
    requiredChatCoverage.length && !requiredChatsAreToday ? 'Pflicht-Updates nicht tagesaktuell' : '',
    reviewInsights.openReviews ? `${reviewInsights.openReviews} aktive Reviews offen` : '',
    liveDraftCount ? `${liveDraftCount} lokale Live-Drafts pruefen` : '',
  ].filter(Boolean);
  const goLiveStatusText = goLiveBlockers.length ? 'Go-Live blockiert' : 'Go-Live technisch bereit';
  const goLiveStatusClass = goLiveBlockers.length ? 'danger' : 'ok';
  const journalStoreStatusText = {
    ok: 'Dateisync aktiv',
    offline: 'Dateisync offline',
    unchecked: 'Dateisync ungeprueft',
  }[journalStoreStatus.status] || 'Dateisync';
  const journalStoreStatusClass = journalStoreStatus.status === 'ok' ? 'ok' : journalStoreStatus.status === 'offline' ? 'watch' : 'watch';
  const liveLastCheckedLabel = liveFeedRefresh.checked_at
    ? new Date(liveFeedRefresh.checked_at).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '--';
  const sourceAgeLabel = (source) => {
    const baseAge = Number(source.age_seconds);
    const fileAge = liveStatusFileAgeSeconds || 0;
    if (!Number.isFinite(baseAge)) return '--';
    return `${Math.round(baseAge + fileAge)}s`;
  };

  const refreshChatUpdateFeed = useCallback(async ({ silent = false } = {}) => {
    setChatUpdateRefresh((current) => ({
      ...current,
      status: silent ? 'refreshing' : 'loading',
      error: '',
    }));
    try {
      const feed = await requestChatUpdateFeed();
      setChatUpdateFeed(feed);
      setChatUpdateRefresh({ status: 'ok', checked_at: new Date().toISOString(), error: '' });
      return feed;
    } catch {
      setChatUpdateRefresh({
        status: 'error',
        checked_at: new Date().toISOString(),
        error: 'Update-Feed konnte nicht geladen werden. Der letzte bekannte Stand bleibt sichtbar.',
      });
      return null;
    }
  }, []);

  const refreshLiveFeedStatus = useCallback(async () => {
    setLiveFeedRefresh((current) => ({ ...current, status: 'loading', error: '' }));
    try {
      const [payload, configPayload] = await Promise.all([
        requestLiveFeedStatus(),
        requestLiveAdapterConfigStatus().catch(() => null),
      ]);
      setLiveFeedStatus(payload);
      if (configPayload) setLiveAdapterConfigStatus(configPayload);
      setLiveFeedRefresh({ status: 'ok', checked_at: new Date().toISOString(), error: '' });
      return payload;
    } catch {
      setLiveFeedRefresh({
        status: 'error',
        checked_at: new Date().toISOString(),
        error: 'Live-Status konnte nicht geladen werden.',
      });
      return null;
    }
  }, []);

  const checkJournalStore = useCallback(async () => {
    try {
      const payload = await requestJournalStore();
      setJournalStoreStatus({
        status: 'ok',
        checked_at: new Date().toISOString(),
        draft_count: payload.draft_count || 0,
        error: '',
      });
      return payload;
    } catch {
      setJournalStoreStatus({
        status: 'offline',
        checked_at: new Date().toISOString(),
        draft_count: 0,
        error: 'Lokale Journal-API ist nicht erreichbar.',
      });
      return null;
    }
  }, []);

  async function saveJournalStoreToBackend() {
    try {
      const payload = await saveJournalStore({
        source: sandboxMode ? 'wertbegleiter_portal_sandbox' : 'wertbegleiter_portal',
        active_journal_draft_id: activeJournalDraftId,
        journal_drafts: journalDrafts,
      });
      setJournalStoreStatus({
        status: 'ok',
        checked_at: new Date().toISOString(),
        draft_count: payload.draft_count || journalDrafts.length,
        error: '',
      });
      setMaintenanceStatus(`${payload.draft_count || journalDrafts.length} Journal-Drafts in lokaler Datei gespeichert.`);
    } catch {
      setJournalStoreStatus({
        status: 'offline',
        checked_at: new Date().toISOString(),
        draft_count: 0,
        error: 'Speichern nicht moeglich: Backend auf Port 8000 ist nicht erreichbar.',
      });
      setMaintenanceStatus('Dateisync offline. Starte bei Bedarf: PYTHONPATH=src python3 -m trading_freaks.api.server');
    }
  }

  async function loadJournalStoreFromBackend() {
    const payload = await checkJournalStore();
    const drafts = payload?.journal_store?.journal_drafts || [];
    if (!drafts.length) {
      setMaintenanceStatus(payload ? 'Lokale Journal-Datei ist leer.' : 'Dateisync offline. Keine Datei geladen.');
      return;
    }
    setJournalDrafts((current) => {
      const byId = new Map(current.map((draft) => [draft.draft_id, draft]));
      drafts.map(normalizeJournalDraft).forEach((draft) => {
        const existing = byId.get(draft.draft_id);
        byId.set(draft.draft_id, existing ? { ...existing, ...draft } : draft);
      });
      return sortJournalEntries([...byId.values()]).slice(0, 160);
    });
    const activeFromStore = payload.journal_store.active_journal_draft_id;
    if (activeFromStore && drafts.some((draft) => draft.draft_id === activeFromStore)) {
      setActiveJournalDraftId(activeFromStore);
      const activeDraft = drafts.find((draft) => draft.draft_id === activeFromStore);
      if (activeDraft) setJournal(journalFromDraft(activeDraft));
    }
    setMaintenanceStatus(`${drafts.length} Drafts aus lokaler Journal-Datei geladen und gemerged.`);
  }

  useEffect(() => {
    try {
      window.localStorage.setItem(
        storageKey,
        JSON.stringify({
          context,
          candidates,
          activeId,
          journal,
          journalDrafts,
          activeJournalDraftId,
          backtestCosts,
          importText,
          tradeEventText,
          activeView,
          sandboxMode,
        }),
      );
      setSavedAt(new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }));
    } catch {
      setSavedAt('Screenshot zu gross');
    }
  }, [context, candidates, activeId, journal, journalDrafts, activeJournalDraftId, backtestCosts, importText, tradeEventText, activeView, storageKey, sandboxMode]);

  useEffect(() => {
    let cancelled = false;
    loadImportedJournalTrades().then((entries) => {
      if (!cancelled) setImportedJournalTrades(entries);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadManualJournalDrafts().then((drafts) => {
      if (cancelled || !drafts.length) return;
      setJournalDrafts((current) => {
        const byId = new Map(current.map((draft) => [draft.draft_id, draft]));
        drafts.forEach((draft) => {
          const existing = byId.get(draft.draft_id);
          byId.set(draft.draft_id, existing ? { ...existing, ...draft } : draft);
        });
        return sortJournalEntries([...byId.values()]).slice(0, 100);
      });
      const openDraft = drafts.find((draft) => draft.lifecycle_status === 'open' || draft.status === 'Trade laeuft');
      if (openDraft) {
        setActiveJournalDraftId((current) => current || openDraft.draft_id);
        setJournal((current) => {
          const hasCurrentScreenshot = Boolean(current.screenshot_before || current.screenshot_after || current.review);
          return hasCurrentScreenshot ? current : journalFromDraft(openDraft);
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    refreshChatUpdateFeed();
  }, [refreshChatUpdateFeed]);

  useEffect(() => {
    refreshLiveFeedStatus();
    const intervalId = window.setInterval(refreshLiveFeedStatus, 1000);
    return () => window.clearInterval(intervalId);
  }, [refreshLiveFeedStatus]);

  useEffect(() => {
    checkJournalStore();
  }, [checkJournalStore]);

  useEffect(() => {
    if (!chatUpdateAutoRefresh) return undefined;
    const intervalId = window.setInterval(() => {
      refreshChatUpdateFeed({ silent: true });
    }, 30000);
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') refreshChatUpdateFeed({ silent: true });
    };
    const refreshOnFocus = () => refreshChatUpdateFeed({ silent: true });
    document.addEventListener('visibilitychange', refreshWhenVisible);
    window.addEventListener('focus', refreshOnFocus);
    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', refreshWhenVisible);
      window.removeEventListener('focus', refreshOnFocus);
    };
  }, [chatUpdateAutoRefresh, refreshChatUpdateFeed]);

  useEffect(() => {
    if (tradeFilters.periodType === 'all' || !tradeFilters.periodValue) return;
    if (!tradePeriodOptions.includes(tradeFilters.periodValue)) {
      setTradeFilters((current) => ({ ...current, periodValue: '' }));
    }
  }, [tradeFilters.periodType, tradeFilters.periodValue, tradePeriodOptions]);

  const updateContext = (key, value) => setContext((current) => ({ ...current, [key]: value }));
  const updateJournal = (key, value) => setJournal((current) => ({ ...current, [key]: value }));
  const updateActive = (key, value) => {
    if (key === 'symbol') {
      const normalizedSymbol = String(value || '').trim().toUpperCase();
      const existing = candidates.find(
        (candidate) =>
          candidate.candidate_id !== activeCandidate.candidate_id &&
          String(candidate.symbol || '').trim().toUpperCase() === normalizedSymbol,
      );
      if (existing) {
        setActiveId(existing.candidate_id);
        return;
      }
      value = normalizedSymbol;
    }
    setCandidates((current) =>
      current.map((candidate) => (candidate.candidate_id === activeCandidate.candidate_id ? { ...candidate, [key]: value } : candidate)),
    );
  };
  const patchActive = (patch) => {
    setCandidates((current) =>
      current.map((candidate) => (candidate.candidate_id === activeCandidate.candidate_id ? { ...candidate, ...patch } : candidate)),
    );
  };
  const updateCondition = (name, passed) => {
    setCandidates((current) =>
      current.map((candidate) =>
        candidate.candidate_id === activeCandidate.candidate_id
          ? {
              ...candidate,
              conditions: candidate.conditions.map((condition) => (condition.name === name ? { ...condition, passed } : condition)),
            }
          : candidate,
      ),
    );
  };

  function openWorkflowStep(step) {
    setActiveView(step.view);
    window.requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  function openUpdateDetails(targetSelector = '.updateDetails') {
    setUpdatesDetailsOpen(true);
    window.requestAnimationFrame(() => {
      document.querySelector(targetSelector)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  function goToUpdateDetails(targetSelector = '.updateDetails') {
    setActiveView('updates');
    setUpdatesDetailsOpen(true);
    window.setTimeout(() => {
      document.querySelector(targetSelector)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  }

  function selectChatUpdate(update) {
    if (!update) return;
    setSelectedUpdateId(update.id);
    openUpdateDetails('.selectedUpdatePanel');
  }

  function applyAssetToActive(symbol) {
    const normalizedSymbol = String(symbol || '').trim().toUpperCase();
    if (!normalizedSymbol) {
      patchActive({ symbol: '' });
      return;
    }
    const existing = candidates.find(
      (candidate) =>
        candidate.candidate_id !== activeCandidate.candidate_id &&
        String(candidate.symbol || '').trim().toUpperCase() === normalizedSymbol,
    );
    if (existing) {
      setActiveId(existing.candidate_id);
      return;
    }
    const option = assetOptions.find((item) => item.symbol === normalizedSymbol) || {
      symbol: normalizedSymbol,
      ...inferImportDefaults('', normalizedSymbol, ''),
    };
    const symbolChanged = Boolean(activeCandidate.symbol && activeCandidate.symbol !== normalizedSymbol);
    patchActive({
      ...assetCandidatePatch(option),
      direction: symbolChanged ? 'conditional' : activeCandidate.direction,
      entry: symbolChanged ? '' : activeCandidate.entry,
      stop_loss: symbolChanged ? '' : activeCandidate.stop_loss,
      take_profit: symbolChanged ? '' : activeCandidate.take_profit,
      conditions: symbolChanged ? makeConditions(false) : activeCandidate.conditions,
      notes: symbolChanged ? option.notes || '' : activeCandidate.notes || option.notes || '',
    });
  }

  function importWatchlist() {
    const imported = dedupeCandidates(parseWatchlistImport(importText));
    if (!imported.length) return;
    setCandidates(imported);
    setActiveId(imported[0].candidate_id);
    setActiveView('desk');
  }

  function importWatchlistFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setImportText(String(reader.result || ''));
    reader.readAsText(file);
    event.target.value = '';
  }

  function addCandidate() {
    const option = candidateAssetDraft
      ? assetOptions.find((item) => item.symbol === candidateAssetDraft)
      : null;
    const existing = option
      ? candidates.find((candidate) => String(candidate.symbol || '').trim().toUpperCase() === option.symbol)
      : candidates.find((candidate) => !String(candidate.symbol || '').trim());
    if (existing) {
      setActiveId(existing.candidate_id);
      setCandidateAssetDraft('');
      setActiveView('desk');
      return;
    }
    const candidate = makeCandidate(option ? assetCandidatePatch(option) : {});
    setCandidates((current) => [...current, candidate]);
    setActiveId(candidate.candidate_id);
    setCandidateAssetDraft('');
    setActiveView('desk');
  }

  function addChatTradeIdea(idea) {
    const candidate = chatIdeaToCandidate(idea);
    const existing = candidates.find((item) => String(item.symbol || '').trim().toUpperCase() === candidate.symbol);
    if (existing) {
      setActiveId(existing.candidate_id);
      setActiveView('desk');
      return;
    }
    setCandidates((current) => dedupeCandidates([candidate, ...current], candidate.candidate_id));
    setActiveId(candidate.candidate_id);
    setActiveView('desk');
  }

  function addSelectedUpdateToDesk(update = selectedChatUpdate) {
    const firstSymbol = update?.assets?.[0];
    if (!update || !firstSymbol || !isTodayUpdate(update)) return;
    addChatTradeIdea(updateAssetToTradeIdea(update, firstSymbol));
  }

  function removeActiveCandidateFromFocus() {
    if (!activeCandidate) return;
    const remaining = candidates.filter((candidate) => candidate.candidate_id !== activeCandidate.candidate_id);
    const nextCandidates = remaining.length ? remaining : [makeCandidate()];
    setCandidates(nextCandidates);
    setActiveId(nextCandidates[0].candidate_id);
    setCandidateAssetDraft(activeCandidate.symbol || '');
    setActiveView('desk');
  }

  function resetDay() {
    setContext(defaultContext);
    setCandidates(defaultCandidates);
    setActiveId(defaultCandidates[0].candidate_id);
    setJournal(defaultJournal);
    setJournalDrafts([]);
    setActiveJournalDraftId('');
    setBacktestCosts(defaultBacktestCosts);
    setImportText('');
    setTradeEventText(makeTradeEventExample());
    setTradeEventStatus('');
    setActiveView('desk');
  }

  function buildJournalDraft({
    status = 'Trade laeuft',
    lifecycleStatus = 'open',
    draftId = `draft-${Date.now()}`,
    exitReason = '',
  } = {}) {
    const now = new Date().toISOString();
    const baseDraft = activeJournalDraft?.draft_id === draftId ? activeJournalDraft : null;
    const riskAmount = baseDraft?.risk_amount || display(activeResult.riskAmount);
    const positionSize = baseDraft?.position_size || display(activeResult.positionSize);
    const plannedCrv = baseDraft?.planned_crv || display(activeResult.crv);
    const direction = baseDraft?.direction || activeCandidate.direction;
    const entry = baseDraft?.entry || activeCandidate.entry || '';
    const stopLoss = baseDraft?.stop_loss || activeCandidate.stop_loss || '';
    const takeProfit = baseDraft?.take_profit || activeCandidate.take_profit || '';
    const exitPrice = journal.exit_price || baseDraft?.exit_price || '';
    const finalExitReason = journal.exit_reason || exitReason || baseDraft?.exit_reason || '';
    const realizedR =
      journal.realized_r ||
      realizedRLabelFromJournalFacts({
        direction,
        entry,
        stop_loss: stopLoss,
        exit_price: exitPrice,
        result_money: journal.result_money || baseDraft?.result_money || '',
        risk_amount: riskAmount,
        exit_reason: finalExitReason,
        planned_crv: plannedCrv,
      });
    return {
      draft_id: draftId,
      external_trade_id: baseDraft?.external_trade_id || '',
      source_import_id: baseDraft?.source_import_id || '',
      date: baseDraft?.date || todayLabel(),
      symbol: baseDraft?.symbol || activeCandidate.symbol || 'UNDEFINED',
      market: baseDraft?.market || activeCandidate.market,
      setup: baseDraft?.setup || activeCandidate.setup_name,
      status,
      lifecycle_status: lifecycleStatus,
      started_at: baseDraft?.started_at || now,
      closed_at: lifecycleStatus === 'closed' ? now : baseDraft?.closed_at || '',
      direction,
      planned_time: baseDraft?.planned_time || activeCandidate.planned_time,
      entry,
      stop_loss: stopLoss,
      take_profit: takeProfit,
      risk_amount: riskAmount,
      position_size: positionSize,
      planned_crv: plannedCrv,
      failed_conditions: baseDraft?.failed_conditions || activeResult.failed,
      emotion_before: journal.emotion_before,
      emotion_during: journal.emotion_during,
      emotion_after: journal.emotion_after,
      confidence_level: journal.confidence_level,
      stress_level: journal.stress_level,
      focus_level: journal.focus_level,
      screenshot_before: journal.screenshot_before || baseDraft?.screenshot_before || '',
      screenshot_after: journal.screenshot_after || baseDraft?.screenshot_after || '',
      exit_price: exitPrice,
      exit_reason: finalExitReason,
      realized_r: realizedR,
      result_money: journal.result_money || baseDraft?.result_money || '',
      fees: journal.fees || baseDraft?.fees || '',
      slippage: journal.slippage || baseDraft?.slippage || '',
      rule_compliant: journal.rule_compliant,
      violated_rule: journal.violated_rule,
      what_went_well: journal.what_went_well,
      improvement: journal.improvement,
      review: journal.review,
      completion: journalScore,
      source: baseDraft?.source || 'Tagesprozess',
      account_mode: baseDraft?.account_mode || 'live',
      sandbox: sandboxMode || baseDraft?.sandbox || false,
      sort_key: now,
      information_only: true,
    };
  }

  function createRunningTradeDraft() {
    const draft = buildJournalDraft();
    setJournalDrafts((current) => [draft, ...current].slice(0, 80));
    setActiveJournalDraftId(draft.draft_id);
    setJournal(journalFromDraft(draft));
    setJournalActionStatus(`${draft.symbol}: laufender Journal-Entwurf gestartet.`);
    setActiveView('journal');
  }

  function updateRunningTradeDraft() {
    if (!activeJournalDraft) {
      createRunningTradeDraft();
      return;
    }
    const staysClosed = activeJournalDraft.lifecycle_status === 'closed' && activeJournalDraft.status !== 'Trade laeuft';
    const updated = buildJournalDraft({
      status: staysClosed ? activeJournalDraft.status || 'Review offen' : 'Trade laeuft',
      lifecycleStatus: staysClosed ? 'closed' : 'open',
      draftId: activeJournalDraft.draft_id,
    });
    setJournalDrafts((current) => current.map((draft) => (draft.draft_id === activeJournalDraft.draft_id ? { ...draft, ...updated } : draft)));
    setJournal(journalFromDraft(updated));
    setJournalActionStatus(`${updated.symbol}: ${staysClosed ? 'Review gespeichert' : 'laufender Trade gespeichert'}. ${updated.realized_r ? `Ergebnis ${updated.realized_r}R.` : 'R noch offen.'}`);
  }

  function closeRunningTradeDraft() {
    if (!activeJournalDraft) {
      setJournalActionStatus('Kein laufender Trade geladen. Bitte zuerst Trade starten oder einen Draft aus der Liste laden.');
      return;
    }
    const closed = buildJournalDraft({
      status: 'Abgeschlossen',
      lifecycleStatus: 'closed',
      draftId: activeJournalDraft.draft_id,
      exitReason: activeJournalDraft.exit_reason || 'Manuell geschlossen',
    });
    setJournalDrafts((current) => current.map((draft) => (draft.draft_id === activeJournalDraft.draft_id ? { ...draft, ...closed } : draft)));
    setJournal(journalFromDraft(closed));
    setJournalActionStatus(`${closed.symbol}: Trade als abgeschlossen gespeichert. ${closed.realized_r ? `Ergebnis ${closed.realized_r}R.` : 'R konnte noch nicht berechnet werden.'}`);
  }

  function closeJournalDraft(draftToClose) {
    const now = new Date().toISOString();
    const exitReason = draftToClose.exit_reason || 'Manuell geschlossen';
    const realizedR =
      draftToClose.realized_r ||
      realizedRLabelFromJournalFacts({
        direction: draftToClose.direction,
        entry: draftToClose.entry,
        stop_loss: draftToClose.stop_loss,
        exit_price: draftToClose.exit_price,
        result_money: draftToClose.result_money,
        risk_amount: draftToClose.risk_amount,
        exit_reason: exitReason,
        planned_crv: draftToClose.planned_crv,
      });
    const closedDraft = {
      ...draftToClose,
      status: 'Abgeschlossen',
      lifecycle_status: 'closed',
      closed_at: now,
      exit_reason: exitReason,
      realized_r: realizedR,
      sort_key: now,
    };
    setJournalDrafts((current) =>
      current.map((draft) =>
        draft.draft_id === draftToClose.draft_id ? closedDraft : draft,
      ),
    );
    setActiveJournalDraftId(draftToClose.draft_id);
    setJournal(journalFromDraft(closedDraft));
    setJournalActionStatus(`${draftToClose.symbol}: laufender Trade abgeschlossen. ${realizedR ? `Ergebnis ${realizedR}R.` : 'R noch offen.'}`);
  }

  function calculateRealizedRForActive() {
    const baseDraft = activeJournalDraft || {};
    const calculated = realizedRLabelFromJournalFacts({
      direction: baseDraft.direction || activeCandidate.direction,
      entry: baseDraft.entry || activeCandidate.entry,
      stop_loss: baseDraft.stop_loss || activeCandidate.stop_loss,
      exit_price: journal.exit_price || baseDraft.exit_price,
      result_money: journal.result_money || baseDraft.result_money,
      risk_amount: baseDraft.risk_amount || display(activeResult.riskAmount),
      exit_reason: journal.exit_reason || baseDraft.exit_reason,
      planned_crv: baseDraft.planned_crv || display(activeResult.crv),
    });
    if (!calculated) {
      setJournalActionStatus('R konnte nicht berechnet werden. Benoetigt wird Ergebnis Geld + Risiko oder Entry + Stop Loss + Exit Preis.');
      return;
    }
    setJournal((current) => ({ ...current, realized_r: calculated }));
    setJournalActionStatus(`Ergebnis in R berechnet: ${calculated}R.`);
  }

  function clearJournalSelection() {
    setActiveJournalDraftId('');
    setJournal(defaultJournal);
    setJournalActionStatus('Neuer Journalfall bereit.');
  }

  function loadJournalDraft(draft) {
    const editableDraft = draft.imported
      ? journalDrafts.find((item) => item.source_import_id === draft.draft_id || item.draft_id === `review-${draft.draft_id}`) ||
        editableReviewDraftFromImported(draft)
      : draft;
    if (draft.imported && editableDraft.source_import_id === draft.draft_id) {
      setJournalDrafts((current) => {
        const exists = current.some((item) => item.draft_id === editableDraft.draft_id);
        return exists ? current : [editableDraft, ...current].slice(0, 100);
      });
    }
    setActiveJournalDraftId(editableDraft.draft_id);
    setJournal(journalFromDraft(editableDraft));
    setActiveView('journal');
    setJournalActionStatus(
      draft.imported
        ? `${draft.symbol}: Import in bearbeitbaren Review uebernommen. Bearbeitung unten im Journalformular moeglich.`
        : `${draft.symbol} geladen. Bearbeitung unten im Journalformular moeglich.`,
    );
    window.requestAnimationFrame(() => {
      document.querySelector('.journalForm')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  function applyTradeEventPayload() {
    let event;
    try {
      event = normalizeExternalTradeEvent(JSON.parse(tradeEventText));
    } catch (error) {
      setTradeEventStatus(`Event nicht lesbar: ${error.message}`);
      return;
    }

    if (!event.event_type) {
      setTradeEventStatus('Event blockiert: event_type fehlt.');
      return;
    }
    if (!event.trade_id) {
      setTradeEventStatus('Event blockiert: trade_id fehlt. Ohne eindeutige ID koennen parallele Trades nicht sauber zugeordnet werden.');
      return;
    }
    if (!event.symbol) {
      setTradeEventStatus('Event blockiert: symbol fehlt.');
      return;
    }

    const eventTime = eventDateParts(event.timestamp);
    const draftId = `event-${event.trade_id}`;

    if (event.event_type === 'opened') {
      const existing = findDraftByExternalTradeId(journalDrafts, event.trade_id);
      const draft = {
        ...(existing || {}),
        draft_id: existing?.draft_id || draftId,
        external_trade_id: event.trade_id,
        date: existing?.date || eventTime.date,
        symbol: event.symbol,
        market: event.market,
        setup: existing?.setup || setupFromImportedSymbol(event.symbol),
        status: 'Trade laeuft',
        lifecycle_status: 'open',
        started_at: eventTime.iso,
        closed_at: '',
        direction: event.direction,
        planned_time: eventTime.time,
        entry: String(event.entry || ''),
        stop_loss: String(event.stop_loss || ''),
        take_profit: String(event.take_profit || ''),
        position_size: String(event.size || event.position_size || ''),
        risk_amount: existing?.risk_amount || '',
        planned_crv: plannedCrvFromEvent(event),
        failed_conditions: [
          'Automatisch importiert: 5 Pre-Checks manuell bestaetigen',
          !event.stop_loss ? 'Stop Loss fehlt im Event' : '',
          !event.take_profit ? 'Take Profit/Exit fehlt im Event' : '',
        ].filter(Boolean),
        emotion_before: existing?.emotion_before || defaultJournal.emotion_before,
        emotion_during: existing?.emotion_during || '',
        emotion_after: existing?.emotion_after || '',
        confidence_level: existing?.confidence_level || defaultJournal.confidence_level,
        stress_level: existing?.stress_level || defaultJournal.stress_level,
        focus_level: existing?.focus_level || defaultJournal.focus_level,
        screenshot_before: event.screenshot_path || existing?.screenshot_before || '',
        screenshot_after: existing?.screenshot_after || '',
        realized_r: existing?.realized_r || '',
        result_money: existing?.result_money || '',
        fees: existing?.fees || '',
        slippage: existing?.slippage || '',
        rule_compliant: false,
        violated_rule: existing?.violated_rule || 'Automatischer Event-Import ohne vollstaendige manuelle Setup-Bestaetigung',
        what_went_well: existing?.what_went_well || '',
        improvement: existing?.improvement || 'Screenshot, 5 Pre-Checks, Setup-These und Risikoannahmen pruefen.',
        review: [existing?.review, event.note || `Importiert aus ${event.source || 'externem Event'}.`].filter(Boolean).join('\n'),
        completion: existing?.completion || 25,
        source: event.source || 'TradingView/Broker Event',
        sort_key: eventTime.iso,
        information_only: true,
      };
      setJournalDrafts((current) => {
        const duplicate = findDraftByExternalTradeId(current, event.trade_id);
        if (duplicate) return current.map((item) => (item.draft_id === duplicate.draft_id ? { ...item, ...draft } : item));
        return [draft, ...current].slice(0, 80);
      });
      setActiveJournalDraftId(draft.draft_id);
      setJournal(journalFromDraft(draft));
      setActiveView('journal');
      setTradeEventStatus(`${event.symbol}: laufender Journal-Entwurf aus Event ${event.trade_id} erstellt/aktualisiert.`);
      return;
    }

    if (String(event.event_type).startsWith('closed')) {
      const existing = findDraftByExternalTradeId(journalDrafts, event.trade_id);
      if (!existing) {
        setTradeEventStatus(`Close-Event blockiert: kein offener Journal-Entwurf fuer Trade-ID ${event.trade_id} gefunden.`);
        return;
      }
      const updated = {
        ...existing,
        status: 'Abgeschlossen',
        lifecycle_status: 'closed',
        closed_at: eventTime.iso,
        exit_price: String(event.exit_price || event.price || ''),
        exit_reason: exitReasonFromEventType(event.event_type),
        realized_r: event.realized_r ? String(event.realized_r) : realizedRFromEventDraft(event, existing),
        result_money: event.result_money ? String(event.result_money) : existing.result_money || '',
        fees: event.fees ? String(event.fees) : existing.fees || '',
        slippage: event.slippage ? String(event.slippage) : existing.slippage || '',
        screenshot_after: event.screenshot_path || existing.screenshot_after || '',
        review: [
          existing.review,
          `${exitReasonFromEventType(event.event_type)} via ${event.source || 'externem Event'} verarbeitet. ${event.note || ''}`.trim(),
        ]
          .filter(Boolean)
          .join('\n'),
        completion: Math.max(existing.completion || 0, 55),
        sort_key: eventTime.iso,
      };
      setJournalDrafts((current) => current.map((draft) => (draft.draft_id === existing.draft_id ? updated : draft)));
      setActiveJournalDraftId(updated.draft_id);
      setJournal(journalFromDraft(updated));
      setActiveView('journal');
      setTradeEventStatus(`${event.symbol}: Trade ${event.trade_id} geschlossen und in aktive Nacharbeit verschoben.`);
      return;
    }

    setTradeEventStatus(`Event-Typ ${event.event_type} wird noch nicht verarbeitet.`);
  }

  function downloadJsonFile(filename, payload) {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function exportJournalBackup() {
    downloadJsonFile(`wertbegleiter-journal-backup-${new Date().toISOString().slice(0, 10)}.json`, {
      exported_at: new Date().toISOString(),
      disclaimer: 'Lokales Journal-Backup. Information und Dokumentation, keine Anlageberatung und keine Orderfreigabe.',
      sandbox_mode: sandboxMode,
      live_journal_entries: liveJournalEntries,
      archive_journal_entries: archiveJournalEntries,
      imported_journal_entries: importedJournalTrades,
      journal_drafts: journalDrafts,
      active_journal_draft_id: activeJournalDraftId,
      current_journal_form: journal,
    });
    setMaintenanceStatus('Journal-Backup wurde als JSON exportiert.');
  }

  function archiveLiveDraftsAsPaper() {
    const liveDraftIds = new Set(journalDrafts.filter((draft) => tradeAccountMode(draft) === 'live').map((draft) => draft.draft_id));
    if (!liveDraftIds.size) {
      setMaintenanceStatus('Keine aktiven Live-Drafts zum Archivieren gefunden.');
      return;
    }
    const ok = window.confirm(
      `${liveDraftIds.size} lokale Live-Journal-Entwuerfe als Paper/Test archivieren? Es wird nichts geloescht; die Eintraege verschwinden nur aus dem Echt/Live-Filter.`,
    );
    if (!ok) return;
    setJournalDrafts((current) =>
      current.map((draft) =>
        liveDraftIds.has(draft.draft_id)
          ? {
              ...draft,
              account_mode: 'paper',
              source: `${draft.source || 'Tagesprozess'} | als Paper/Test archiviert`,
              sort_key: new Date().toISOString(),
            }
          : draft,
      ),
    );
    if (liveDraftIds.has(activeJournalDraftId)) {
      setActiveJournalDraftId('');
      setJournal(defaultJournal);
    }
    setTradeFilters(defaultTradeFilters);
    setMaintenanceStatus(`${liveDraftIds.size} Live-Entwurf${liveDraftIds.size === 1 ? '' : 'e'} verlustfrei als Paper/Test archiviert.`);
  }

  function startCleanLiveJournal() {
    const liveDraftIds = new Set(journalDrafts.filter((draft) => tradeAccountMode(draft) === 'live').map((draft) => draft.draft_id));
    if (!liveDraftIds.size) {
      setMaintenanceStatus('Echtjournal ist bereits leer. Backup kann separat exportiert werden.');
      return;
    }
    const ok = window.confirm(
      `${liveDraftIds.size} lokale Live-Journal-Entwuerfe sichern und danach als Paper/Test archivieren? Es wird nichts geloescht.`,
    );
    if (!ok) return;
    downloadJsonFile(`wertbegleiter-journal-backup-${new Date().toISOString().slice(0, 10)}.json`, {
      exported_at: new Date().toISOString(),
      disclaimer: 'Backup vor Echtjournal-Bereinigung. Information und Dokumentation, keine Anlageberatung und keine Orderfreigabe.',
      sandbox_mode: sandboxMode,
      journal_drafts: journalDrafts,
      imported_journal_entries: importedJournalTrades,
      active_journal_draft_id: activeJournalDraftId,
      current_journal_form: journal,
    });
    setJournalDrafts((current) =>
      current.map((draft) =>
        liveDraftIds.has(draft.draft_id)
          ? {
              ...draft,
              account_mode: 'paper',
              source: `${draft.source || 'Tagesprozess'} | als Paper/Test archiviert`,
              sort_key: new Date().toISOString(),
            }
          : draft,
      ),
    );
    if (liveDraftIds.has(activeJournalDraftId)) {
      setActiveJournalDraftId('');
      setJournal(defaultJournal);
    }
    setTradeFilters(defaultTradeFilters);
    setMaintenanceStatus(`${liveDraftIds.size} Live-Entwurf${liveDraftIds.size === 1 ? '' : 'e'} gesichert und als Paper/Test archiviert. Echtjournal ist bereit.`);
  }

  function enableSandboxMode() {
    window.localStorage.setItem(SANDBOX_FLAG_KEY, '1');
    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.set('sandbox', '1');
    window.location.href = nextUrl.toString();
  }

  function disableSandboxMode() {
    window.localStorage.removeItem(SANDBOX_FLAG_KEY);
    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.delete('sandbox');
    window.location.href = nextUrl.toString();
  }

  function resetSandboxMode() {
    if (!sandboxMode) {
      setMaintenanceStatus('Sandbox ist nicht aktiv.');
      return;
    }
    const ok = window.confirm('Sandbox-Daten zuruecksetzen? Das echte Journal bleibt unveraendert.');
    if (!ok) return;
    window.localStorage.removeItem(SANDBOX_STORAGE_KEY);
    window.location.reload();
  }

  function exportDailyPlan() {
    const payload = {
      exported_at: new Date().toISOString(),
      disclaimer: 'Information und Checklistenunterstuetzung, keine Anlageberatung oder Orderfreigabe.',
      context,
      morning_timeline: morningTimeline,
      focus_candidates: focusCandidates,
      candidates: evaluations,
      news_deck_columns: newsDeckColumns,
      chatgpt_trading_updates: chatUpdateFeed,
      current_day_chat_updates: currentDayChatUpdates,
      chatgpt_trade_ideas: chatTradeIdeas,
      backtest_costs: backtestCosts,
      journal_drafts: journalDrafts,
      imported_journal_entries: importedJournalTrades,
      visible_journal_entries: visibleJournalEntries,
    };
    downloadJsonFile(`tradingfreaks-focus-desk-${new Date().toISOString().slice(0, 10)}.json`, payload);
  }

  const renderCommandRail = () => (
    <section className="simpleFocusBar" aria-label="Tagessteuerung">
      <div className="focusNow">
        <small>Jetzt</small>
        <strong>{activeWorkflowStep.title}</strong>
        <span>{activeWorkflowStep.action}</span>
      </div>
      <div className="focusBadges" aria-label="Kurzstatus">
        <mark className={`statusMark ${liveStatusClass}`}>{liveStatusText}</mark>
        <mark className={`statusMark ${runningJournalDrafts.length ? 'watch' : 'ok'}`}>
          {runningJournalDrafts.length} laufend
        </mark>
        <mark className={`statusMark ${reviewInsights.openReviews ? 'danger' : 'ok'}`}>
          {reviewInsights.openReviews} Reviews
        </mark>
        {sandboxMode && <mark className="statusMark watch">Sandbox</mark>}
      </div>
      <button type="button" className="secondaryButton" onClick={() => openWorkflowStep(activeWorkflowStep)}>
        Oeffnen
      </button>
    </section>
  );

  const renderDecisionCockpit = (variant = 'day') => {
    const totalCandidates = Math.max(candidates.length, 1);
    const resolvedReviews = Math.max(0, reviewInsights.completedReviews);
    const reviewTotal = Math.max(1, reviewInsights.completedReviews + reviewInsights.openReviews);
    const documentationScore = journalMetrics.count
      ? Math.max(0, Math.round(((journalMetrics.count - reviewInsights.openReviews) / journalMetrics.count) * 100))
      : 0;
    const decisionText = contextIssues[0] || (manualCount
      ? `${manualCount} Kandidat${manualCount === 1 ? '' : 'en'} zur manuellen Pruefung`
      : 'Kein vollstaendiges Setup. Nur beobachten.');
    const primaryActionView = manualCount ? 'desk' : runningJournalDrafts.length ? 'journal' : 'updates';

    return (
      <section className={`proCockpit ${variant}`}>
        <article className={`proDecisionHero ${statusClass(dayStatus)}`}>
          <small>Tagesentscheidung</small>
          <strong>{statusLabel(dayStatus)}</strong>
          <p>{decisionText}</p>
          <div className="decisionActionRow">
            <button type="button" className="secondaryButton" onClick={() => setActiveView(primaryActionView)}>
              Naechste Entscheidung
            </button>
            <button type="button" className="ghostButton" onClick={() => setActiveView('review')}>
              Review
            </button>
          </div>
        </article>

        <article className="proMetricCard">
          <small>Setup-Pipeline</small>
          <strong>{manualCount}/{candidates.length}</strong>
          <span>pruefbar</span>
          <div className="stackedBar" aria-label="Setup Pipeline">
            <i className="ok" style={{ width: percentWidth(manualCount, totalCandidates) }} />
            <i className="watch" style={{ width: percentWidth(watchCount, totalCandidates) }} />
            <i className="danger" style={{ width: percentWidth(blockedCount, totalCandidates) }} />
          </div>
          <div className="miniLegend">
            <span>Pruefen {manualCount}</span>
            <span>Beobachten {watchCount}</span>
            <span>Blockiert {blockedCount}</span>
          </div>
        </article>

        <article className="proMetricCard">
          <small>Prozessqualitaet</small>
          <strong>{documentationScore}%</strong>
          <span>Review-Fortschritt</span>
          <div className="singleBar">
            <i style={{ width: percentWidth(resolvedReviews, reviewTotal) }} />
          </div>
          <div className="miniLegend">
            <span>{reviewInsights.completedReviews} fertig</span>
            <span>{reviewInsights.openReviews} aktiv offen</span>
          </div>
        </article>

        <article className="proMetricCard">
          <small>Journal</small>
          <strong>{display(journalMetrics.avgR)}</strong>
          <span>Ø R | {display(journalMetrics.winRate, 0)}% Trefferquote</span>
          <div className="singleBar">
            <i style={{ width: `${Math.max(0, Math.min(100, journalMetrics.winRate))}%` }} />
          </div>
          <div className="miniLegend">
            <span>{journalMetrics.count} Trades</span>
            <span>{runningJournalDrafts.length} laufend</span>
          </div>
        </article>
      </section>
    );
  };

  const renderGoLivePanel = () => (
    <section className="panel goLivePanel">
      <div className="panelHeader tight">
        <div>
          <h2>Go-Live Status</h2>
          <p>Nur harte Blocker. Details oeffnen, wenn etwas rot ist.</p>
        </div>
        <span className={`statusMark ${goLiveStatusClass}`}>{goLiveStatusText}</span>
      </div>
      <div className="goLiveGrid">
        <article>
          <small>Live-Quellen</small>
          <strong>{liveReadinessMissing.length ? `${liveReadinessMissing.length} offen` : 'bereit'}</strong>
          <span>{liveStatusText}</span>
          <button type="button" className="ghostButton" onClick={() => goToUpdateDetails('.liveReadinessPanel')}>
            Anschlussplan
          </button>
        </article>
        <article>
          <small>Updates</small>
          <strong>{requiredChatsAreToday ? 'heute' : 'alt'}</strong>
          <span>{requiredChatLatestKey || latestUpdateDateLabel}</span>
          <button type="button" className="ghostButton" onClick={() => goToUpdateDetails('.updatesHero')}>
            Feed pruefen
          </button>
        </article>
        <article>
          <small>Echtjournal</small>
          <strong>{liveDraftCount}</strong>
          <span>{reviewInsights.openReviews} Reviews offen</span>
          <button type="button" className="ghostButton" onClick={() => setActiveView('trades')}>
            Bereinigen
          </button>
        </article>
        <article>
          <small>Testmodus</small>
          <strong>{sandboxMode ? 'aktiv' : 'aus'}</strong>
          <span>{sandboxMode ? 'Isolierter Speicher' : 'Echtdaten geschuetzt testen'}</span>
          <button type="button" className="ghostButton" onClick={sandboxMode ? disableSandboxMode : enableSandboxMode}>
            {sandboxMode ? 'Beenden' : 'Starten'}
          </button>
        </article>
      </div>
      <div className="goLiveBlockers">
        {goLiveBlockers.length
          ? goLiveBlockers.map((blocker) => <span key={blocker}>{blocker}</span>)
          : <span>Keine technischen Go-Live-Blocker im lokalen Check. Manuelle Setup-Pruefung bleibt Pflicht.</span>}
      </div>
      {maintenanceStatus && <p className="journalActionStatus">{maintenanceStatus}</p>}
    </section>
  );

  const renderJournalMaintenancePanel = () => (
    <section className="panel journalMaintenancePanel">
      <div className="panelHeader tight">
        <div>
          <h2>Echtjournal vorbereiten</h2>
          <p>Backup, Datei-Sync, Paper/Test-Trennung und sicherer UI-Testmodus.</p>
        </div>
        <span className={`statusMark ${sandboxMode ? 'watch' : liveDraftCount ? 'danger' : 'ok'}`}>
          {sandboxMode ? 'Sandbox' : liveDraftCount ? 'Pruefen' : 'sauber'}
        </span>
      </div>
      <div className="maintenanceGrid">
        <article>
          <small>Echt/Live</small>
          <strong>{liveDraftCount}</strong>
          <span>lokale Journal-Drafts</span>
        </article>
        <article>
          <small>Paper/Test</small>
          <strong>{paperDraftCount}</strong>
          <span>archivierte lokale Tests</span>
        </article>
        <article>
          <small>Import/Archiv</small>
          <strong>{importedDraftCount}</strong>
          <span>Broker-/Reportdaten</span>
        </article>
        <article>
          <small>Datei-Sync</small>
          <strong>{journalStoreStatus.status === 'ok' ? journalStoreStatus.draft_count : '--'}</strong>
          <span>{journalStoreStatusText}</span>
        </article>
      </div>
      <div className="actionRow">
        <button type="button" className="ghostButton" onClick={exportJournalBackup}>Backup exportieren</button>
        <button type="button" className="ghostButton" onClick={loadJournalStoreFromBackend}>Datei laden</button>
        <button type="button" className="ghostButton" onClick={saveJournalStoreToBackend}>Datei speichern</button>
        <button type="button" className="secondaryButton" onClick={startCleanLiveJournal}>
          Echtjournal leer starten
        </button>
        <button type="button" className="ghostButton" onClick={sandboxMode ? resetSandboxMode : enableSandboxMode}>
          {sandboxMode ? 'Sandbox resetten' : 'Sandbox testen'}
        </button>
      </div>
      <p className="ruleLine">
        Bereinigung archiviert Live-Drafts als Paper/Test und loescht nichts. Dateisync nutzt die lokale API auf Port 8000.
      </p>
      <div className="goLiveBlockers">
        <span className={`statusMark ${journalStoreStatusClass}`}>{journalStoreStatusText}</span>
        {journalStoreStatus.error && <span>{journalStoreStatus.error}</span>}
      </div>
      {maintenanceStatus && <p className="journalActionStatus">{maintenanceStatus}</p>}
    </section>
  );

  const renderTopDecisionList = () => (
    <div className="proDecisionList">
      {rankedEvaluations.slice(0, 3).map(({ candidate, result }) => (
        <button
          type="button"
          className={`proDecisionItem ${candidate.candidate_id === activeCandidate.candidate_id ? 'active' : ''}`}
          key={candidate.candidate_id}
          onClick={() => {
            setActiveId(candidate.candidate_id);
            setActiveView('desk');
          }}
        >
          <span>
            <strong>{candidate.symbol || 'Symbol fehlt'}</strong>
            <small>{shortSetupName(candidate.setup_name)} | {directionLabel(candidate.direction)}</small>
          </span>
          <mark className={`statusMark ${statusClass(result.status)}`}>{statusLabel(result.status)}</mark>
          <i>{firstBlockingReason(result)}</i>
        </button>
      ))}
    </div>
  );

  const renderGuide = () => (
    <section className="managementWorkspace">
      {renderDecisionCockpit('home')}
      {renderGoLivePanel()}

      <section className="proBoardGrid">
        <section className="panel proBoardPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Entscheidungsboard</h2>
              <p>Nur Kandidaten, Status und naechste Aktion. Details erst nach Klick.</p>
            </div>
            <span className={`statusMark ${statusClass(dayStatus)}`}>{statusLabel(dayStatus)}</span>
          </div>
          {renderTopDecisionList()}
        </section>

        <section className="panel proBoardPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Management Snapshot</h2>
              <p>Was blockiert die Umsetzung?</p>
            </div>
          </div>
          <div className="snapshotGrid">
            <article>
              <small>Live-Daten</small>
              <strong>{liveStatusText}</strong>
              <span>{liveLastCheckedLabel}</span>
            </article>
            <article>
              <small>Nacharbeit</small>
              <strong>{reviewInsights.openReviews}</strong>
              <span>aktiv offen</span>
            </article>
            <article>
              <small>Slots</small>
              <strong>{slotsRemaining}/{context.max_trades_per_day}</strong>
              <span>frei</span>
            </article>
            <article>
              <small>Updates</small>
              <strong>{chatUpdateFeed.update_count || chatUpdates.length}</strong>
              <span>Stand {latestUpdateDateLabel} | {chatUpdateRefreshText}</span>
            </article>
          </div>
        </section>
      </section>

      <details className="proDetails">
        <summary>
          <strong>Prozessdetails anzeigen</strong>
          <span>Tagesablauf, Bedienlogik und Chat-Kontext</span>
        </summary>
        <section className="guideGrid detailsGrid">
          <section className="panel workflowPanel">
            <div className="panelHeader tight">
              <div>
                <h2>Tagesablauf</h2>
                <p>Der erste offene Punkt ist Deine naechste Aktion.</p>
              </div>
            </div>
            <div className="workflowList">
              {dailyWorkflow.map((step, index) => (
                <article className={`${step.done ? 'done' : ''} ${step.id === activeWorkflowStep.id ? 'active' : ''}`} key={step.id}>
                  <mark>{index + 1}</mark>
                  <div>
                    <strong>{step.title}</strong>
                    <span>{step.action}</span>
                    <small>{step.detail}</small>
                  </div>
                  <button type="button" className="ghostButton" onClick={() => openWorkflowStep(step)}>
                    Oeffnen
                  </button>
                </article>
              ))}
            </div>
          </section>

          <aside className="panel wherePanel">
            <div className="panelHeader tight">
              <div>
                <h2>Arbeitsbereiche</h2>
                <p>Direkt in den passenden Bereich springen.</p>
              </div>
            </div>
            <div className="whereGrid">
              <button type="button" onClick={() => setActiveView('desk')}>
                <strong>Vor Trade</strong>
                <span>Setup, Richtung, Entry, SL, TP, Risiko.</span>
              </button>
              <button type="button" onClick={() => setActiveView('updates')}>
                <strong>News & Sessions</strong>
                <span>Updates, Assets, Pflichtchecks, Blocker.</span>
              </button>
              <button type="button" onClick={() => setActiveView('journal')}>
                <strong>Journal</strong>
                <span>Screenshots, Ergebnis, Review.</span>
              </button>
              <button type="button" onClick={() => setActiveView('trades')}>
                <strong>Auswertung</strong>
                <span>Liste, Filter, Bewertung.</span>
              </button>
            </div>
          </aside>
        </section>
      </details>

      <section className="panel updatePreviewPanel">
        <div className="panelHeader tight">
          <div>
            <h2>Importierte ChatGPT-Updates</h2>
            <p>{requiredChatCoverageText} eingebunden, {chatUpdateFeed.update_count || chatUpdates.length} Updates gesamt. Zeitstempel bleiben Informationskontext, keine Signale.</p>
          </div>
          <button type="button" className="ghostButton" onClick={() => setActiveView('updates')}>Alle Updates</button>
        </div>
        <div className="chatCoverageStrip">
          {requiredChatCoverage.map((source) => (
            <article className={`chatSourceMini ${chatCoverageClass(source)}`} key={source.canonical_title}>
              <small>{coverageStatusText(source)}</small>
              <strong>{source.canonical_title}</strong>
              <span>{source.update_count || 0} Updates | letzter Stand {source.latest_timestamp || '--'}</span>
            </article>
          ))}
        </div>
        <div className="updatePreviewGrid">
          {latestChatUpdates.slice(0, 4).map((update) => (
            <article className="updateMiniCard" key={update.id}>
              <small>{update.timestamp} | {update.session}</small>
              <strong>{update.chat_title}</strong>
              <span>{(update.assets || []).slice(0, 6).join(' | ') || 'Assetkontext aus Text pruefen'}</span>
            </article>
          ))}
          {latestChatUpdates.length === 0 && <span className="emptyState">Noch kein ChatGPT-Update-Feed geladen</span>}
        </div>
      </section>

      <section className="panel directionGuidePanel">
        <div className="panelHeader tight">
          <div>
            <h2>Wann Long oder Short pruefen?</h2>
            <p>Keine Empfehlung. Nur die Kriterien, ab wann eine Richtung ueberhaupt zur manuellen Pruefung taugt.</p>
          </div>
          <span className={`statusMark ${statusClass(activeResult.status)}`}>{statusLabel(activeResult.status)}</span>
        </div>
        <div className="directionCards">
          <article className="longCard">
            <h3>Long pruefbar, wenn</h3>
            <div className="focusRules compactRules">
              {directionCards.long.map((item) => <span key={item}>{item}</span>)}
            </div>
          </article>
          <article className="shortCard">
            <h3>Short pruefbar, wenn</h3>
            <div className="focusRules compactRules">
              {directionCards.short.map((item) => <span key={item}>{item}</span>)}
            </div>
          </article>
          <article className="observeCard">
            <h3>Nur beobachten, wenn</h3>
            <div className="failList compactRules">
              {directionCards.observe.map((item) => <span key={item}>{item}</span>)}
            </div>
          </article>
        </div>
      </section>
    </section>
  );

  const renderCandidateCard = ({ candidate, result }) => (
    <button
      type="button"
      className={`candidateCard ${candidate.candidate_id === activeCandidate.candidate_id ? 'active' : ''}`}
      key={candidate.candidate_id}
      onClick={() => setActiveId(candidate.candidate_id)}
    >
      <div className="candidateTop">
        <strong>{candidate.symbol || 'Symbol fehlt'}</strong>
        <span className={`badge ${statusClass(result.status)}`}>{statusLabel(result.status)}</span>
      </div>
      <span>{candidate.setup_name}</span>
      <small>{marketLabel(candidate.market)} | {directionLabel(candidate.direction)} | {candidate.planned_time}</small>
      <small>{timeWindow(candidate)}</small>
      <div className="progressBar" aria-label={`${result.completionScore} Prozent Pre-Checks`}>
        <span style={{ width: `${result.completionScore}%` }} />
      </div>
      <div className="miniMetrics">
        <span>CRV {display(result.crv)}</span>
        <span>{result.completionScore}% Pre-Checks</span>
      </div>
    </button>
  );

  const renderDesk = () => {
    const riskPerTrade = (toNumber(context.account_equity) * toNumber(context.default_risk_percent)) / 100;
    const nextAction = contextIssues.length
      ? contextIssues[0]
      : activeResult.status === 'Manuelle Pruefung'
        ? 'Ticket manuell pruefen'
        : firstBlockingReason(activeResult);

    return (
      <>
        {renderDecisionCockpit('desk')}

        <section className="proBoardGrid">
          <section className="panel proBoardPanel">
            <div className="panelHeader tight">
              <div>
                <h2>Naechste Pruefung</h2>
                <p>Top-Kandidaten aus Watchlist und Update-Kontext.</p>
              </div>
              <button type="button" className="ghostButton" onClick={() => setActiveView('updates')}>Updates</button>
            </div>
            {renderTopDecisionList()}
          </section>

          <section className="panel proBoardPanel">
            <div className="panelHeader tight">
              <div>
                <h2>Aktiver Fall</h2>
                <p>{activeCandidate.symbol || 'Kein Asset'} | {shortSetupName(activeCandidate.setup_name)}</p>
              </div>
              <span className={`statusMark ${statusClass(activeResult.status)}`}>{statusLabel(activeResult.status)}</span>
            </div>
            <div className="decisionFactGrid">
              <span><small>CRV</small>{display(activeResult.crv)}</span>
              <span><small>Risiko</small>{display(activeResult.riskAmount)}</span>
              <span><small>Checks</small>{activeResult.completionScore}%</span>
              <span><small>Richtung</small>{directionLabel(activeCandidate.direction)}</span>
            </div>
            <p className="focusSentence">{firstBlockingReason(activeResult)}</p>
            <div className="actionRow">
              <button type="button" className="ghostButton" onClick={removeActiveCandidateFromFocus}>
                Aus Fokus entfernen
              </button>
            </div>
          </section>
        </section>

        <section className="dashboardHero">
          <article className={`statCard ${statusClass(dayStatus)}`}>
            <small>Status</small>
            <strong>{statusLabel(dayStatus)}</strong>
            <span>Nicht handeln ohne volle 5 Pre-Checks</span>
          </article>
          <article className="statCard">
            <small>Kandidaten</small>
            <strong>{manualCount}/{candidates.length}</strong>
            <span>{watchCount} beobachten, {blockedCount} blockiert</span>
          </article>
          <article className="statCard">
            <small>Risiko/Trade</small>
            <strong>{display(riskPerTrade, 0)}</strong>
            <span>{context.default_risk_percent}% Default</span>
          </article>
          <article className="statCard">
            <small>Freie Slots</small>
            <strong>{slotsRemaining}/{context.max_trades_per_day}</strong>
            <span>Qualitaetskorridor 2-5</span>
          </article>
          <article className="statCard actionStat">
            <small>Naechste Aktion</small>
            <strong>{nextAction}</strong>
            <span>{savedAt ? `Gespeichert ${savedAt}` : 'Noch nicht gespeichert'}</span>
          </article>
        </section>

        <details className="proDetails workbenchDetails">
          <summary>
            <strong>Setup-Details bearbeiten</strong>
            <span>Watchlist, Entry, Stop Loss, Take Profit, Risiko und 5 Pre-Checks</span>
          </summary>
        <section className="dashboardShell">
          <section className="dashboardMain">
            <section className="panel sessionPanel">
              <div className="panelHeader tight">
                <div>
                  <h2>Session-Fahrplan</h2>
                  <p>Nur die naechsten Prozessfenster</p>
                </div>
              </div>
              <div className="sessionRail">
                {morningTimeline.map((item) => (
                  <article className={item.title === 'No Trade' ? 'sessionPill danger' : 'sessionPill'} key={item.time}>
                    <strong>{item.time}</strong>
                    <span>{item.title}</span>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel setupMapPanel">
              <div className="panelHeader tight">
                <div>
                  <h2>Setup-Karte</h2>
                  <p>{activeCandidate.symbol || 'Symbol fehlt'} | {activeCandidate.setup_name}</p>
                </div>
                <span className={`statusMark ${statusClass(activeResult.status)}`}>{statusLabel(activeResult.status)}</span>
              </div>
              <div className="setupMapGrid">
                <article>
                  <small>Fokus</small>
                  <strong>{activeGuide.focus}</strong>
                  <span>{directionThesis(activeCandidate)}</span>
                </article>
                <article>
                  <small>Entry-Logik</small>
                  <strong>{activeGuide.entry}</strong>
                  <span>{timeWindow(activeCandidate)}</span>
                </article>
                <article>
                  <small>Exit/Risiko</small>
                  <strong>{activeGuide.exit}</strong>
                  <span>Default {activeCandidate.risk_percent || context.default_risk_percent}% Risiko, SL und CRV &gt;= 1:1 Pflicht.</span>
                </article>
              </div>
              <div className="setupChecklistRow">
                <div>
                  <h3>Bestaetigungen</h3>
                  <div className="focusRules compactRules">
                    {activeGuide.confirmations.map((item) => <span key={item}>{item}</span>)}
                  </div>
                </div>
                <div>
                  <h3>Blocker</h3>
                  <div className="failList compactRules">
                    {activeGuide.blockers.map((item) => <span key={item}>{item}</span>)}
                  </div>
                </div>
              </div>
            </section>

            <section className="panel chatIdeasPanel">
              <div className="panelHeader tight">
                <div>
                  <h2>Tagesaktuelle Pruefkandidaten</h2>
                  <p>Nur heutige Updates duerfen Kandidaten erzeugen. Aeltere Chat-Inhalte bleiben Regel- und Kontextarchiv, keine Tagesentscheidung.</p>
                </div>
                <button type="button" className="ghostButton" onClick={() => setActiveView('updates')}>Update-Feed</button>
              </div>
              <div className="chatIdeaGrid">
                {chatTradeIdeas.slice(0, 6).map((idea) => (
                  <article className="chatIdeaCard" key={idea.idea_id}>
                    <div className="candidateTop">
                      <strong>{idea.symbol}</strong>
                      <span className="badge watch">Score {Math.round(idea.score)}</span>
                    </div>
                    <span>{shortSetupName(idea.setup_name)} | {marketLabel(idea.market)} | {idea.session}</span>
                    <small>{idea.source_type}</small>
                    <small>{idea.timestamp} | Prueffen ab {idea.planned_time}</small>
                    <p>{idea.summary}</p>
                    <div className="focusRules compactRules">
                      {idea.required_checks.slice(0, 4).map((item) => <span key={item}>{item}</span>)}
                      {idea.required_checks.length === 0 && <span>Pflichtchecks aus Update manuell ableiten</span>}
                    </div>
                    <div className="failList compactRules">
                      {idea.blockers.slice(0, 3).map((item) => <span key={item}>{item}</span>)}
                      {idea.blockers.length === 0 && <span>Blocker im Setup-Check pruefen</span>}
                    </div>
                    <button type="button" className="secondaryButton" onClick={() => addChatTradeIdea(idea)}>
                      In Focus Desk pruefen
                    </button>
                  </article>
                ))}
                {chatTradeIdeas.length === 0 && (
                  <span className="emptyState">
                    Keine tagesaktuellen Update-Kandidaten. Erst aktuellen Chat-/News-/Kalenderstand laden, dann pruefen.
                  </span>
                )}
              </div>
            </section>

            <section className="panel candidateTablePanel">
              <div className="panelHeader tight">
                <div>
                  <h2>Watchlist Dashboard</h2>
                  <p>Auswahl anklicken, rechts bearbeiten</p>
                </div>
                <div className="candidateActions">
                  <select
                    className="assetPicker"
                    aria-label="Asset fuer neuen Kandidaten"
                    value={candidateAssetDraft}
                    onChange={(event) => setCandidateAssetDraft(event.target.value)}
                  >
                    <option value="">Asset waehlen</option>
                    {assetOptions.map((option) => (
                      <option value={option.symbol} key={option.symbol}>
                        {option.symbol} | {marketLabel(option.market)} | {shortSetupName(option.setup_name)}
                        {focusedSymbols.has(option.symbol) ? ' | im Fokus' : ''}
                      </option>
                    ))}
                  </select>
                  <button type="button" className="ghostButton" onClick={addCandidate}>
                    {candidateAssetDraft && focusedSymbols.has(candidateAssetDraft) ? 'Kandidat oeffnen' : '+ Kandidat'}
                  </button>
                </div>
              </div>
              <div className="candidateTable" role="table" aria-label="Setup Kandidaten">
                <div className="candidateHeaderRow" role="row">
                  <span>Asset</span>
                  <span>Status</span>
                  <span>Setup</span>
                  <span>Zeit</span>
                  <span>CRV</span>
                  <span>Check</span>
                  <span>Blocker</span>
                </div>
                {rankedEvaluations.map(({ candidate, result }) => (
                  <button
                    type="button"
                    className={`candidateRow ${candidate.candidate_id === activeCandidate.candidate_id ? 'active' : ''}`}
                    key={candidate.candidate_id}
                    onClick={() => setActiveId(candidate.candidate_id)}
                  >
                    <span className="assetCell">
                      <strong>{candidate.symbol || 'Symbol fehlt'}</strong>
                      <small>{marketLabel(candidate.market)}</small>
                    </span>
                    <span><mark className={`statusMark ${statusClass(result.status)}`}>{statusLabel(result.status)}</mark></span>
                    <span>{shortSetupName(candidate.setup_name)}</span>
                    <span>{candidate.planned_time}</span>
                    <span>{display(result.crv)}</span>
                    <span>
                      <span className="tableProgress"><i style={{ width: `${result.completionScore}%` }} /></span>
                      <small>{result.completionScore}%</small>
                    </span>
                    <span className="blockerCell">{firstBlockingReason(result)}</span>
                  </button>
                ))}
              </div>
            </section>

            <section className="panel sourceDashboard">
              <div className="panelHeader tight">
                <div>
                  <h2>Quellen</h2>
                  <p>Schnellzugriff statt Textwand</p>
                </div>
                <a className="externalLink" href={sourceLinks.xPro} target="_blank" rel="noreferrer">X Pro</a>
              </div>
              <div className="sourceChips">
                <a href={sourceLinks.tradingView} target="_blank" rel="noreferrer">TradingView</a>
                <a href={sourceLinks.seekingAlpha} target="_blank" rel="noreferrer">Seeking Alpha</a>
                <a href={sourceLinks.investingCalendar} target="_blank" rel="noreferrer">Kalender</a>
                <a href={sourceLinks.forexLive} target="_blank" rel="noreferrer">ForexLive</a>
              </div>
              <details className="dashboardDetails">
                <summary>News-Deck anzeigen</summary>
                <div className="sourceGrid">
                  {newsDeckColumns.map((column) => (
                    <article className="sourceCard" key={column.title}>
                      <strong>{column.title}</strong>
                      <span>{column.symbols.length ? column.symbols.join(' | ') : 'Watchlist'}</span>
                      <small>{column.blocker}</small>
                      <a href={column.url} target="_blank" rel="noreferrer">Oeffnen</a>
                    </article>
                  ))}
                </div>
              </details>
            </section>
          </section>

          <aside className="dashboardSide">
            <section className="panel activeSummary">
              <div className="panelHeader tight">
                <div>
                  <h2>{activeCandidate.symbol || 'Symbol fehlt'}</h2>
                  <p>{marketLabel(activeCandidate.market)} | {shortSetupName(activeCandidate.setup_name)}</p>
                </div>
                <span className={`badge ${statusClass(activeResult.status)}`}>{statusLabel(activeResult.status)}</span>
              </div>
              <div className="decisionStatus compact">
                <small>Dashboard-Entscheidung</small>
                <strong>{statusLabel(activeResult.status)}</strong>
              </div>
              <div className="metrics">
                <span><small>Risiko</small>{display(activeResult.riskAmount)}</span>
                <span><small>Groesse</small>{display(activeResult.positionSize)}</span>
                <span><small>CRV</small>{display(activeResult.crv)}</span>
              </div>
              <p className="ruleLine">Nicht handeln ohne die 5 Pre-Checks, Stop Loss, Take Profit/Exit und CRV &gt;= 1:1.</p>
              <div className="failList compact">
                {activeResult.failed.length ? activeResult.failed.slice(0, 5).map((item) => <span key={item}>{item}</span>) : <span>Alle 5 Pre-Checks erfuellt</span>}
              </div>
              <div className="actionRow">
                <button type="button" className="ghostButton" onClick={removeActiveCandidateFromFocus}>
                  Aus Fokus entfernen
                </button>
              </div>
            </section>

            <section className="panel quickTicket">
              <div className="panelHeader tight">
                <div>
                  <h2>Schnell-Ticket</h2>
                  <p>Nur die Felder, die entscheiden</p>
                </div>
              </div>
              <div className="quickGrid">
                <Field label="Asset" compact>
                  <select value={activeCandidate.symbol || ''} onChange={(event) => applyAssetToActive(event.target.value)}>
                    <option value="">Asset waehlen</option>
                    {assetOptions.map((option) => (
                      <option value={option.symbol} key={option.symbol}>
                        {option.symbol} | {marketLabel(option.market)} | {shortSetupName(option.setup_name)}
                        {focusedSymbols.has(option.symbol) ? ' | im Fokus' : ''}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Richtung" compact>
                  <select value={activeCandidate.direction} onChange={(event) => updateActive('direction', event.target.value)}>
                    <option value="conditional">Bedingt</option>
                    <option value="long">Long</option>
                    <option value="short">Short</option>
                  </select>
                </Field>
                <Field label="Zeit" compact>
                  <input type="time" value={activeCandidate.planned_time} onChange={(event) => updateActive('planned_time', event.target.value)} />
                </Field>
                <Field label="Entry" compact>
                  <input {...inputProps(activeCandidate.entry, (value) => updateActive('entry', value))} placeholder="0.00" />
                </Field>
                <Field label="Stop" compact>
                  <input {...inputProps(activeCandidate.stop_loss, (value) => updateActive('stop_loss', value))} placeholder="Pflicht" />
                </Field>
                <Field label="Ziel" compact>
                  <input {...inputProps(activeCandidate.take_profit, (value) => updateActive('take_profit', value))} placeholder="Pflicht" />
                </Field>
                <Field label="Risiko %" compact>
                  <input {...inputProps(activeCandidate.risk_percent, (value) => updateActive('risk_percent', value), '0.25')} />
                </Field>
              </div>
              <details className="dashboardDetails">
                <summary>Details bearbeiten</summary>
                <div className="quickGrid">
                  <Field label="Symbol manuell" compact>
                    <input value={activeCandidate.symbol} onChange={(event) => updateActive('symbol', event.target.value.toUpperCase())} />
                  </Field>
                  <Field label="Setup" compact>
                    <select value={activeCandidate.setup_name} onChange={(event) => updateActive('setup_name', event.target.value)}>
                      {setupOptions.map((setup) => <option value={setup} key={setup}>{setup}</option>)}
                    </select>
                  </Field>
                  <Field label="Punktwert" compact>
                    <input {...inputProps(activeCandidate.unit_value, (value) => updateActive('unit_value', value))} />
                  </Field>
                  <Field label="Katalysator" compact>
                    <input value={activeCandidate.catalyst} onChange={(event) => updateActive('catalyst', event.target.value)} />
                  </Field>
                </div>
                <Field label="Notiz">
                  <textarea value={activeCandidate.notes} onChange={(event) => updateActive('notes', event.target.value)} />
                </Field>
              </details>
            </section>

            <section className="panel checklistPanel">
              <div className="panelHeader tight">
                <div>
                  <h2>5 Pre-Checks</h2>
                  <p>{activeResult.completionScore}% erledigt</p>
                </div>
              </div>
              <div className="compactChecklist">
                {activeCandidate.conditions.map((condition, index) => (
                  <PreCheckToggle
                    key={condition.name}
                    condition={condition}
                    definition={preCheckDefinitions[index]}
                    onChange={(value) => updateCondition(condition.name, value)}
                  />
                ))}
              </div>
              <div className="actionStack">
                <button type="button" className="secondaryButton" onClick={createRunningTradeDraft}>Trade starten</button>
                <button type="button" className="ghostButton" onClick={exportDailyPlan}>Export</button>
              </div>
            </section>

            <section className="panel utilityPanel">
              <details className="dashboardDetails">
                <summary>Watchlist Import</summary>
                <textarea
                  className="importBox compact"
                  value={importText}
                  placeholder={importExample}
                  onChange={(event) => setImportText(event.target.value)}
                />
                <div className="actionRow">
                  <button type="button" onClick={importWatchlist}>Importieren</button>
                  <label className="fileButton">
                    Datei laden
                    <input type="file" accept=".txt,.csv" onChange={importWatchlistFile} />
                  </label>
                </div>
              </details>
              <button type="button" className="ghostButton" onClick={resetDay}>Tag zuruecksetzen</button>
            </section>
          </aside>
        </section>
        </details>
      </>
    );
  };

  const renderJournal = () => (
    <section className="journalWorkspace">
      <section className="proBoardGrid journalOverview">
        <section className="panel proBoardPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Journal Cockpit</h2>
              <p>{activeJournalSymbol} | {activeJournalDraft ? draftStatusLabel(activeJournalDraft.status) : 'Kein laufender Trade'}</p>
            </div>
            <span className={`statusMark ${activeJournalDraft?.lifecycle_status === 'open' ? 'watch' : journalScore >= 80 ? 'ok' : 'danger'}`}>
              {journalScore}% komplett
            </span>
          </div>
          <div className="decisionFactGrid">
            <span><small>Laufend</small>{runningJournalDrafts.length}</span>
            <span><small>Nacharbeit</small>{reviewInsights.openReviews}</span>
            <span><small>Ø R</small>{display(journalMetrics.avgR)}</span>
            <span><small>Treffer</small>{display(journalMetrics.winRate, 0)}%</span>
          </div>
          <div className="singleBar">
            <i style={{ width: `${journalScore}%` }} />
          </div>
        </section>

        <section className="panel proBoardPanel imageBoard">
          <div className="panelHeader tight">
            <div>
              <h2>Bildstatus</h2>
              <p>Vorher/Nachher fuer Review sichtbar halten.</p>
            </div>
          </div>
          <div className="imagePreviewGrid">
            <article>
              <small>Vorher</small>
              {journal.screenshot_before ? <img src={journal.screenshot_before} alt="Chart vor Trade" /> : <span>fehlt</span>}
            </article>
            <article>
              <small>Nachher</small>
              {journal.screenshot_after ? <img src={journal.screenshot_after} alt="Chart nach Trade" /> : <span>fehlt</span>}
            </article>
          </div>
        </section>
      </section>

      <details className="proDetails journalDetails">
        <summary>
          <strong>Journal-Details bearbeiten</strong>
          <span>Trade starten, abschliessen, Bilder und Review erfassen</span>
        </summary>
      <section className="journalHero">
        <section className="panel journalSummary">
          <div className="panelHeader">
            <div>
              <h2>Daily Journal</h2>
              <p>{activeJournalSymbol} | {activeJournalDraft?.setup || activeCandidate.setup_name} | {activeJournalDraft ? draftStatusLabel(activeJournalDraft.status) : statusLabel(activeResult.status)}</p>
            </div>
            <span>{journalScore}% vollstaendig</span>
          </div>
          <div className={`journalLifecycle ${activeJournalDraft?.lifecycle_status === 'open' ? 'open' : 'idle'}`}>
            <small>Aktiver Journal-Trade</small>
            <strong>{activeJournalDraft ? `${activeJournalDraft.symbol} | ${draftStatusLabel(activeJournalDraft.status)}` : 'Kein laufender Trade geladen'}</strong>
            <span>{runningJournalDrafts.length} parallel offen | Abschluss ergaenzt denselben Entwurf, kein neuer Snapshot.</span>
          </div>
          <div className="journalKpis">
            <span><small>Eintraege</small>{journalMetrics.count}</span>
            <span><small>Ø R</small>{display(journalMetrics.avgR)}</span>
            <span><small>Regelquote bekannt</small>{display(journalMetrics.ruleRate, 0)}%</span>
            <span><small>Trefferquote</small>{display(journalMetrics.winRate, 0)}%</span>
          </div>
          <div className="journalPrimaryFacts">
            <span><small>Aktiver Fall</small>{activeJournalSymbol}</span>
            <span><small>Risiko</small>{activeJournalRisk}</span>
            <span><small>Positionsgroesse</small>{activeJournalPositionSize}</span>
            <span><small>CRV geplant</small>{activeJournalPlannedCrv}</span>
          </div>
          <div className="journalPrimaryFacts orderFacts">
            <span><small>Entry</small>{activeJournalEntry}</span>
            <span><small>Stop Loss</small>{activeJournalStopLoss}</span>
            <span><small>Take Profit</small>{activeJournalTakeProfit}</span>
            <span><small>Exit</small>{activeJournalExit}</span>
          </div>
          <div className="actionRow">
            <button type="button" className="ghostButton" onClick={clearJournalSelection}>Neuer Journalfall</button>
            {activeJournalDraft && (
              <button type="button" className="ghostButton" onClick={updateRunningTradeDraft}>
                {activeJournalDraft.lifecycle_status === 'closed' ? 'Review speichern' : 'Aktiven Stand speichern'}
              </button>
            )}
          </div>
          {journalActionStatus && <p className="journalActionStatus">{journalActionStatus}</p>}
        </section>

        <section className="panel journalFlowPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Tagesabschluss</h2>
              <p>Ein Trade ist erst fertig, wenn Bild, Ergebnis, Regelcheck und Review erfasst sind.</p>
            </div>
          </div>
          <div className="journalStepList">
            {journalSteps.map((step) => (
              <article className={step.done ? 'done' : ''} key={step.label}>
                <strong>{step.label}</strong>
                <span>{step.detail}</span>
              </article>
            ))}
          </div>
          <div className="actionRow">
            <button type="button" className="secondaryButton" onClick={activeJournalDraft ? updateRunningTradeDraft : createRunningTradeDraft}>
              {journalSaveLabel}
            </button>
            <button type="button" className="dangerButton" onClick={closeRunningTradeDraft}>Trade abschliessen</button>
            <button type="button" className="ghostButton" onClick={() => setActiveView('desk')}>Zum Setup</button>
          </div>
        </section>
      </section>

      <section className="journalGrid">
        <section className="panel journalForm">
          <details className="formSection tradeEventSection secondaryEventPanel">
            <summary>
              <span>
                <strong>TradingView/Broker Event importieren</strong>
                <small>Optional: Paper-/Demo-/Broker-Fakten in den Journal-Lifecycle uebernehmen.</small>
              </span>
              <mark className="eventBadge">trade_id steuert parallele Trades</mark>
            </summary>
            <textarea
              className="eventBox"
              value={tradeEventText}
              onChange={(event) => setTradeEventText(event.target.value)}
              spellCheck="false"
            />
            <div className="actionRow">
              <button type="button" className="ghostButton" onClick={() => setTradeEventText(makeTradeEventExample('opened'))}>
                Open-Beispiel
              </button>
              <button type="button" className="ghostButton" onClick={() => setTradeEventText(makeTradeEventExample('closed_take_profit'))}>
                Close-TP
              </button>
              <button type="button" className="ghostButton" onClick={() => setTradeEventText(makeTradeEventExample('closed_stop_loss'))}>
                Close-SL
              </button>
              <button type="button" className="secondaryButton" onClick={applyTradeEventPayload}>
                Event verarbeiten
              </button>
            </div>
            {tradeEventStatus && <p className="eventStatus">{tradeEventStatus}</p>}
            <details className="captureHelp">
              <summary>TradingView MacOS App: Screenshot + Event erzeugen</summary>
              <p>TradingView-Chart sichtbar lassen, Befehl ausfuehren, danach JSON hier einfuegen oder mit `--copy` direkt aus der Zwischenablage uebernehmen.</p>
              <code>{tradingViewCaptureCommands.open}</code>
              <code>{tradingViewCaptureCommands.close}</code>
            </details>
          </details>

          <div className="formSection">
            <h3>Vor Trade</h3>
            <div className="threeGrid">
              <Field label="Emotion vor Trade">
                <select value={journal.emotion_before} onChange={(event) => updateJournal('emotion_before', event.target.value)}>
                  <option>Neutral</option>
                  <option>Ruhig</option>
                  <option>Fokussiert</option>
                  <option>Nervoes</option>
                  <option>FOMO</option>
                  <option>Frustriert</option>
                </select>
              </Field>
              <Field label="Ueberzeugung 1-10">
                <input {...inputProps(journal.confidence_level, (value) => updateJournal('confidence_level', value), '1')} min="1" max="10" />
              </Field>
              <Field label="Stress 1-5">
                <input {...inputProps(journal.stress_level, (value) => updateJournal('stress_level', value), '1')} min="1" max="5" />
              </Field>
            </div>
            <ScreenshotDropZone
              label="Screenshot vor Trade"
              value={journal.screenshot_before}
              onChange={(value) => updateJournal('screenshot_before', value)}
            />
          </div>

          <div className="formSection">
            <h3>Waehrend / Nach Trade</h3>
            <div className="threeGrid">
              <Field label="Emotion waehrend Trade">
                <input value={journal.emotion_during} onChange={(event) => updateJournal('emotion_during', event.target.value)} />
              </Field>
              <Field label="Emotion nach Trade">
                <input value={journal.emotion_after} onChange={(event) => updateJournal('emotion_after', event.target.value)} />
              </Field>
              <Field label="Fokus 1-5">
                <input {...inputProps(journal.focus_level, (value) => updateJournal('focus_level', value), '1')} min="1" max="5" />
              </Field>
            </div>
            <div className="threeGrid">
              <Field label="Exit Preis">
                <input value={journal.exit_price} onChange={(event) => updateJournal('exit_price', event.target.value)} placeholder="z. B. 59500.00" />
              </Field>
              <Field label="Exit Grund">
                <select value={journal.exit_reason} onChange={(event) => updateJournal('exit_reason', event.target.value)}>
                  <option value="">Offen / manuell pruefen</option>
                  <option value="Stop Loss">Stop Loss</option>
                  <option value="Take Profit">Take Profit</option>
                  <option value="Manuell geschlossen">Manuell geschlossen</option>
                  <option value="Teilverkauf / Management">Teilverkauf / Management</option>
                </select>
              </Field>
              <Field label="Ergebnis in R">
                <input value={journal.realized_r} onChange={(event) => updateJournal('realized_r', event.target.value)} placeholder="-1.00 / 1.25" />
              </Field>
            </div>
            <div className="threeGrid">
              <Field label="Ergebnis Geld">
                <input value={journal.result_money} onChange={(event) => updateJournal('result_money', event.target.value)} />
              </Field>
              <Field label="Gebuehren">
                <input value={journal.fees} onChange={(event) => updateJournal('fees', event.target.value)} />
              </Field>
              <Field label="Slippage">
                <input value={journal.slippage} onChange={(event) => updateJournal('slippage', event.target.value)} />
              </Field>
            </div>
            <div className="actionRow">
              <button type="button" className="ghostButton" onClick={calculateRealizedRForActive}>
                R berechnen
              </button>
            </div>
            <ScreenshotDropZone
              label="Screenshot nach Trade"
              value={journal.screenshot_after}
              onChange={(value) => updateJournal('screenshot_after', value)}
            />
          </div>

          <div className="formSection">
            <h3>Regelcheck</h3>
            <div className="complianceLine">
              <Toggle label="Regelkonform" checked={journal.rule_compliant} onChange={(value) => updateJournal('rule_compliant', value)} />
              <Field label="Verletzte Regel">
                <input value={journal.violated_rule} onChange={(event) => updateJournal('violated_rule', event.target.value)} disabled={journal.rule_compliant} />
              </Field>
            </div>
            <div className="failList">
              {activeResult.failed.length ? activeResult.failed.slice(0, 10).map((item) => <span key={item}>{item}</span>) : <span>Keine offenen Pre-Check-Blocker</span>}
            </div>
          </div>

          <div className="formSection">
            <h3>Review</h3>
            <div className="twoGrid">
              <Field label="Was war gut?">
                <textarea value={journal.what_went_well} onChange={(event) => updateJournal('what_went_well', event.target.value)} />
              </Field>
              <Field label="Verbesserung">
                <textarea value={journal.improvement} onChange={(event) => updateJournal('improvement', event.target.value)} />
              </Field>
            </div>
            <Field label="Review">
              <textarea value={journal.review} onChange={(event) => updateJournal('review', event.target.value)} />
            </Field>
            <div className="actionRow">
              <button type="button" className="secondaryButton" onClick={activeJournalDraft ? updateRunningTradeDraft : createRunningTradeDraft}>
                {journalSaveLabel}
              </button>
              <button type="button" className="dangerButton" onClick={closeRunningTradeDraft}>Trade abschliessen</button>
            </div>
          </div>
        </section>

        <aside className="panel journalFeed">
          <div className="panelHeader">
            <div>
              <h2>Aktive Nacharbeit</h2>
              <p>{runningJournalDrafts.length} laufen | {reviewInsights.openReviews} aktiv offen | {reviewInsights.importReviews} Import-Archiv offen | {reviewInsights.completedReviews} abgeschlossen</p>
            </div>
          </div>
          <div className="feedSummary">
            <span><small>Laufend</small>{runningJournalDrafts.length}</span>
            <span><small>Aktiv offen</small>{reviewInsights.openReviews}</span>
            <span><small>Ohne R</small>{reviewInsights.noRealizedR}</span>
            <span><small>Ohne Bilder</small>{reviewInsights.noScreenshots}</span>
          </div>
          {runningJournalDrafts.length > 0 && (
            <section className="runningTradesBox">
              <h3>Laufende Trades</h3>
              {runningJournalDrafts.map((draft) => (
                <article className={draft.draft_id === activeJournalDraftId ? 'active' : ''} key={draft.draft_id}>
                  <div>
                    <strong>{draft.symbol}</strong>
                    <span>{draft.setup} | {directionLabel(draft.direction)} | seit {String(draft.started_at || '').slice(11, 16) || '--'}</span>
                  </div>
                  <div className="actionRow">
                    <button type="button" className="ghostButton" onClick={() => loadJournalDraft(draft)}>Laden</button>
                    <button type="button" className="dangerButton" onClick={() => closeJournalDraft(draft)}>Abschliessen</button>
                  </div>
                </article>
              ))}
            </section>
          )}
          <div className="draftList">
            {reviewQueueEntries.length === 0 && (
              <span className="emptyState">
                Keine aktive Nacharbeit. Importierte Historie und technische Bewertungen liegen unter Trades.
              </span>
            )}
            {reviewQueueEntries.slice(0, 80).map((draft) => (
              <article className={`draftCard ${draft.draft_id === activeJournalDraftId ? 'active' : ''}`} key={draft.draft_id}>
                <div>
                  <strong>
                    {draft.symbol} <mark className={`statusMark ${reviewQueueStatusClass(draft)}`}>{reviewQueueStatusLabel(draft)}</mark>
                  </strong>
                  <span>{draft.date} | {draft.setup} | {directionLabel(draft.direction)} | {draft.planned_time}</span>
                  <small>{draft.source || 'Tagesprozess'}{draft.lifecycle_status === 'open' ? ` | gestartet ${String(draft.started_at || '').slice(11, 16)}` : ''}</small>
                </div>
                <div className="draftMetrics">
                  <span>CRV {draft.planned_crv}</span>
                  <span>{draft.result_money ? `${draft.result_money}` : `R ${draft.realized_r || '--'}`}</span>
                  <span>{draft.completion || 0}%</span>
                </div>
                <div className="draftActions">
                  <button type="button" className="ghostButton" onClick={() => loadJournalDraft(draft)}>
                    {draft.imported ? 'In Review uebernehmen' : draft.draft_id === activeJournalDraftId ? 'Aktiv bearbeiten' : 'Bearbeiten'}
                  </button>
                  {!draft.imported && draft.status !== 'Abgeschlossen' && (
                      <button type="button" className="dangerButton" onClick={() => closeJournalDraft(draft)}>
                        Abschliessen
                      </button>
                  )}
                </div>
                {draft.failed_conditions?.length > 0 && <small>{draft.failed_conditions.slice(0, 3).join(' | ')}</small>}
              </article>
            ))}
          </div>
        </aside>
      </section>
      </details>
    </section>
  );

  const renderUpdates = () => (
    <section className="updatesWorkspace">
      <section className="proBoardGrid updatesOverview">
        <section className="panel proBoardPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Live & News Cockpit</h2>
              <p>Nur Quellenstatus und Entscheidungsreife.</p>
            </div>
            <span className={`statusMark ${liveStatusClass}`}>{liveStatusText}</span>
          </div>
          <div className="decisionFactGrid">
            <span><small>Live</small>{liveStatusText}</span>
            <span><small>Stand</small>{latestUpdateDateLabel}</span>
            <span><small>Pflicht-Chats</small>{requiredChatCoverageText}</span>
            <span><small>Updates</small>{chatUpdateFeed.update_count || chatUpdates.length}</span>
          </div>
          <p className="focusSentence">
            {requiredChatsAreToday
              ? 'Pflicht-Update-Chats sind tagesaktuell. Trotzdem keine Orderfreigabe, nur manuelle Pruefung.'
              : `Neuester Zusatzkontext ist ${latestUpdateDateLabel}; die Pflicht-ChatGPT-Exports bleiben alt und sind nur historischer Kontext.`}
          </p>
        </section>

        <section className="panel proBoardPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Heutige Update-Kandidaten</h2>
              <p>Nur aus Updates mit heutigem Datum. Keine Empfehlung.</p>
            </div>
          </div>
          <div className="proDecisionList">
            {chatTradeIdeas.slice(0, 3).map((idea) => (
              <button type="button" className="proDecisionItem" key={idea.idea_id} onClick={() => addChatTradeIdea(idea)}>
                <span>
                  <strong>{idea.symbol}</strong>
                  <small>{shortSetupName(idea.setup_name)} | {idea.session}</small>
                </span>
                <mark className="statusMark watch">Score {Math.round(idea.score)}</mark>
                <i>{idea.summary}</i>
              </button>
            ))}
            {chatTradeIdeas.length === 0 && (
              <span className="emptyState">Keine tagesaktuellen Update-Ideen geladen.</span>
            )}
          </div>
        </section>
      </section>

      <section className="panel updateProcessPanel">
        <div className="panelHeader tight">
          <div>
            <h2>Prozessweg</h2>
            <p>Von frischer Information zur manuellen Setup-Pruefung. Keine Orderfreigabe.</p>
          </div>
          <span className={`statusMark ${chatUpdateRefreshClass}`}>{chatUpdateRefreshText}</span>
        </div>
        <div className="updateProcessGrid">
          <article>
            <mark>1</mark>
            <strong>Aktualisieren</strong>
            <span>Feed und Live-Status neu laden.</span>
            <button type="button" className="ghostButton" disabled={chatUpdateRefreshBusy} onClick={() => refreshChatUpdateFeed()}>
              Jetzt aktualisieren
            </button>
          </article>
          <article>
            <mark>2</mark>
            <strong>Quelle bewerten</strong>
            <span>{requiredChatCoverageText} | {liveStatusText}</span>
            <button type="button" className="ghostButton" onClick={() => openUpdateDetails('.chatSourcePanel')}>
              Quellen ansehen
            </button>
          </article>
          <article>
            <mark>3</mark>
            <strong>Information oeffnen</strong>
            <span>{selectedChatUpdate ? `${selectedChatUpdate.timestamp} | ${selectedChatUpdate.session}` : 'Kein Update geladen'}</span>
            <button type="button" className="ghostButton" onClick={() => openUpdateDetails('.selectedUpdatePanel')}>
              Details anzeigen
            </button>
          </article>
          <article>
            <mark>4</mark>
            <strong>Manuell pruefen</strong>
            <span>{selectedUpdateIsToday ? 'Tagesaktuell pruefbar' : 'Nur historischer Kontext'}</span>
            <button
              type="button"
              className="secondaryButton"
              disabled={!selectedUpdateIsToday || !(selectedChatUpdate?.assets || []).length}
              onClick={() => addSelectedUpdateToDesk()}
            >
              In Focus Desk
            </button>
          </article>
        </div>
      </section>

      <details className="proDetails updateDetails" open={updatesDetailsOpen} onToggle={(event) => setUpdatesDetailsOpen(event.currentTarget.open)}>
        <summary>
          <strong>Update-Details anzeigen</strong>
          <span>Quellenabdeckung, Live-Bridge, Kandidaten und kompletter Feed</span>
        </summary>
      <section className="panel updatesHero">
        <div className="panelHeader">
          <div>
            <h2>News, Sessions & ChatGPT-Updates</h2>
            <p>Strukturierte Integration der importierten Trading-Projektchats mit Zeitstempel, Session, Assets, Pflichtchecks und Blockern.</p>
          </div>
          <div className="updateRefreshControls">
            <span className={`statusMark ${chatUpdateRefreshClass}`}>{chatUpdateRefreshText}</span>
            <label className="autoRefreshToggle">
              <input
                type="checkbox"
                checked={chatUpdateAutoRefresh}
                onChange={(event) => setChatUpdateAutoRefresh(event.target.checked)}
              />
              Auto
            </label>
            <button
              type="button"
              className="ghostButton"
              disabled={chatUpdateRefreshBusy}
              onClick={() => refreshChatUpdateFeed()}
            >
              Jetzt aktualisieren
            </button>
          </div>
        </div>
        <div className="journalKpis">
          <span><small>Chats</small>{chatUpdateFeed.chat_count || 0}</span>
          <span><small>Pflicht-Chats</small>{coveredRequiredChatCount}/{requiredChatCount}</span>
          <span><small>Updates</small>{chatUpdateFeed.update_count || chatUpdates.length}</span>
          <span><small>Gefiltert</small>{filteredChatUpdates.length}</span>
          <span><small>Generiert</small>{chatUpdateFeed.generated_at ? chatUpdateFeed.generated_at.slice(0, 10) : '--'}</span>
          <span><small>Neuester Chat</small>{requiredChatLatestKey || '--'}</span>
          <span><small>Geprueft</small>{chatUpdateRefreshLabel}</span>
        </div>
        <p className="ruleLine">
          Die vier ChatGPT-Update-Chats speisen den Focus Desk als strukturierter Kontext. Entry, Richtung, Risiko, Stop Loss, Take Profit und CRV muessen weiterhin manuell bestaetigt werden.
        </p>
        {requiredChatCoverage.length > 0 && !requiredChatsAreToday && (
          <p className="feedWarning">
            Die vier ChatGPT-Update-Chats sind eingebunden, aber der neueste Chat-Export ist vom {requiredChatLatestKey || 'unbekannt'}.
            Tagesaktuelle Bewertung braucht einen neuen ChatGPT-Export oder Live-Quelle.
          </p>
        )}
        {!chatUpdateFreshness.isToday && chatUpdates.length > 0 && (
          <p className="feedError">
            Der geladene Feed ist nicht tagesaktuell. Neuester Inhalt: {chatUpdateFreshness.latestKey || 'unbekannt'}.
            Bitte Chat-/News-Export oder Tagesupdate neu erzeugen.
          </p>
        )}
        {chatUpdateRefresh.error && <p className="feedError">{chatUpdateRefresh.error}</p>}
      </section>

      <section className="panel selectedUpdatePanel">
        <div className="panelHeader tight">
          <div>
            <h2>Ausgewaehlte Information</h2>
            <p>{selectedChatUpdate ? `${selectedChatUpdate.chat_title} | ${selectedChatUpdate.timestamp}` : 'Noch kein Update ausgewaehlt'}</p>
          </div>
          <span className={`statusMark ${selectedUpdateIsToday ? 'ok' : 'watch'}`}>
            {selectedUpdateIsToday ? 'Tagesaktuell' : 'Historisch'}
          </span>
        </div>
        {selectedChatUpdate ? (
          <div className="selectedUpdateGrid">
            <article className="selectedUpdateSummary">
              <small>{selectedChatUpdate.session} | {selectedChatUpdate.timestamp_source === 'chat_text' ? 'Zeit aus Chat' : 'Exportzeit'}</small>
              <strong>{selectedChatUpdate.summary}</strong>
              <div className="updateTags">
                {(selectedChatUpdate.assets || []).slice(0, 10).map((asset) => <span key={asset}>{asset}</span>)}
                {(selectedChatUpdate.themes || []).slice(0, 8).map((theme) => <span key={theme}>{theme}</span>)}
              </div>
              <div className="actionRow">
                {selectedChatUpdate.chat_url && (
                  <a className="externalLink" href={selectedChatUpdate.chat_url} target="_blank" rel="noreferrer">
                    Quelle oeffnen
                  </a>
                )}
                <button
                  type="button"
                  className="secondaryButton"
                  disabled={!selectedUpdateIsToday || !(selectedChatUpdate.assets || []).length}
                  onClick={() => addSelectedUpdateToDesk(selectedChatUpdate)}
                >
                  Erstes Asset pruefen
                </button>
              </div>
              {!selectedUpdateIsToday && (
                <p className="feedWarning">
                  Dieses Update ist nicht von heute. Es bleibt Kontext; fuer den Focus Desk erst heutigen Chat-/News-/Kalenderstand laden.
                </p>
              )}
            </article>
            <article>
              <h3>Pflichtchecks</h3>
              <div className="focusRules compactRules">
                {(selectedChatUpdate.required_checks || []).length
                  ? selectedChatUpdate.required_checks.map((item) => <span key={item}>{item}</span>)
                  : <span>Keine Pflichtchecks extrahiert. Manuell aus dem Update ableiten.</span>}
              </div>
            </article>
            <article>
              <h3>Blocker</h3>
              <div className="failList compactRules">
                {(selectedChatUpdate.blockers || []).length
                  ? selectedChatUpdate.blockers.map((item) => <span key={item}>{item}</span>)
                  : <span>Keine harte Blockerkennung im Text.</span>}
              </div>
            </article>
          </div>
        ) : (
          <span className="emptyState">Noch keine Information geladen.</span>
        )}
      </section>

      <section className="panel chatSourcePanel">
        <div className="panelHeader tight">
          <div>
            <h2>ChatGPT-Quellenabdeckung</h2>
            <p>Pflicht sind die vier Update-Chats. Breaking News und Webchecks sind Zusatzkontext.</p>
          </div>
          <span className={`statusMark ${missingRequiredChats.length ? 'danger' : requiredChatsAreToday ? 'ok' : 'watch'}`}>
            {missingRequiredChats.length ? 'Unvollstaendig' : requiredChatCoverageText}
          </span>
        </div>
        <div className="chatSourceGrid">
          {[...requiredChatCoverage, ...optionalChatCoverage].map((source) => (
            <article className={`chatSourceCard ${source.required ? 'required' : 'optional'} ${chatCoverageClass(source)}`} key={source.canonical_title}>
              <div>
                <small>{source.required ? 'Pflicht-Update-Chat' : 'Zusatzkontext'}</small>
                <strong>{source.canonical_title}</strong>
              </div>
              <span className={`statusMark ${chatCoverageClass(source)}`}>{coverageStatusText(source)}</span>
              <p>{source.update_count || 0} Updates | letzter Stand {source.latest_timestamp || '--'}</p>
              <div className="updateTags compactTags">
                {(source.sessions || []).slice(0, 4).map((session) => <span key={session}>{session}</span>)}
                {(source.assets || []).slice(0, 6).map((asset) => <span key={asset}>{asset}</span>)}
              </div>
              {source.url && <a href={source.url} target="_blank" rel="noreferrer">Chat oeffnen</a>}
            </article>
          ))}
        </div>
      </section>

      <section className={`panel liveStatusPanel ${liveStatusClass}`}>
        <div className="panelHeader tight">
          <div>
            <h2>Live-Status der Pflichtquellen</h2>
            <p>Sekundenaktuelle Pruefung ist nur moeglich, wenn Kurse, Orders, Kalender und News live verbunden sind.</p>
          </div>
          <div className="updateRefreshControls">
            <span className={`statusMark ${liveStatusClass}`}>{liveStatusText}</span>
            <span className="liveClock">geprueft {liveLastCheckedLabel}</span>
          </div>
        </div>
        <div className="liveSourceGrid">
          {(liveStatus.evaluations || []).map((source) => (
            <article key={source.source_name}>
              <strong>{source.source_name}</strong>
              <span className={`statusMark ${source.status === 'live' ? 'ok' : source.status === 'stale' ? 'watch' : 'danger'}`}>
                {source.status}
              </span>
              <small>{sourceAgeLabel(source)} alt | Grenze {source.stale_after_seconds}s | {source.message}</small>
              {(source.details || []).slice(0, 4).map((detail) => (
                <small className="sourceDetail" key={detail}>{detail}</small>
              ))}
            </article>
          ))}
          {!(liveStatus.evaluations || []).length && <span className="emptyState">Noch kein Live-Status geladen</span>}
        </div>
        {((liveStatus.warnings || []).length > 0 || liveStatusFileIsStale) && (
          <div className="liveWarnings">
            {liveStatus.warnings.map((warning) => <span key={warning}>{warning}</span>)}
            {liveStatusFileIsStale && <span>Statusdatei wurde seit {Math.round(liveStatusFileAgeSeconds)}s nicht neu geschrieben.</span>}
          </div>
        )}
        {liveFeedRefresh.error && <p className="feedError">{liveFeedRefresh.error}</p>}
      </section>

      <section className="panel liveReadinessPanel">
        <div className="panelHeader tight">
          <div>
            <h2>Anschlussplan fuer Live-Quellen</h2>
            <p>
              {liveAdapterConfigStatus.env_file?.exists ? '.env erkannt' : '.env fehlt'} |
              {' '}{liveAdapterConfigStatus.configured_count || 0}/4 Adapter konfiguriert |
              {' '}{liveReadinessMissing.length ? `${liveReadinessMissing.length} Quellen nicht live` : 'alle Quellen live'}
            </p>
          </div>
          <span className={`statusMark ${liveReadinessMissing.length ? 'danger' : 'ok'}`}>
            {liveReadinessMissing.length ? 'Anschluss offen' : 'Bereit'}
          </span>
        </div>
        <div className="liveReadinessGrid">
          {liveReadiness.map((item) => (
            <article key={item.source} className={item.ready ? 'ready' : 'missing'}>
              <div>
                <small>{item.title} | {item.stale}</small>
                <strong>{item.source}</strong>
              </div>
              <span className={`statusMark ${item.ready ? 'ok' : item.status === 'stale' ? 'watch' : 'danger'}`}>{item.status}</span>
              <p>{item.message}</p>
              <small>{item.configMessage}</small>
              <small>
                {item.configured
                  ? `Konfiguriert: ${item.locationMasked || 'Quelle gesetzt'}${item.fileExists === false ? ' | Datei fehlt' : ''}`
                  : 'Noch nicht in .env gesetzt'}
              </small>
              <code>{item.config}</code>
              <small>{item.nextStep}</small>
              {item.link && <a href={item.link} target="_blank" rel="noreferrer">Quelle / Zugang oeffnen</a>}
            </article>
          ))}
        </div>
        <p className="ruleLine">
          Reihenfolge: <code>.env</code> anlegen, echte Feed-/Dateipfade setzen, dann <code>python3 tools/run_configured_live_adapters.py --interval-seconds 5</code> starten.
          Ohne echte Quelle bleibt der Status korrekt auf <strong>missing</strong> oder <strong>blocked</strong>.
        </p>
      </section>

      <section className="panel liveBridgePanel">
        <div className="panelHeader tight">
          <div>
            <h2>Live-Bridge Anschluss</h2>
            <p>Lokale Adapter schreiben JSON nach <code>reports/live_bridge_inbox</code>. Der Inbox-Service aktualisiert daraus den Quellenstatus; es gibt keine Orderausfuehrung.</p>
          </div>
          <span className="statusMark watch">Information only</span>
        </div>
        <div className="liveBridgeGrid">
          {liveBridgeCards.map((card) => (
            <article key={card.source}>
              <small>{card.title} | Frische {card.stale}</small>
              <strong>{card.source}</strong>
              <span>{card.connect}</span>
              <code>{card.config}</code>
              <code>{card.payload}</code>
              {card.link && <a href={card.link} target="_blank" rel="noreferrer">Quelle oeffnen</a>}
            </article>
          ))}
        </div>
        <p className="ruleLine">
          Adapter: <code>python3 tools/run_configured_live_adapters.py --interval-seconds 5</code>. Inbox:
          <code>python3 tools/run_live_bridge_inbox.py --interval-seconds 1</code>. Erst wenn Kurse, Orders, Kalender und News frisch sind, zeigt das Portal <strong>Sekundenfrisch</strong>.
        </p>
      </section>

      <section className="panel chatIdeasPanel">
        <div className="panelHeader tight">
          <div>
            <h2>Heutige Pruefkandidaten aus Updates</h2>
            <p>Alte Chat-Exporte liefern nur Kontext. Ein Trade bleibt blockiert, bis Setup, Richtung, Entry, Stop, Ziel, CRV und 5 Pre-Checks passen.</p>
          </div>
        </div>
        <div className="chatIdeaGrid">
          {chatTradeIdeas.length === 0 && (
            <span className="emptyState">
              Keine heutigen Update-Kandidaten. Historische Chat-Inhalte bleiben unten im Feed filterbar.
            </span>
          )}
          {chatTradeIdeas.map((idea) => (
            <article className="chatIdeaCard" key={idea.idea_id}>
              <div className="candidateTop">
                <strong>{idea.symbol}</strong>
                <span className="badge watch">Score {Math.round(idea.score)}</span>
              </div>
              <span>{shortSetupName(idea.setup_name)} | {marketLabel(idea.market)} | {idea.session}</span>
              <small>{idea.source_type}</small>
              <small>{idea.timestamp} | Prueffen ab {idea.planned_time}</small>
              <p>{idea.summary}</p>
              <button type="button" className="secondaryButton" onClick={() => addChatTradeIdea(idea)}>
                In Focus Desk pruefen
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="panel updateTablePanel">
        <div className="panelHeader tight">
          <div>
            <h2>Update-Feed</h2>
            <p>Neueste importierte Chat-Erkenntnisse oben. Filter helfen beim Tagesupdate und Session-Review.</p>
          </div>
        </div>
        <div className="tradeFilters">
          <Field label="Session" compact>
            <select value={chatUpdateFilters.session} onChange={(event) => setChatUpdateFilters({ ...chatUpdateFilters, session: event.target.value })}>
              <option value="all">Alle Sessions</option>
              {chatSessions.map((session) => <option value={session} key={session}>{session}</option>)}
            </select>
          </Field>
          <Field label="Asset" compact>
            <select value={chatUpdateFilters.asset} onChange={(event) => setChatUpdateFilters({ ...chatUpdateFilters, asset: event.target.value })}>
              <option value="all">Alle Assets</option>
              {chatAssets.map((asset) => <option value={asset} key={asset}>{asset}</option>)}
            </select>
          </Field>
          <Field label="Thema" compact>
            <select value={chatUpdateFilters.theme} onChange={(event) => setChatUpdateFilters({ ...chatUpdateFilters, theme: event.target.value })}>
              <option value="all">Alle Themen</option>
              {chatThemes.map((theme) => <option value={theme} key={theme}>{theme}</option>)}
            </select>
          </Field>
          <button type="button" className="ghostButton" onClick={() => setChatUpdateFilters({ session: 'all', asset: 'all', theme: 'all' })}>
            Filter zuruecksetzen
          </button>
        </div>
        <div className="updateFeedList">
          {filteredChatUpdates.length === 0 && <span className="emptyState">Keine Updates fuer diese Filterauswahl</span>}
          {filteredChatUpdates.map((update) => (
            <article className={`updateCard ${update.id === selectedChatUpdate?.id ? 'active' : ''}`} key={update.id}>
              <header>
                <div>
                  <small>{update.timestamp} | {update.session} | {update.timestamp_source === 'chat_text' ? 'Zeit aus Chat' : 'Exportzeit'}</small>
                  <strong>{update.chat_title}</strong>
                </div>
                <div className="updateCardActions">
                  <button type="button" className="ghostButton" onClick={() => selectChatUpdate(update)}>
                    Details
                  </button>
                  {update.chat_url && <a href={update.chat_url} target="_blank" rel="noreferrer">Quelle</a>}
                </div>
              </header>
              <p>{update.summary}</p>
              <div className="updateTags">
                {(update.assets || []).slice(0, 12).map((asset) => <span key={asset}>{asset}</span>)}
                {(update.themes || []).slice(0, 8).map((theme) => <span key={theme}>{theme}</span>)}
              </div>
              <div className="updateChecks">
                <div>
                  <h3>Pflichtchecks</h3>
                  <div className="focusRules compactRules">
                    {(update.required_checks || []).length
                      ? update.required_checks.map((item) => <span key={item}>{item}</span>)
                      : <span>Manuell aus dem Update ableiten</span>}
                  </div>
                </div>
                <div>
                  <h3>Blocker</h3>
                  <div className="failList compactRules">
                    {(update.blockers || []).length
                      ? update.blockers.map((item) => <span key={item}>{item}</span>)
                      : <span>Keine harte Blockerkennung im Text</span>}
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
      </details>
    </section>
  );

  const renderTrades = () => (
    <section className="tradesWorkspace">
      <section className="panel tradesHero">
        <div className="panelHeader">
          <div>
            <h2>Trade-Uebersicht</h2>
            <p>Alle geladenen Broker-Imports und Tagesentwuerfe mit technischer Review-Einstufung.</p>
          </div>
          <button type="button" className="secondaryButton" onClick={exportDailyPlan}>Exportieren</button>
        </div>
        <div className="journalKpis">
          <span><small>Gefiltert</small>{filteredJournalEntries.length}/{visibleJournalEntries.length}</span>
          <span><small>Echt-Journal</small>{liveJournalEntries.length}</span>
          <span><small>Archiv/Paper</small>{archiveJournalEntries.length}</span>
          <span><small>Ø R Auswahl</small>{display(filteredJournalMetrics.avgR)}</span>
          <span><small>Regelquote</small>{display(filteredJournalMetrics.ruleRate, 0)}%</span>
          <span><small>Trefferquote</small>{display(filteredJournalMetrics.winRate, 0)}%</span>
        </div>
        <p className="ruleLine">
          Technische Bewertung bedeutet hier: Abgleich gegen TradingFreaks-Prozessdaten, Dokumentation, Risiko-Flags und Regelvollstaendigkeit. Es ist keine Anlageberatung und keine nachtraegliche Trade-Empfehlung.
        </p>
      </section>

      <section className="proBoardGrid tradeOverview">
        <section className="panel proBoardPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Auswertung</h2>
              <p>Gefilterte Historie als Management-Blick.</p>
            </div>
            <button type="button" className="ghostButton" onClick={exportDailyPlan}>Export</button>
          </div>
          <div className="decisionFactGrid">
            <span><small>Trades</small>{filteredJournalEntries.length}</span>
            <span><small>Ø R</small>{display(filteredJournalMetrics.avgR)}</span>
            <span><small>Treffer</small>{display(filteredJournalMetrics.winRate, 0)}%</span>
            <span><small>Regelquote</small>{display(filteredJournalMetrics.ruleRate, 0)}%</span>
          </div>
          <div className="chartRows">
            <span><small>Trefferquote</small><i><b style={{ width: `${Math.max(0, Math.min(100, filteredJournalMetrics.winRate))}%` }} /></i></span>
            <span><small>Regelquote</small><i><b style={{ width: `${Math.max(0, Math.min(100, filteredJournalMetrics.ruleRate))}%` }} /></i></span>
          </div>
        </section>

        <section className="panel proBoardPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Review-Risiko</h2>
              <p>Was vor dem Echtgeldkonto sauber sein muss.</p>
            </div>
          </div>
          <div className="decisionFactGrid">
            <span><small>Aktiv offen</small>{reviewInsights.openReviews}</span>
            <span><small>Ohne R</small>{reviewInsights.noRealizedR}</span>
            <span><small>Ohne Bilder</small>{reviewInsights.noScreenshots}</span>
            <span><small>Blocker</small>{journalMetrics.blockers}</span>
          </div>
        </section>
      </section>

      {renderJournalMaintenancePanel()}

      <details className="proDetails tradeDetails">
        <summary>
          <strong>Trade-Liste und Filter anzeigen</strong>
          <span>Wochen, Monate, Quartale, Jahre und Assetklassen auswerten</span>
        </summary>
      <section className="panel tradeTablePanel">
        <div className="panelHeader tight">
          <div>
            <h2>Alle Trades</h2>
            <p>Sortiert nach letztem Import-/Exit-Zeitpunkt. Filterbar nach Woche, Monat, Quartal, Jahr und Assetklasse.</p>
          </div>
        </div>
        <div className="tradeFilters">
          <Field label="Datenbereich" compact>
            <select
              value={tradeFilters.mode}
              onChange={(event) => setTradeFilters({ ...tradeFilters, mode: event.target.value, periodValue: '' })}
            >
              <option value="live">Echt/Live Journal</option>
              <option value="paper">Paper/Test</option>
              <option value="import">Import/Archiv</option>
              <option value="all">Alle Daten</option>
            </select>
          </Field>
          <Field label="Zeitraum" compact>
            <select
              value={tradeFilters.periodType}
              onChange={(event) => setTradeFilters({ ...tradeFilters, periodType: event.target.value, periodValue: '' })}
            >
              <option value="all">Alle</option>
              <option value="week">Woche</option>
              <option value="month">Monat</option>
              <option value="quarter">Quartal</option>
              <option value="year">Jahr</option>
            </select>
          </Field>
          <Field label="Periode" compact>
            <select
              value={tradeFilters.periodValue}
              disabled={tradeFilters.periodType === 'all'}
              onChange={(event) => setTradeFilters({ ...tradeFilters, periodValue: event.target.value })}
            >
              <option value="">Alle Perioden</option>
              {tradePeriodOptions.map((option) => (
                <option value={option} key={option}>{periodLabel(option, tradeFilters.periodType)}</option>
              ))}
            </select>
          </Field>
          <Field label="Assetklasse" compact>
            <select value={tradeFilters.market} onChange={(event) => setTradeFilters({ ...tradeFilters, market: event.target.value })}>
              <option value="all">Alle Assetklassen</option>
              <option value="us_stock">US-Aktien</option>
              <option value="index">Indizes</option>
              <option value="forex">FX</option>
              <option value="commodity">Rohstoffe</option>
              <option value="crypto">Krypto-CFD</option>
            </select>
          </Field>
          <button type="button" className="ghostButton" onClick={() => setTradeFilters(defaultTradeFilters)}>
            Echtgeld-Filter
          </button>
        </div>
        <div className="tradeTable" role="table" aria-label="Alle Trade Eintraege">
          <div className="tradeHeaderRow" role="row">
            <span>Datum</span>
            <span>Zeit</span>
            <span>Symbol</span>
            <span>Assetklasse</span>
            <span>Setup</span>
            <span>Richtung</span>
            <span>Ergebnis</span>
            <span>Bewertung</span>
            <span>Naechste Nacharbeit</span>
          </div>
          {filteredJournalEntries.length === 0 && <span className="emptyState">{tradeModeEmptyText(tradeFilters.mode)}</span>}
          {filteredJournalEntries.map((entry) => {
            const rating = technicalTradeRating(entry);
            return (
              <article className="tradeRow" role="row" key={entry.draft_id}>
                <span>{entry.date || '--'}</span>
                <span>{entry.planned_time || '--'}</span>
                <span className="assetCell">
                  <strong>{entry.symbol || 'UNDEFINED'}</strong>
                  <small>{tradeAccountModeLabel(tradeAccountMode(entry))} | {entry.source || 'Tagesprozess'}</small>
                </span>
                <span>{marketLabel(entry.market || marketFromImportedSymbol(entry.symbol))}</span>
                <span>{entry.setup || '--'}</span>
                <span>{directionLabel(entry.direction)}</span>
                <span><mark className={`statusMark ${resultClass(entry)}`}>{resultLabel(entry)}</mark></span>
                <span><mark className={`statusMark ${rating.className}`}>{rating.label}</mark></span>
                <span className="blockerCell">{rating.reason}</span>
              </article>
            );
          })}
        </div>
      </section>
      </details>
    </section>
  );

  const renderReview = () => (
    <section className="reviewWorkspace">
      <section className="reviewCommandCenter">
        <article className="reviewAlert danger">
          <small>Offene Nacharbeit</small>
          <strong>{reviewInsights.openReviews}</strong>
          <span>Nur laufende und manuell bearbeitbare Journalfaelle zaehlen hier. Brokerimporte bleiben im Trade-Archiv.</span>
        </article>
        <article className="reviewAlert watch">
          <small>Netto Testhistorie</small>
          <strong>{display(reviewInsights.totalMoney, 0)}</strong>
          <span>{reviewInsights.moneySample} Eintraege mit Geld-Ergebnis; reine Prozessinformation.</span>
        </article>
        <article className="reviewAlert">
          <small>Trefferquote Geld</small>
          <strong>{display(reviewInsights.winRateCash, 0)}%</strong>
          <span>{reviewInsights.winners} Gewinner, {reviewInsights.losers} Verlierer.</span>
        </article>
        <article className="reviewAlert danger">
          <small>Dokumentationsluecken</small>
          <strong>{reviewInsights.noScreenshots}</strong>
          <span>Eintraege ohne vollstaendige Vorher-/Nachher-Screenshots.</span>
        </article>
      </section>

      <section className="panel proReviewDashboard">
        <div className="panelHeader tight">
          <div>
            <h2>Review Cockpit</h2>
            <p>Prozessrisiken, Muster und offene Nacharbeit.</p>
          </div>
          <button type="button" className="secondaryButton" onClick={exportDailyPlan}>Export</button>
        </div>
        <div className="proReviewGrid">
          <article>
            <small>Nacharbeit</small>
            <strong>{reviewInsights.openReviews}</strong>
            <div className="singleBar dangerBar">
              <i style={{ width: percentWidth(reviewInsights.openReviews, Math.max(1, reviewInsights.openReviews + reviewInsights.completedReviews)) }} />
            </div>
          </article>
          <article>
            <small>Trefferquote Geld</small>
            <strong>{display(reviewInsights.winRateCash, 0)}%</strong>
            <div className="singleBar">
              <i style={{ width: `${Math.max(0, Math.min(100, reviewInsights.winRateCash))}%` }} />
            </div>
          </article>
          <article>
            <small>Dokuluecken</small>
            <strong>{reviewInsights.noScreenshots}</strong>
            <div className="singleBar dangerBar">
              <i style={{ width: percentWidth(reviewInsights.noScreenshots, Math.max(1, journalMetrics.count)) }} />
            </div>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Wochenreview</h2>
            <p>Prozessqualitaet, nicht Performanceversprechen</p>
          </div>
          <button type="button" className="secondaryButton" onClick={exportDailyPlan}>Exportieren</button>
        </div>
        <div className="reviewGrid">
          <article>
            <small>Journal-Eintraege</small>
            <strong>{journalMetrics.count}</strong>
            <span>Aktives Echtgeld-Journal ohne Paper-/Import-Archiv</span>
          </article>
          <article>
            <small>Durchschnitt R</small>
            <strong>{display(journalMetrics.avgR)}</strong>
            <span>Nur ausgefuellte R-Werte</span>
          </article>
          <article>
            <small>Regelkonform</small>
            <strong>{display(journalMetrics.ruleRate, 0)}%</strong>
            <span>{journalMetrics.knownCompliance} Eintraege mit bekanntem Regelstatus</span>
          </article>
          <article>
            <small>Offene Blocker</small>
            <strong>{journalMetrics.blockers}</strong>
            <span>Haeufigste Nicht-handeln-Gruende pruefen</span>
          </article>
        </div>
      </section>

      <section className="panel reviewWorklistPanel">
        <div className="panelHeader tight">
          <div>
            <h2>Review-Arbeitsliste</h2>
            <p>Direkt bearbeitbare offene Punkte. Importierte Brokertrades erst ins Journal uebernehmen, dann Setup, Bilder, R und Regelcheck ergaenzen.</p>
          </div>
          <button type="button" className="ghostButton" onClick={() => setActiveView('journal')}>Zum Journal</button>
        </div>
        <div className="reviewWorklist">
          {reviewQueueEntries.slice(0, 8).map((draft) => {
            const rating = technicalTradeRating(draft);
            return (
              <article key={draft.draft_id}>
                <div>
                  <strong>{draft.symbol}</strong>
                  <span>{draft.date} | {draft.setup} | {directionLabel(draft.direction)}</span>
                </div>
                <mark className={`statusMark ${rating.className}`}>{rating.label}</mark>
                <small>{rating.reason}</small>
                <button type="button" className="ghostButton" onClick={() => loadJournalDraft(draft)}>
                  Bearbeiten
                </button>
              </article>
            );
          })}
          {reviewQueueEntries.length === 0 && <span className="emptyState">Keine aktive Review-Nacharbeit geladen</span>}
        </div>
      </section>

      <details className="proDetails reviewDetails">
        <summary>
          <strong>Review-Details anzeigen</strong>
          <span>Schwache Symbole, haeufige Blocker und Kostenmodell</span>
        </summary>
      <section className="reviewSplit">
        <section className="panel reviewListPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Schwaechste Symbole</h2>
              <p>Review-Prioritaet nach Netto-Ergebnis</p>
            </div>
          </div>
          <div className="reviewRows">
            {reviewInsights.weakestSymbols.length === 0 && <span className="emptyState">Keine Geld-Ergebnisse geladen</span>}
            {reviewInsights.weakestSymbols.map((item) => (
              <article key={item.symbol}>
                <strong>{item.symbol}</strong>
                <span>{item.trades} Trades</span>
                <mark>{display(item.net, 0)}</mark>
              </article>
            ))}
          </div>
        </section>

        <section className="panel reviewListPanel">
          <div className="panelHeader tight">
            <div>
              <h2>Haeufigste Blocker</h2>
              <p>Was vor dem naechsten Live-Einsatz geschlossen werden muss</p>
            </div>
          </div>
          <div className="reviewRows blockerRows">
            {reviewInsights.topBlockers.length === 0 && <span className="emptyState">Keine Blocker geladen</span>}
            {reviewInsights.topBlockers.map((item) => (
              <article key={item.name}>
                <strong>{item.name}</strong>
                <span>{item.count}x</span>
              </article>
            ))}
          </div>
        </section>
      </section>

      <section className="reviewSplit">
        <section className="panel">
          <h2>Backtest Kostenmodell</h2>
          <div className="twoGrid">
            <Field label="spread_per_unit">
              <input {...inputProps(backtestCosts.spread_per_unit, (value) => setBacktestCosts((current) => ({ ...current, spread_per_unit: value })))} />
            </Field>
            <Field label="slippage_per_unit">
              <input {...inputProps(backtestCosts.slippage_per_unit, (value) => setBacktestCosts((current) => ({ ...current, slippage_per_unit: value })))} />
            </Field>
          </div>
        </section>
        <section className="panel">
          <h2>Naechste Prozessfokus</h2>
          <div className="focusRules">
            <span>Kein Trade ohne Stop Loss.</span>
            <span>Mindest-CRV 1:1 bleibt Pflicht.</span>
            <span>Nach 3 Verlusten Psychologie-Check.</span>
            <span>US Open 15:30-15:35 bleibt No Trade.</span>
            <span>XAGUSD immer mit Gold, USD/Yields und China-Kontext pruefen.</span>
          </div>
        </section>
      </section>
      </details>
    </section>
  );

  const renderHelp = () => (
    <section className="helpWorkspace">
      <section className="panel helpIntro">
        <div className="panelHeader">
          <div>
            <h2>Bedienungsanleitung</h2>
            <p>Die App ist als taeglicher Trading-Prozess aufgebaut: vorbereiten, pruefen, dokumentieren, reviewen.</p>
          </div>
        </div>
        <div className="helpGrid">
          <article>
            <strong>1. Focus Desk</strong>
            <span>Hier bereitest Du den Tag vor: Watchlist, aktives Setup, Richtung, Entry, Stop, Ziel, Risiko und 5 Pre-Checks. Ergebnis ist nur `Manuelle Pruefung`, `Nur beobachten` oder `Blockiert`.</span>
          </article>
          <article>
            <strong>2. Journal</strong>
            <span>Hier dokumentierst Du einen konkreten Trade: Emotion, Vorher-Bild, Ergebnis, Nachher-Bild, Regelcheck und Review. Das ist der Tagesabschluss pro Trade.</span>
          </article>
          <article>
            <strong>3. Trades</strong>
            <span>Hier findest Du die Uebersicht aller geladenen Trades. Die technische Bewertung zeigt, ob Setup-/Risikodaten fehlen, ob Risiko auffaellig war oder ob der Trade ausreichend dokumentiert ist.</span>
          </article>
          <article>
            <strong>4. Review</strong>
            <span>Hier findest Du Muster: offene Nacharbeit, schwache Symbole, haeufige Blocker, Dokumentationsluecken und Prozesskennzahlen. Das ist fuer Wochenreview und Verbesserungen gedacht.</span>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader tight">
          <div>
            <h2>Wichtig zur technischen Bewertung</h2>
            <p>Brokerreports enthalten Ausfuehrungen, aber keine vollstaendige TradingFreaks-Setupqualitaet.</p>
          </div>
        </div>
        <div className="focusRules">
          <span>`Technisch offen`: Chart, Setup-Kriterien, Screenshots, SL/TP/CRV oder Emotionen fehlen.</span>
          <span>`Risiko auffaellig`: Import enthaelt Risiko-/Positionsgroessen-Warnungen, z. B. Verlust groesser als 1% oder Metall-Exposure.</span>
          <span>`Regelabweichung`: Im Journal wurde eine Abweichung vom Plan dokumentiert.</span>
          <span>`Dokumentiert`: Die wesentlichen Journalfelder sind gefuellt. Das ist keine Aussage ueber zukuenftige Performance.</span>
        </div>
      </section>
    </section>
  );

  return (
    <main className="appShell simpleMode">
      <header className="appTop">
        <section className="brandBlock">
          <span>WertBegleiter® Kapitalmarkt</span>
          <h1>{viewLabel(activeView)}</h1>
          <p>{todayLabel()} | Scalping-Fokus | Keine Anlageberatung, keine Orderfreigabe</p>
        </section>

        <nav className="viewTabs" aria-label="Arbeitsbereich">
          {['guide', 'desk', 'updates', 'journal', 'trades', 'review', 'help'].map((view) => (
            <button
              type="button"
              className={activeView === view ? 'active' : ''}
              key={view}
              onClick={() => setActiveView(view)}
            >
              {viewLabel(view)}
            </button>
          ))}
        </nav>

        <section className={`dayStatus ${statusClass(dayStatus)}`}>
          <small>Tagesstatus</small>
          <strong>{statusLabel(dayStatus)}</strong>
          <span>{manualCount} pruefen | {watchCount} beobachten | {blockedCount} blockiert | Slots {slotsRemaining}/{context.max_trades_per_day}</span>
        </section>
      </header>

      <section className="workspace">
        {renderCommandRail()}
        {activeView === 'guide' && renderGuide()}
        {activeView === 'desk' && renderDesk()}
        {activeView === 'updates' && renderUpdates()}
        {activeView === 'journal' && renderJournal()}
        {activeView === 'trades' && renderTrades()}
        {activeView === 'review' && renderReview()}
        {activeView === 'help' && renderHelp()}
      </section>
    </main>
  );
}
