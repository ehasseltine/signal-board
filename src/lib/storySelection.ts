/**
 * Story selection logic for Signal Board
 *
 * Supports TWO data formats:
 * - Legacy (2026-03-28): mega_stories with synthesis, cross_spectrum, why_this_matters, watch_for
 * - Current (2026-03-29+): top_stories, what_connects, cooperation, narrative_divergence, editorial
 *
 * The current pipeline (ingest → analyze → synthesize) produces:
 *   editorial: headline, subheadline, synthesis, cooperation_highlight, coverage_gap_note, thread_to_watch
 *   cooperation: total_cooperation_stories, cooperation_rate, highlights[], coverage_gap[]
 *   what_connects: cross-spectrum stories with left/right/intl/local sources
 *   narrative_divergence: framing gaps between outlets
 *   top_stories: tier_framing, connections[], articles[]
 */

// ── INTERFACES ──

export interface MegaStory {
  name: string;
  article_count: number;
  source_count: number;
  sources_sample: string[];
  domains: string[];
  domain_counts: Record<string, number>;
  patterns: Array<{ name: string; count: number }>;
  insights: string[];
  source_tiers: Record<string, number>;
  yesterday_count: number;
  change_description: string;
  synthesis: string;
  watch_for: string;
  cross_spectrum: string;
  why_this_matters: string;
}

export interface WhatConnects {
  headline: string;
  structural_force: string;
  total_sources: number;
  spectrum_segments: number;
  left_sources: string[];
  right_sources: string[];
  international_sources: string[];
  local_regional_sources: string[];
  article_count: number;
  domains: string[];
  sample_connection: string;
}

export interface TopStory {
  headline: string;
  structural_force: string;
  source_count: number;
  tier_count: number;
  tiers: string[];
  domains: string[];
  article_count: number;
  connections: Array<{ text: string; source?: string; title?: string }>;
  tier_framing?: Record<string, any>;
  articles: Array<{ source: string; title: string; url?: string; tier?: string }>;
}

export interface NarrativeDivergence {
  topic: string;
  theme: string;
  source_count: number;
  structural_force: string;
  articles: Array<{ source: string; title: string; url?: string; tier?: string; framing?: string }>;
}

export interface Cooperation {
  total_cooperation_stories: number;
  cooperation_rate: number;
  by_type?: Array<{ type: string; count: number; sources: string[] }>;
  highlights: Array<{ title: string; source: string; url?: string; type?: string }>;
  coverage_gap: Array<{ force: string; article_count: number; note: string }>;
}

export interface Editorial {
  headline: string;
  subheadline: string;
  synthesis: string;
  cooperation_highlight: string;
  coverage_gap_note: string;
  thread_to_watch: string;
}

// ── OUTPUT ──

export interface SectionStory {
  title: string;
  synthesis: string;
  crossSpectrum: string;
  whyThisMatters: string;
  watchFor: string;
  articleCount: number;
  sourceCount: number;
  sourcesSample: string[];
  domains: string[];
  domainCounts: Record<string, number>;
  sourceTiers: Record<string, number>;
  changeDescription: string;
  insights: string[];
  yesterdayCount: number;
}

// ── CONVERTERS ──

function megaToSection(story: MegaStory): SectionStory {
  return {
    title: story.name || 'Untitled',
    synthesis: story.synthesis || '',
    crossSpectrum: story.cross_spectrum || '',
    whyThisMatters: story.why_this_matters || '',
    watchFor: story.watch_for || '',
    articleCount: story.article_count || 0,
    sourceCount: story.source_count || 0,
    sourcesSample: story.sources_sample || [],
    domains: story.domains || [],
    domainCounts: story.domain_counts || {},
    sourceTiers: story.source_tiers || {},
    changeDescription: story.change_description || '',
    insights: story.insights || [],
    yesterdayCount: story.yesterday_count || 0,
  };
}

