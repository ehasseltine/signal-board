// Story selection logic using MEGA_STORIES — the real analysis data
// mega_stories contain: synthesis, cross_spectrum, why_this_matters, watch_for,
// source_tiers, domain_counts, insights, patterns, change_description

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

export interface LocalRegionalExample {
  text?: string;
  // local_regional_examples are typically paragraph strings
  [key: string]: any;
}

// What we return for each section
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

/**
 * THE DAILY THREAD — The biggest story, widest coverage
 * Pick the mega story with the most articles AND broadest source coverage.
 * This is the story that connects across the most sources and perspectives.
 */
export function selectDailyThread(megaStories: MegaStory[]): SectionStory | null {
  if (!megaStories || megaStories.length === 0) return null;

  // Score by: source diversity (number of tiers) * 1000 + article_count
  const scored = megaStories.map(story => {
    const tierCount = Object.keys(story.source_tiers || {}).length;
    const score = (tierCount * 1000) + (story.article_count || 0);
    return { story, score };
  });

  scored.sort((a, b) => b.score - a.score);
  return megaToSection(scored[0].story);
}

/**
 * THE DAILY GAP — Where the framing diverges
 * Pick the mega story where international/independent coverage differs most
 * from mainstream US coverage. Uses cross_spectrum text as signal.
 */
export function selectDailyGap(
  megaStories: MegaStory[],
  threadTitle: string
): SectionStory | null {
  if (!megaStories || megaStories.length === 0) return null;

  // Skip the thread story, find the one with richest cross_spectrum analysis
  const candidates = megaStories.filter(s => s.name !== threadTitle);
  if (candidates.length === 0) return null;

  // Score by: cross_spectrum text length (more text = more framing analysis)
  // + source_count for breadth
  const scored = candidates.map(story => {
    const spectrumLength = (story.cross_spectrum || '').length;
    const score = spectrumLength + (story.source_count || 0);
    return { story, score };
  });

  scored.sort((a, b) => b.score - a.score);
  return megaToSection(scored[0].story);
}

/**
 * MEANWHILE — Who showed up
 * Uses local_regional_synthesis and local_regional_examples for community stories.
 * Falls back to a mega story about community/action if local data is thin.
 */
export function selectMeanwhile(
  megaStories: MegaStory[],
  localRegionalSynthesis: string,
  localRegionalExamples: any[],
  threadTitle: string,
  gapTitle: string
): SectionStory | null {
  // If we have rich local/regional synthesis, use it
  if (localRegionalSynthesis && localRegionalSynthesis.length > 50) {
    // Build a synthetic SectionStory from local_regional data
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

  // Fallback: find a mega story about community action
  if (megaStories && megaStories.length > 0) {
    const communityKeywords = ['community', 'local', 'action', 'resistance', 'municipal',
      'council', 'support', 'care', 'organizing', 'initiative', 'movement', 'solidarity'];
    const remaining = megaStories.filter(s => s.name !== threadTitle && s.name !== gapTitle);

    for (const story of remaining) {
      const text = (story.name + ' ' + story.synthesis).toLowerCase();
      if (communityKeywords.some(kw => text.includes(kw))) {
        return megaToSection(story);
      }
    }

    // If nothing matches keywords, use whatever mega story is left
    if (remaining.length > 0) {
      return megaToSection(remaining[0]);
    }
  }

  return null;
}
