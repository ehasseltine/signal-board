// Story selection logic mapped to ACTUAL pipeline data structure
// Pipeline outputs: top_stories, what_connects, cooperation,
// narrative_divergence, local_regional_exclusive

interface WhatConnects {
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

interface NarrativeDivergence {
  topic: string;
  theme: string;
  source_count: number;
  structural_force: string;
  articles: Array<{
    source: string;
    title: string;
    url?: string;
    tier?: string;
    framing?: string;
  }>;
}

interface CooperationHighlight {
  title: string;
  source: string;
  url?: string;
  type?: string;
}

interface Cooperation {
  total_cooperation_stories: number;
  cooperation_rate: number;
  by_type?: Record<string, number>;
  by_force?: Record<string, number>;
  highlights: CooperationHighlight[];
  coverage_gap: Array<{ force: string; article_count: number; note: string }>;
}

interface TopStory {
  headline: string;
  structural_force: string;
  all_forces?: string[];
  source_count: number;
  tier_count: number;
  tiers: string[];
  domains: string[];
  article_count: number;
  connections: Array<{ text: string }>;
  tier_framing?: Record<string, any>;
  articles: Array<{
    source: string;
    title: string;
    url?: string;
    tier?: string;
  }>;
}

interface LocalRegionalExclusive {
  title: string;
  source: string;
  url?: string;
  tier: string;
  text_preview: string;
  domains: string[];
  connection: string;
  force_tag: string;
  context: string;
}

// What we return for each section (normalized for the template)
export interface SectionStory {
  title: string;
  narrative: string;
  key_developments: string[];
  sources: Record<string, { tier?: string; url?: string; headline?: string }>;
  sourceCount: number;
  spectrumSegments?: number;
}

/**
 * THE DAILY THREAD — Cross-spectrum convergence
 * Uses `what_connects`: stories covered by left, right, international, local sources
 * Picks the one with widest spectrum coverage
 */
export function selectDailyThread(whatConnects: WhatConnects[]): SectionStory | null {
  if (!whatConnects || whatConnects.length === 0) return null;

  // Sort by spectrum_segments (widest coverage) then total_sources
  const sorted = [...whatConnects].sort((a, b) => {
    const segDiff = (b.spectrum_segments || 0) - (a.spectrum_segments || 0);
    if (segDiff !== 0) return segDiff;
    return (b.total_sources || 0) - (a.total_sources || 0);
  });

  const pick = sorted[0];

  // Build sources map from spectrum lists
  const sources: Record<string, { tier?: string; url?: string; headline?: string }> = {};
  for (const s of (pick.left_sources || [])) sources[s] = { tier: 'left' };
  for (const s of (pick.right_sources || [])) sources[s] = { tier: 'right' };
  for (const s of (pick.international_sources || [])) sources[s] = { tier: 'international' };
  for (const s of (pick.local_regional_sources || [])) sources[s] = { tier: 'local-regional' };

  return {
    title: pick.headline,
    narrative: pick.sample_connection || '',
    key_developments: pick.domains
      ? [`Covered across ${pick.domains.join(', ')} domains by ${pick.total_sources} sources spanning ${pick.spectrum_segments} points on the political spectrum.`]
      : [],
    sources,
    sourceCount: pick.total_sources,
    spectrumSegments: pick.spectrum_segments,
  };
}

/**
 * THE DAILY GAP — Framing differences
 * Uses `narrative_divergence`: where outlets tell the same story differently
 * Picks the topic with the most sources (most contested framing)
 */
export function selectDailyGap(
  narrativeDivergence: NarrativeDivergence[],
  topStories: TopStory[]
): SectionStory | null {
  if (narrativeDivergence && narrativeDivergence.length > 0) {
    const sorted = [...narrativeDivergence].sort(
      (a, b) => (b.source_count || 0) - (a.source_count || 0)
    );
    const pick = sorted[0];

    const sources: Record<string, any> = {};
    for (const art of (pick.articles || [])) {
      sources[art.source] = { url: art.url, headline: art.title, tier: art.tier };
    }

    return {
      title: pick.theme || pick.topic,
      narrative: `Across ${pick.source_count} sources covering ${pick.topic}, the framing diverges — revealing how the same events get shaped into different stories depending on who's telling them.`,
      key_developments: pick.articles.slice(0, 3).map(
        a => `${a.source}: "${a.title?.substring(0, 120)}"`
      ),
      sources,
      sourceCount: pick.source_count,
    };
  }

  // Fallback: use a top story with multiple tiers showing different framing
  if (topStories && topStories.length > 0) {
    const multiTier = topStories.find(s => s.tier_count >= 2 && s.tier_framing);
    if (multiTier) {
      const sources: Record<string, any> = {};
      for (const art of (multiTier.articles || [])) {
        sources[art.source] = { url: art.url, tier: art.tier };
      }
      return {
        title: multiTier.headline,
        narrative: multiTier.connections?.[0]?.text || '',
        key_developments: Object.entries(multiTier.tier_framing || {}).map(
          ([tier, framing]: [string, any]) =>
            `${tier}: ${typeof framing === 'string' ? framing : JSON.stringify(framing).substring(0, 150)}`
        ),
        sources,
        sourceCount: multiTier.source_count,
      };
    }
  }

  return null;
}

/**
 * MEANWHILE — Who showed up
 * Uses `cooperation`: stories about communities taking action
 * Picks from cooperation highlights
 */
export function selectMeanwhile(
  cooperation: Cooperation,
  localRegional: LocalRegionalExclusive[]
): SectionStory | null {
  if (cooperation && cooperation.highlights && cooperation.highlights.length > 0) {
    const highlights = cooperation.highlights;

    const sources: Record<string, any> = {};
    for (const h of highlights.slice(0, 6)) {
      sources[h.source] = { url: h.url, headline: h.title };
    }

    return {
      title: 'Communities Taking Action',
      narrative: `Today, ${cooperation.total_cooperation_stories} stories showed people cooperating — a ${cooperation.cooperation_rate}% cooperation signal across everything we read. Here's who showed up.`,
      key_developments: highlights.slice(0, 4).map(h => h.title),
      sources,
      sourceCount: highlights.length,
    };
  }

  // Fallback: use local/regional exclusives about community action
  if (localRegional && localRegional.length > 0) {
    const communityKeywords = ['community', 'volunteer', 'mutual aid', 'neighbors', 'organize', 'solidarity', 'support'];
    const communityStories = localRegional.filter(lr =>
      communityKeywords.some(kw =>
        lr.title.toLowerCase().includes(kw) ||
        lr.text_preview.toLowerCase().includes(kw)
      )
    );
    const picks = communityStories.length > 0 ? communityStories : localRegional.slice(0, 4);

    const sources: Record<string, any> = {};
    for (const lr of picks) {
      sources[lr.source] = { url: lr.url, headline: lr.title };
    }

    return {
      title: 'Communities Taking Action',
      narrative: 'Local and independent outlets cover what the national cycle misses — people showing up for each other.',
      key_developments: picks.slice(0, 4).map(lr => `${lr.source}: ${lr.title}`),
      sources,
      sourceCount: picks.length,
    };
  }

  return null;
}