function whatConnectsToSection(
  wc: WhatConnects,
  topStory?: TopStory,
  editorial?: Editorial
): SectionStory {
  // Build sources list from spectrum
  const allSources = [
    ...(wc.left_sources || []),
    ...(wc.right_sources || []),
    ...(wc.international_sources || []),
    ...(wc.local_regional_sources || []),
  ];

  // Build cross-spectrum description
  const specParts: string[] = [];
  if (wc.left_sources?.length) specParts.push(`Left-leaning: ${wc.left_sources.join(', ')}`);
  if (wc.right_sources?.length) specParts.push(`Right-leaning: ${wc.right_sources.join(', ')}`);
  if (wc.international_sources?.length) specParts.push(`International: ${wc.international_sources.join(', ')}`);
  if (wc.local_regional_sources?.length) specParts.push(`Local & Regional: ${wc.local_regional_sources.join(', ')}`);

  // Use editorial synthesis if available, fall back to connection text
  const synthesis = editorial?.synthesis
    || topStory?.connections?.[0]?.text
    || wc.sample_connection
    || '';

  // Build tier framing from top story if available
  const tierFraming: string[] = [];
  if (topStory?.tier_framing) {
    for (const [tier, data] of Object.entries(topStory.tier_framing)) {
      if (data?.sample?.title) {
        tierFraming.push(`${tier}: "${data.sample.title}"`);
      }
    }
  }

  return {
    title: wc.headline,
    synthesis,
    crossSpectrum: specParts.join('. ') + '.',
    whyThisMatters: '',
    watchFor: editorial?.thread_to_watch || '',
    articleCount: wc.article_count || 0,
    sourceCount: wc.total_sources || 0,
    sourcesSample: allSources.slice(0, 12),
    domains: wc.domains || [],
    domainCounts: {},
    sourceTiers: {},
    changeDescription: '',
    insights: tierFraming,
    yesterdayCount: 0,
  };
}

// ── SELECTION FUNCTIONS ──

/**
 * THE DAILY THREAD — Widest coverage story
 */
export function selectDailyThread(
  megaStories: MegaStory[],
  whatConnects: WhatConnects[],
  topStories: TopStory[],
  editorial?: Editorial
): SectionStory | null {
  // Legacy format: use mega_stories
  if (megaStories && megaStories.length > 0) {
    const scored = megaStories.map(story => {
      const tierCount = Object.keys(story.source_tiers || {}).length;
      return { story, score: (tierCount * 1000) + (story.article_count || 0) };
    });
    scored.sort((a, b) => b.score - a.score);
    return megaToSection(scored[0].story);
  }

  // Current format: use what_connects + top_stories
  if (whatConnects && whatConnects.length > 0) {
    const sorted = [...whatConnects].sort((a, b) => {
      const segDiff = (b.spectrum_segments || 0) - (a.spectrum_segments || 0);
      if (segDiff !== 0) return segDiff;
      return (b.total_sources || 0) - (a.total_sources || 0);
    });
    const pick = sorted[0];

    // Find matching top story for richer data
    const matchingTop = topStories?.find(ts =>
      ts.structural_force === pick.structural_force ||
      ts.headline?.includes(pick.headline?.substring(0, 30))
    );

    return whatConnectsToSection(pick, matchingTop, editorial);
  }

  return null;
}

/**
 * THE DAILY GAP — Where framing diverges
 */
