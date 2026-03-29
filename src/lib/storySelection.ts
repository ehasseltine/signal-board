/**
 * Story selection logic for Signal Board
 *
 * Supports TWO data formats:
 * - Legacy (2026-03-28): mega_stories with synthesis, cross_spectrum, why_this_matters, watch_for
 * - Current (2026-03-29+): top_stories, what_connects, cooperation, narrative_divergence, editorial
 *
 * Priority for current format: top_stories → what_connects → narrative_divergence
 *
 * When story_syntheses[] exists in the pipeline data (produced by synthesize.py Pass 2),
 * those rich per-story narratives are merged into the SectionStory output, replacing
 * the thin connection-text fallbacks. This is the primary path for quality content.
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
  highlights: Array<{
    title: string;
    source: string;
    url?: string;
    type?: string;
    cooperation_type?: string;
    force_tag?: string;
    connection?: string;
    context?: string;
  }>;
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

export interface StorySynthesis {
  role: string;              // "thread" | "gap" | "meanwhile"
  structural_force: string;
  synthesis: string;         // 2-3 paragraph narrative
  cross_spectrum: string;    // How outlets framed it differently
  why_this_matters: string;  // Personal relevance
  watch_for: string;         // What to track
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

/**
 * Convert a top_story into a SectionStory.
 * Uses connections for narrative, tier_framing for cross-spectrum analysis.
 */
function topStoryToSection(
  ts: TopStory,
  wc?: WhatConnects
): SectionStory {
  // Build synthesis from connections
  const connectionTexts = (ts.connections || []).map(c => c.text).filter(Boolean);
  const synthesis = connectionTexts.join(' ');

  // Build cross-spectrum from tier_framing (how different tiers frame the story)
  const specParts: string[] = [];
  if (ts.tier_framing) {
    for (const [tier, data] of Object.entries(ts.tier_framing)) {
      const label = tier === 'national' ? 'National outlets' :
                    tier === 'international' ? 'International outlets' :
                    tier === 'local-regional' ? 'Local & regional outlets' :
                    tier === 'specialist' ? 'Specialist outlets' :
                    tier === 'explainer' ? 'Explainers' : tier;
      if (data?.sample?.title) {
        specParts.push(`${label} frame it as: "${data.sample.title}"`);
      }
    }
  }

  // If we have a matching what_connects, use its spectrum sources for the sourcesSample
  let sourcesSample: string[] = [];
  if (wc) {
    sourcesSample = [
      ...(wc.left_sources || []),
      ...(wc.right_sources || []),
      ...(wc.international_sources || []),
      ...(wc.local_regional_sources || []),
    ];
  }
  if (sourcesSample.length === 0) {
    sourcesSample = (ts.articles || []).map(a => a.source);
    sourcesSample = [...new Set(sourcesSample)];
  }

  // Build tier counts from articles
  const tierCounts: Record<string, number> = {};
  for (const art of (ts.articles || [])) {
    if (art.tier) {
      tierCounts[art.tier] = (tierCounts[art.tier] || 0) + 1;
    }
  }

  return {
    title: ts.headline,
    synthesis,
    crossSpectrum: specParts.join(' '),
    whyThisMatters: '',
    watchFor: '',
    articleCount: ts.article_count || 0,
    sourceCount: ts.source_count || 0,
    sourcesSample: sourcesSample.slice(0, 12),
    domains: ts.domains || [],
    domainCounts: {},
    sourceTiers: tierCounts,
    changeDescription: '',
    insights: [],
    yesterdayCount: 0,
  };
}

// ── SELECTION FUNCTIONS ──

/**
 * THE DAILY THREAD — The biggest, most cross-cutting story
 *
 * Priority: mega_stories (legacy) → top_stories[0] (current)
 * Uses the story with the most sources across the most tiers.
 * When story_syntheses contains a "thread" entry, its rich narrative
 * replaces the thin connection-text fallback.
 */
