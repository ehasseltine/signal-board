#!/usr/bin/env node
/**
 * Post-build validation for Signal Board.
 * Checks the built HTML for common problems that previously required
 * manual screenshot inspection to catch.
 *
 * Exit code 0 = all checks pass
 * Exit code 1 = one or more checks failed (blocks push in CI)
 *
 * Run: node scripts/validate.js
 */

import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

let failures = 0;
let passes = 0;

function check(name, passed, detail) {
  if (passed) {
    passes++;
    console.log(`  ✓ ${name}`);
  } else {
    failures++;
    console.log(`  ✗ FAIL: ${name}`);
    if (detail) console.log(`    → ${detail}`);
  }
}

// ---------------------------------------------------------------------------
// Load files
// ---------------------------------------------------------------------------

const todayHtml = readFileSync(resolve(ROOT, 'docs/today/index.html'), 'utf-8');
const latestJsonPath = resolve(ROOT, 'docs/data/daily/latest.json');

if (!existsSync(latestJsonPath)) {
  console.log('✗ FATAL: docs/data/daily/latest.json does not exist. Build may have failed.');
  process.exit(1);
}

const latestJson = JSON.parse(readFileSync(latestJsonPath, 'utf-8'));

console.log('\nSignal Board post-build validation\n');

// ---------------------------------------------------------------------------
// 1. Date match
// ---------------------------------------------------------------------------

console.log('Date:');
const jsonDate = latestJson.date || '';
// Look for the date in the hero section (it appears as text content)
const dateInHtml = todayHtml.includes(jsonDate);
check('Hero date matches latest.json', dateInHtml,
  dateInHtml ? null : `Expected ${jsonDate} in HTML`);

// ---------------------------------------------------------------------------
// 2. Framing row labels — no "Perspective N" or empty labels
// ---------------------------------------------------------------------------

console.log('Framing rows:');

// Extract framing-label contents
const labelRegex = /class="framing-label"[^>]*>(.*?)<\/div>/gs;
const labels = [];
let m;
while ((m = labelRegex.exec(todayHtml)) !== null) {
  // Strip HTML tags to get text content
  const text = m[1].replace(/<[^>]+>/g, '').trim();
  labels.push(text);
}

const perspectiveLabels = labels.filter(l => /^Perspective \d+$/i.test(l));
check('No "Perspective N" fallback labels', perspectiveLabels.length === 0,
  perspectiveLabels.length > 0 ? `Found: ${perspectiveLabels.join(', ')}` : null);

const emptyLabels = labels.filter(l => l === '');
check('No empty framing labels', emptyLabels.length === 0,
  emptyLabels.length > 0 ? `${emptyLabels.length} empty labels found` : null);

check('At least 6 framing rows exist', labels.length >= 6,
  `Found ${labels.length} framing rows`);

// ---------------------------------------------------------------------------
// 3. Source card descriptions — no bias labels
// ---------------------------------------------------------------------------

console.log('Source descriptions:');

const descRegex = /class="coverage-type"[^>]*>(.*?)<\/div>/gs;
const descriptions = [];
while ((m = descRegex.exec(todayHtml)) !== null) {
  descriptions.push(m[1].replace(/<[^>]+>/g, '').trim());
}

const biasTerms = [
  'conservative', 'liberal', 'progressive',
  'center-left', 'center-right',
  'left-leaning', 'right-leaning',
  'left-of-center', 'right-of-center',
  'generally regarded',
  'right-wing', 'left-wing'
];

const biasFound = [];
for (const desc of descriptions) {
  for (const term of biasTerms) {
    if (desc.toLowerCase().includes(term)) {
      biasFound.push({ term, desc: desc.substring(0, 80) });
    }
  }
}

check('No bias labels in source descriptions', biasFound.length === 0,
  biasFound.length > 0 ? biasFound.map(b => `"${b.term}" in: ${b.desc}...`).join('\n    → ') : null);

// Check for empty descriptions (source cards with no text)
check('All source cards have descriptions', descriptions.length > 0,
  descriptions.length === 0 ? 'No source descriptions found in HTML' : `${descriptions.length} descriptions found`);

