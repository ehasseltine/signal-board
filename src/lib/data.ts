import fs from 'node:fs';
import path from 'node:path';

// Data lives in public/data/daily/ at build time.
// Astro copies public/ into the output directory (docs/).
export function loadLatestData() {
  const dataPath = path.join(process.cwd(), 'public', 'data', 'daily', 'latest.json');
  const raw = fs.readFileSync(dataPath, 'utf-8');
  return JSON.parse(raw);
}

export function loadDailyData(date: string) {
  const dataPath = path.join(process.cwd(), 'public', 'data', 'daily', `${date}.json`);
  if (!fs.existsSync(dataPath)) return null;
  const raw = fs.readFileSync(dataPath, 'utf-8');
  return JSON.parse(raw);
}

export function listDailyDates(): string[] {
  const dir = path.join(process.cwd(), 'public', 'data', 'daily');
  return fs.readdirSync(dir)
    .filter(f => /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
    .map(f => f.replace('.json', ''))
    .sort()
    .reverse();
}