export function selectDailyThread(
  megaStories: MegaStory[],
  whatConnects: WhatConnects[],
  topStories: TopStory[],
  editorial?: Editorial,
  storySyntheses?: StorySynthesis[]
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

  // Current format: use top_stories (ranked by source_count × tier_count)
  if (topStories && topStories.length > 0) {
    const scored = topStories.map(ts => ({
      story: ts,
      score: (ts.tier_count || 1) * 100 + (ts.source_count || 0),
    }));
    scored.sort((a, b) => b.score - a.score);
    const pick = scored[0].story;

    // Find matching what_connects for spectrum source details
    const matchWc = whatConnects?.find(wc =>
      wc.structural_force === pick.structural_force ||
      wc.headline?.includes(pick.headline?.substring(0, 30))
    );

    const section = topStoryToSection(pick, matchWc);

    // Merge per-story synthesis if available (the rich narrative from Pass 2)
    const threadSynth = storySyntheses?.find(s => s.role === 'thread');
    if (threadSynth) {
      if (threadSynth.synthesis) section.synthesis = threadSynth.synthesis;
      if (threadSynth.cross_spectrum) section.crossSpectrum = threadSynth.cross_spectrum;
      if (threadSynth.why_this_matters) section.whyThisMatters = threadSynth.why_this_matters;
      if (threadSynth.watch_for) section.watchFor = threadSynth.watch_for;
    } else if (editorial?.thread_to_watch) {
      // Fallback: use editorial's thread_to_watch
      section.watchFor = editorial.thread_to_watch;
    }

    return section;
  }

  // Fallback: what_connects alone
  if (whatConnects && whatConnects.length > 0) {
    const sorted = [...whatConnects].sort((a, b) => (b.total_sources || 0) - (a.total_sources || 0));
    const pick = sorted[0];
    const allSources = [
      ...(pick.left_sources || []),
      ...(pick.right_sources || []),
      ...(pick.international_sources || []),
      ...(pick.local_regional_sources || []),
    ];
    return {
      title: pick.headline,
      synthesis: pick.sample_connection || '',
      crossSpectrum: '',
      whyThisMatters: '',
      watchFor: editorial?.thread_to_watch || '',
      articleCount: pick.article_count || 0,
      sourceCount: pick.total_sources || 0,
      sourcesSample: allSources.slice(0, 12),
      domains: pick.domains || [],
      domainCounts: {},
      sourceTiers: {},
      changeDescription: '',
      insights: [],
      yesterdayCount: 0,
    };
  }

  return null;
}

/**
 * THE DAILY GAP — Where framing diverges most
 *
 * Priority: mega_stories (legacy) → narrative_divergence (current) → second top_story
 */
export function selectDailyGap(
  megaStories: MegaStory[],
  narrativeDivergence: NarrativeDivergence[],
  topStories: TopStory[],
  editorial?: Editorial,
  threadTitle?: string,
  storySyntheses?: StorySynthesis[]
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

  // Current: narrative_divergence — pick one that differs from the thread
  if (narrativeDivergence && narrativeDivergence.length > 0) {
    // Try to find a divergence that's NOT the same story as the thread
    let pick = narrativeDivergence.find(nd =>
      nd.theme !== threadTitle && !nd.theme?.startsWith(threadTitle?.substring(0, 30) || '___')
    );
    if (!pick) pick = narrativeDivergence[0];

    const sources: string[] = (pick.articles || []).map(a => a.source);
    const uniqueSources = [...new Set(sources)];

    // Build framing comparisons from articles — this is the GAP's value
    const framingInsights: string[] = [];
    const articlesByTier: Record<string, any[]> = {};
    for (const art of (pick.articles || [])) {
      const tier = art.tier || 'unknown';
      if (!articlesByTier[tier]) articlesByTier[tier] = [];
      articlesByTier[tier].push(art);
    }

    // Show how different tiers frame the same story
    for (const [tier, arts] of Object.entries(articlesByTier)) {
      const label = tier === 'national' ? 'National outlets' :
                    tier === 'international' ? 'International outlets' :
                    tier === 'local-regional' ? 'Local & regional outlets' :
                    tier === 'specialist' ? 'Specialist outlets' : tier;
      const best = arts[0];
      if (best?.title) {
        framingInsights.push(`${label}: "${best.title}" — ${best.source}`);
      }
    }

    // Build synthesis from the framing tension
    const synthParts: string[] = [];
    if (pick.source_count > 1) {
      synthParts.push(`${pick.source_count} sources are covering this story, but the way they frame it reveals sharp differences in what they think matters.`);
    }

    // Add article-level framing if available
    const framedArticles = (pick.articles || []).filter(a => a.framing);
    if (framedArticles.length > 0) {
      for (const fa of framedArticles.slice(0, 2)) {
        synthParts.push(`${fa.source} frames it as: ${fa.framing}`);
      }
    }

    const gapSection: SectionStory = {
      title: pick.theme || pick.topic,
      synthesis: editorial?.coverage_gap_note || synthParts.join(' ') ||
        `Across ${pick.source_count} sources, the framing diverges, revealing how the same events get shaped into different stories.`,
      crossSpectrum: framingInsights.join(' '),
      whyThisMatters: 'When the same event gets told as different stories, the gap between those frames is where the real story lives.',
      watchFor: '',
      articleCount: pick.articles?.length || 0,
      sourceCount: pick.source_count || 0,
      sourcesSample: uniqueSources.slice(0, 8),
      domains: [pick.topic],
      domainCounts: {},
      sourceTiers: {},
      changeDescription: `${pick.source_count} sources, ${Object.keys(articlesByTier).length} tiers`,
      insights: framingInsights,
      yesterdayCount: 0,
    };

    // Merge per-story synthesis if available
    const gapSynth = storySyntheses?.find(s => s.role === 'gap');
    if (gapSynth) {
      if (gapSynth.synthesis) gapSection.synthesis = gapSynth.synthesis;
      if (gapSynth.cross_spectrum) gapSection.crossSpectrum = gapSynth.cross_spectrum;
      if (gapSynth.why_this_matters) gapSection.whyThisMatters = gapSynth.why_this_matters;
      if (gapSynth.watch_for) gapSection.watchFor = gapSynth.watch_for;
    }

    return gapSection;
  }

  // Fallback: second top_story
  if (topStories && topStories.length > 1) {
    const candidates = topStories.filter(ts => ts.headline !== threadTitle);
    if (candidates.length > 0) {
      const section = topStoryToSection(candidates[0]);
      if (editorial?.coverage_gap_note) {
        section.synthesis = editorial.coverage_gap_note;
      }
      return section;
    }
  }

  return null;
}