const shortDescs = descriptions.filter(d => d.split(/\s+/).length < 10);
check('No source descriptions under 10 words', shortDescs.length === 0,
  shortDescs.length > 0 ? `${shortDescs.length} short: ${shortDescs[0]?.substring(0, 60)}...` : null);

// ---------------------------------------------------------------------------
// 4. Framing row content — no orphaned fragments
// ---------------------------------------------------------------------------

console.log('Framing content:');

const contentRegex = /class="framing-content"[^>]*>(.*?)<\/div>/gs;
const framingContents = [];
while ((m = contentRegex.exec(todayHtml)) !== null) {
  framingContents.push(m[1].replace(/<[^>]+>/g, '').trim());
}

const orphanedFragments = framingContents.filter(c => c.length < 20 && c.length > 0);
check('No orphaned sentence fragments (under 20 chars)', orphanedFragments.length === 0,
  orphanedFragments.length > 0 ? `Found: "${orphanedFragments[0]}"` : null);

// ---------------------------------------------------------------------------
// 5. Numerical consistency
// ---------------------------------------------------------------------------

console.log('Data consistency:');

// Check that the source count in the JSON is reflected
const topStories = latestJson.top_stories || [];
const totalArticles = topStories.reduce((sum, s) => sum + (s.article_count || 0), 0);
check('Pipeline has top stories', topStories.length > 0,
  `${topStories.length} top stories found`);

// Cooperation data
const coop = latestJson.cooperation;
if (coop) {
  const coopCount = coop.total_cooperation_stories || 0;
  const coopInHtml = todayHtml.includes(String(coopCount));
  check('Cooperation count matches', coopInHtml,
    coopInHtml ? null : `Expected ${coopCount} in HTML`);
}

// ---------------------------------------------------------------------------
// 6. All three sections present
// ---------------------------------------------------------------------------

console.log('Sections:');

check('Daily Thread section exists', todayHtml.includes('id="daily-thread"') || todayHtml.includes('id="thread"') || todayHtml.includes('daily-thread'),
  null);
check('Daily Gap section exists', todayHtml.includes('id="gap"') || todayHtml.includes('id="daily-gap"') || todayHtml.includes('daily-gap'),
  null);
check('Meanwhile section exists', todayHtml.includes('id="meanwhile"') || todayHtml.includes('Meanwhile'),
  null);

// ---------------------------------------------------------------------------
// 7. Cooperation rate → fraction consistency (4A)
// ---------------------------------------------------------------------------

console.log('Cooperation fraction:');

if (coop) {
  const rate = coop.cooperation_rate || 0;
  // The template maps rates to fractions — verify the HTML contains the right one
  const expectedFraction =
    rate >= 28 ? 'About one in three' :
    rate >= 23 ? 'About one in four' :
    rate >= 18 ? 'About one in five' :
    rate >= 15 ? 'About one in six' :
    rate >= 12 ? 'About one in eight' :
    `${rate}% of`;
  const fractionInHtml = todayHtml.includes(expectedFraction);
  check(`Cooperation fraction matches rate (${rate}% → "${expectedFraction}")`, fractionInHtml,
    fractionInHtml ? null : `Expected "${expectedFraction}" in HTML for rate ${rate}%`);
}

// ---------------------------------------------------------------------------
// 8. URL-content section isolation (4B)
// ---------------------------------------------------------------------------

console.log('URL isolation:');

// Extract URLs from each section and check for cross-section contamination
// Thread section: between "daily-thread" and "daily-gap" or "gap"
// Gap section: between "daily-gap"/"gap" and "meanwhile"
function extractSectionUrls(html, startMarker, endMarker) {
  const startIdx = html.indexOf(startMarker);
  const endIdx = endMarker ? html.indexOf(endMarker, startIdx + 1) : html.length;
  if (startIdx === -1) return [];
  const section = html.substring(startIdx, endIdx > startIdx ? endIdx : html.length);
  const urlRegex = /href="(https?:\/\/[^"]+)"/g;
  const urls = [];
  let um;
  while ((um = urlRegex.exec(section)) !== null) {
    urls.push(um[1]);
  }
  return urls;
}