export function selectDailyGap(
  megaStories: MegaStory[],
  narrativeDivergence: NarrativeDivergence[],
  topStories: TopStory[],
  editorial?: Editorial,
  threadTitle?: string
): SectionStory | null {
  // Legacy: second-best mega story with cross_spectrum
  if (megaStories && megaStories.length > 0) {
    const candidates = megaStories.filter(s => s.name !== threadTitle);
    if (candidates.length > 0) {
      const scored = candidates.map(story => ({
        story,
        score: (story.cross_spectrum || '').length + (story.source_count || 0),
      }));
      scored.sort((a, b) => b.score - a.score);
      return megaToSection(scored[0].story);
    }
  }

  // Current: narrative_divergence
  if (narrativeDivergence && narrativeDivergence.length > 0) {
    const sorted = [...narrativeDivergence].sort(
      (a, b) => (b.source_count || 0) - (a.source_count || 0)
    );
    const pick = sorted[0];

    const sources: string[] = (pick.articles || []).map(a => a.source);
    const uniqueSources = [...new Set(sources)];

    // Build framing insights from articles
    const framings = (pick.articles || [])
      .filter(a => a.framing || a.title)
      .slice(0, 4)
      .map(a => `${a.source}: "${a.title}"`);

    return {
      title: pick.theme || pick.topic,
      synthesis: editorial?.coverage_gap_note
        || `Across ${pick.source_count} sources covering ${pick.topic}, the framing diverges — revealing how the same events get shaped into different stories depending on who's telling them.`,
      crossSpectrum: '',
      whyThisMatters: '',
      watchFor: '',
      articleCount: pick.articles?.length || 0,
      sourceCount: pick.source_count || 0,
      sourcesSample: uniqueSources.slice(0, 8),
      domains: [pick.topic],
      domainCounts: {},
      sourceTiers: {},
      changeDescription: '',
      insights: framings,
      yesterdayCount: 0,
    };
  }

  return null;
}

/**
 * MEANWHILE — Who showed up
 */
export function selectMeanwhile(
  megaStories: MegaStory[],
  cooperation: Cooperation | null,
  localRegionalSynthesis: string,
  localRegionalExamples: any[],
  editorial?: Editorial,
  threadTitle?: string,
  gapTitle?: string
): SectionStory | null {
  // Current format: use cooperation data + editorial cooperation highlight
  if (cooperation && cooperation.highlights && cooperation.highlights.length > 0) {
    const highlights = cooperation.highlights;
    const cooperationNarrative = editorial?.cooperation_highlight
      || `Today, ${cooperation.total_cooperation_stories} stories showed people cooperating — a ${cooperation.cooperation_rate}% cooperation signal across everything we read.`;

    return {
      title: 'Communities Taking Action',
      synthesis: cooperationNarrative,
      crossSpectrum: '',
      whyThisMatters: 'The stories that local and specialist outlets tell are the stories most likely to affect your daily life — and most likely to be missing from the national cycle.',
      watchFor: '',
      articleCount: cooperation.total_cooperation_stories || 0,
      sourceCount: highlights.length,
      sourcesSample: highlights.slice(0, 8).map(h => h.source),
      domains: [],
      domainCounts: {},
      sourceTiers: {},
      changeDescription: `${cooperation.cooperation_rate}% of today's coverage`,
      insights: highlights.slice(0, 5).map(h => `${h.source}: ${h.title}`),
      yesterdayCount: 0,
    };
  }

  // Legacy format: local_regional_synthesis
  if (localRegionalSynthesis && localRegionalSynthesis.length > 50) {
    const exampleTexts = (localRegionalExamples || []).map((ex: any) =>
      typeof ex === 'string' ? ex : (ex.text || JSON.stringify(ex))
    );

    return {
      title: 'Communities Taking Action',
      synthesis: localRegionalSynthesis,
      crossSpectrum: '',
      whyThisMatters: 'The stories that local and specialist outlets tell are the stories most likely to affect your daily life — and most likely to be missing from the national cycle.',
      watchFor: '',
      articleCount: 0,
      sourceCount: 0,
      sourcesSample: [],
      domains: [],
      domainCounts: {},
      sourceTiers: {},
      changeDescription: '',
      insights: exampleTexts,
      yesterdayCount: 0,
    };
  }

  // Last resort: remaining mega story
  if (megaStories && megaStories.length > 0) {
    const remaining = megaStories.filter(s => s.name !== threadTitle && s.name !== gapTitle);
    if (remaining.length > 0) return megaToSection(remaining[0]);
  }

  return null;
}