/**
 * MEANWHILE — Who showed up (cooperation stories)
 *
 * Priority: cooperation data → local_regional_synthesis → remaining mega_story
 */
export function selectMeanwhile(
  megaStories: MegaStory[],
  cooperation: Cooperation | null,
  localRegionalSynthesis: string,
  localRegionalExamples: any[],
  editorial?: Editorial,
  threadTitle?: string,
  gapTitle?: string,
  storySyntheses?: StorySynthesis[]
): SectionStory | null {
  // Current format: use cooperation data
  if (cooperation && cooperation.highlights && cooperation.highlights.length > 0) {
    const highlights = cooperation.highlights;

    // Build a narrative from the cooperation data, not just stats
    const cooperationNarrative = editorial?.cooperation_highlight
      || `Today, ${cooperation.total_cooperation_stories} stories showed people cooperating — a ${cooperation.cooperation_rate}% cooperation signal across everything we read.`;

    // Build richer insight cards from highlights (with connection text when available)
    const insightCards: string[] = [];
    for (const h of highlights.slice(0, 5)) {
      if (h.connection) {
        insightCards.push(`${h.source}: ${h.connection}`);
      } else {
        insightCards.push(`${h.source}: ${h.title}`);
      }
    }

    // Cooperation types breakdown
    const typeBreakdown: string[] = [];
    if (cooperation.by_type) {
      for (const t of cooperation.by_type.slice(0, 3)) {
        typeBreakdown.push(`${t.type}: ${t.count} stories from ${t.sources.slice(0, 3).join(', ')}`);
      }
    }

    const meanwhileSection: SectionStory = {
      title: 'Who Showed Up Today',
      synthesis: cooperationNarrative,
      crossSpectrum: '',
      whyThisMatters: 'The stories that local and specialist outlets tell are the stories most likely to affect your daily life, and most likely to be missing from the national cycle.',
      watchFor: '',
      articleCount: cooperation.total_cooperation_stories || 0,
      sourceCount: highlights.length,
      sourcesSample: highlights.slice(0, 8).map(h => h.source),
      domains: [],
      domainCounts: {},
      sourceTiers: {},
      changeDescription: `${cooperation.cooperation_rate}% of today's coverage`,
      insights: insightCards,
      yesterdayCount: 0,
    };

    // Merge per-story synthesis if available
    const meanwhileSynth = storySyntheses?.find(s => s.role === 'meanwhile');
    if (meanwhileSynth) {
      if (meanwhileSynth.synthesis) meanwhileSection.synthesis = meanwhileSynth.synthesis;
      if (meanwhileSynth.cross_spectrum) meanwhileSection.crossSpectrum = meanwhileSynth.cross_spectrum;
      if (meanwhileSynth.why_this_matters) meanwhileSection.whyThisMatters = meanwhileSynth.why_this_matters;
      if (meanwhileSynth.watch_for) meanwhileSection.watchFor = meanwhileSynth.watch_for;
    }

    return meanwhileSection;
  }

  // Legacy format: local_regional_synthesis
  if (localRegionalSynthesis && localRegionalSynthesis.length > 50) {
    const exampleTexts = (localRegionalExamples || []).map((ex: any) =>
      typeof ex === 'string' ? ex : (ex.text || JSON.stringify(ex))
    );

    return {
      title: 'Who Showed Up Today',
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