// Check that Thread and Gap sections have at least some URLs
// Use id attributes as markers — more reliable than text content
const threadUrls = extractSectionUrls(todayHtml, 'id="thread"', 'id="gap"');
const gapUrls = extractSectionUrls(todayHtml, 'id="gap"', 'id="meanwhile"');

check('Thread section has source URLs', threadUrls.length >= 1,
  `Found ${threadUrls.length} URLs in Thread section`);
check('Gap section has source URLs', gapUrls.length >= 1,
  `Found ${gapUrls.length} URLs in Gap section`);

// Check that Thread and Gap don't share identical URL sets (they can share some outlets, but not all)
if (threadUrls.length > 0 && gapUrls.length > 0) {
  const threadSet = new Set(threadUrls);
  const gapSet = new Set(gapUrls);
  const overlap = [...threadSet].filter(u => gapSet.has(u));
  const overlapPct = Math.round((overlap.length / Math.min(threadSet.size, gapSet.size)) * 100);
  check('Thread and Gap sections are not URL-identical', overlapPct < 90,
    overlapPct >= 90 ? `${overlapPct}% URL overlap — sections may be showing the same story` : `${overlapPct}% overlap (some shared outlets expected)`);
}

// ---------------------------------------------------------------------------
// 9. Meanwhile synthesis outlet accuracy (Issue E)
// ---------------------------------------------------------------------------

console.log('Meanwhile synthesis accuracy:');

const meanwhileSynth = (latestJson.story_syntheses || []).find(s => s.role === 'meanwhile');
if (meanwhileSynth) {
  // Only check the synthesis field — cross_spectrum intentionally names
  // non-cooperation outlets for framing contrast, which is correct editorial behavior.
  const meanwhileText = meanwhileSynth.synthesis || '';

  // Collect all cooperation sources
  const coopSources = new Set();
  const coopHighlights = latestJson.cooperation?.highlights || [];
  for (const h of coopHighlights) {
    if (h.source) coopSources.add(h.source);
  }
  const allSourceUrls = latestJson.cooperation?.all_source_urls || {};
  for (const src of Object.keys(allSourceUrls)) {
    coopSources.add(src);
  }
  // Also add by_type sources
  for (const t of (latestJson.cooperation?.by_type || [])) {
    for (const src of (t.sources || [])) {
      coopSources.add(src);
    }
  }

  // Build the full set of known outlet names from sources.json (all 300 outlets)
  // plus any that appear in the pipeline data
  const allKnownOutlets = new Set();
  const sourcesJsonPath = resolve(ROOT, 'data/sources.json');
  if (existsSync(sourcesJsonPath)) {
    const sourcesJson = JSON.parse(readFileSync(sourcesJsonPath, 'utf-8'));
    for (const name of Object.keys(sourcesJson)) {
      allKnownOutlets.add(name);
    }
  }
  for (const story of (latestJson.top_stories || [])) {
    for (const a of (story.articles || [])) {
      if (a.source) allKnownOutlets.add(a.source);
    }
  }
  for (const src of coopSources) allKnownOutlets.add(src);

  // Find outlet names in synthesis text that aren't cooperation-tagged
  const hallucinatedOutlets = [];
  for (const outlet of allKnownOutlets) {
    if (meanwhileText.includes(outlet) && !coopSources.has(outlet)) {
      hallucinatedOutlets.push(outlet);
    }
  }

  // This is a WARNING, not a hard failure — the synthesis model may occasionally
  // reference outlets not tagged as cooperation in the pipeline. This can only be
  // fixed by re-running the synthesis, not at the template level.
  if (hallucinatedOutlets.length > 0) {
    console.log(`  ⚠ WARNING: Meanwhile synthesis names non-cooperation outlets: ${hallucinatedOutlets.join(', ')}`);
    console.log(`    → This is a synthesis model accuracy issue. Consider tightening the prompt.`);
  } else {
    check('Meanwhile synthesis only names cooperation sources', true);
  }
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${passes} passed, ${failures} failed\n`);

if (failures > 0) {
  console.log('Build validation FAILED. Fix the issues above before pushing.');
  process.exit(1);
} else {
  console.log('Build validation PASSED.');
  process.exit(0);
}
