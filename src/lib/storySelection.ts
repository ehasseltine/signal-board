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
  tier_breakdown?: Record<string, string[]>;
  international_sources?: string[];
  local_regional_sources?: string[];
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

  // PRIMARY: actual article sources from this story, ordered by editorial interest
  // International & local-regional sources first (unique angles), then specialist, then national
  // Within national, deprioritize aggregators
  const AGGREGATORS = new Set(['RealClearPolitics', 'RealClearDefense', 'RealClearEnergy', 'Google News', 'Yahoo News', 'MSN']);
  const TIER_PRIORITY: Record<string, number> = {
    'international': 0,
    'local-regional': 1,
    'specialist': 2,
    'national': 3,
  };

  // Combine articles + connections + tier_framing samples for complete source picture
  const allSourceEntries: Array<{ source: string; tier: string }> = [];

  for (const art of (ts.articles || [])) {
    allSourceEntries.push({ source: art.source, tier: art.tier || 'national' });
  }
  // Add sources from connections that aren't already in articles
  const articleSources = new Set((ts.articles || []).map(a => a.source));
  for (const conn of (ts.connections || [])) {
    if (conn.source && !articleSources.has(conn.source)) {
      allSourceEntries.push({ source: conn.source, tier: 'national' });
    }
  }
  // Add sources from tier_framing samples
  if (ts.tier_framing) {
    for (const [tier, data] of Object.entries(ts.tier_framing)) {
      if (data?.sample?.source && !articleSources.has(data.sample.source)) {
        allSourceEntries.push({ source: data.sample.source, tier });
      }
    }
  }

  const sortedArticles = allSourceEntries.sort((a, b) => {
    const aTier = TIER_PRIORITY[a.tier || 'national'] ?? 3;
    const bTier = TIER_PRIORITY[b.tier || 'national'] ?? 3;
    if (aTier !== bTier) return aTier - bTier;
    // Within same tier, deprioritize aggregators
    const aAgg = AGGREGATORS.has(a.source) ? 1 : 0;
    const bAgg = AGGREGATORS.has(b.source) ? 1 : 0;
    return aAgg - bAgg;
  });

  let sourcesSample = [...new Set(sortedArticles.map(a => a.source))];

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
      if (threadSynth.structural_force) {
        section.title = threadSynth.structural_force.charAt(0).toUpperCase() + threadSynth.structural_force.slice(1);
      }
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
    const allSources = pick.tier_breakdown
      ? Object.values(pick.tier_breakdown).flat()
      : [
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
  // Determine the thread's structural force so the Gap always picks a DIFFERENT force.
  // This is the core editorial rule: the Gap must surface a different structural force than the Thread.
  const threadSynth = storySyntheses?.find(s => s.role === 'thread');
  const threadForce = threadSynth?.structural_force?.toLowerCase() || '';

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

  // Current: narrative_divergence — pick the entry that matches the gap synthesis's structural force
  if (narrativeDivergence && narrativeDivergence.length > 0) {
    const gapSynth = storySyntheses?.find(s => s.role === 'gap');
    let pick: NarrativeDivergence | undefined;

    if (gapSynth?.structural_force) {
      // Primary: match by the gap synthesis's structural force
      const gapForce = gapSynth.structural_force.toLowerCase();
      pick = narrativeDivergence.find(nd =>
        nd.structural_force?.toLowerCase() === gapForce
      );
    }

    if (!pick) {
      // Fallback: pick any ND whose structural force differs from the thread's
      pick = narrativeDivergence.find(nd =>
        nd.structural_force?.toLowerCase() !== threadForce
      );
    }

    if (!pick) {
      // Last resort: pick the second ND entry (skip the first, which likely matches the thread)
      pick = narrativeDivergence.length > 1 ? narrativeDivergence[1] : narrativeDivergence[0];
    }

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
        framingInsights.push(`${label}: "${best.title}" (${best.source})`);
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

    const tierCount = Object.keys(articlesByTier).length;
    // ND entries are derived from top_stories[:3] — the articles array is a sample (max 6),
    // not the full count. Look up the matching top_story for the real article_count.
    const matchingTopStory = topStories.find(ts =>
      ts.structural_force?.toLowerCase() === pick.structural_force?.toLowerCase()
    );
    const realArticleCount = matchingTopStory?.article_count || pick.articles?.length || 0;
    const gapSection: SectionStory = {
      title: pick.theme || pick.topic,
      synthesis: synthParts.join(' ') ||
        `Across ${pick.source_count} sources, the framing diverges, revealing how the same events get shaped into different stories.`,
      crossSpectrum: framingInsights.join(' '),
      whyThisMatters: 'When the same event gets told as different stories, the gap between those frames is where the real story lives.',
      watchFor: '',
      articleCount: realArticleCount,
      sourceCount: pick.source_count || 0,
      sourcesSample: uniqueSources.slice(0, 8),
      domains: [pick.topic],
      domainCounts: {},
      sourceTiers: {},
      changeDescription: `${pick.source_count} sources, ${tierCount} ${tierCount === 1 ? 'tier' : 'tiers'}`,
      insights: framingInsights,
      yesterdayCount: 0,
    };

    // Merge per-story synthesis if available — overrides narrative text but NOT counts/sources.
    // The counts must come from the matched ND entry above, not from the synthesis text.
    if (gapSynth) {
      if (gapSynth.synthesis) gapSection.synthesis = gapSynth.synthesis;
      if (gapSynth.cross_spectrum) gapSection.crossSpectrum = gapSynth.cross_spectrum;
      if (gapSynth.why_this_matters) gapSection.whyThisMatters = gapSynth.why_this_matters;
      if (gapSynth.watch_for) gapSection.watchFor = gapSynth.watch_for;
      // Use structural_force as title when available — it's a cleaner editorial label
      // than the raw connection string which may be truncated or overly long
      if (gapSynth.structural_force) {
        gapSection.title = gapSynth.structural_force.charAt(0).toUpperCase() + gapSynth.structural_force.slice(1);
      }
    }

    return gapSection;
  }

  // Fallback: second top_story
  if (topStories && topStories.length > 1) {
    const candidates = topStories.filter(ts =>
      ts.structural_force?.toLowerCase() !== threadForce &&
      ts.headline !== threadTitle
    );
    if (candidates.length > 0) {
      const section = topStoryToSection(candidates[0]);
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

    // ── INSIGHT CARDS: Only use connection text (analysis), NEVER raw titles ──
    // If a highlight has no connection text, it has no analytical value — skip it.
    const insightCards: string[] = [];
    for (const h of highlights.slice(0, 8)) {
      if (h.connection && h.connection.length > 20) {
        insightCards.push(`${h.source}: ${h.connection}`);
      }
      if (insightCards.length >= 5) break;
    }

    // ── COOPERATION TYPES: Build analytical breakdown ──
    const typeBreakdown: string[] = [];
    if (cooperation.by_type) {
      for (const t of cooperation.by_type.slice(0, 4)) {
        typeBreakdown.push(`${t.type}: ${t.count} stories from ${t.sources.slice(0, 3).join(', ')}`);
      }
    }

    // ── SYNTHESIS: Rich narrative, never a generic stats template ──
    // Priority: Pass 2 synthesis → editorial cooperation_highlight → constructed narrative from data
    const meanwhileSynth = storySyntheses?.find(s => s.role === 'meanwhile');
    let synthesis: string;
    let crossSpectrum = '';
    let whyThisMatters = '';
    let watchFor = '';

    if (meanwhileSynth?.synthesis) {
      // Best case: Pass 2 ran and produced rich editorial content
      synthesis = meanwhileSynth.synthesis;
      crossSpectrum = meanwhileSynth.cross_spectrum || '';
      whyThisMatters = meanwhileSynth.why_this_matters || '';
      watchFor = meanwhileSynth.watch_for || '';
    } else if (editorial?.cooperation_highlight && editorial.cooperation_highlight.length > 80) {
      // Good case: Pass 1 editorial has a substantive cooperation highlight
      synthesis = editorial.cooperation_highlight;
    } else {
      // Fallback: construct a real narrative from the cooperation data itself.
      // NEVER use a generic stats template. Build from specific stories and sources.
      const storyParts: string[] = [];
      const highlightsWithText = highlights.filter(h => h.connection && h.connection.length > 20);

      if (highlightsWithText.length >= 2) {
        // Lead with the count, then immediately go to specific stories
        storyParts.push(
          `While the national cycle focused elsewhere, ${cooperation.total_cooperation_stories} stories across everything we read, a ${cooperation.cooperation_rate}% cooperation signal, showed people building, fixing, and showing up.`
        );
        // Add 2-3 specific stories with source attribution
        for (const h of highlightsWithText.slice(0, 3)) {
          storyParts.push(`${h.source} reported: ${h.connection}`);
        }
      } else {
        // Even without good connection text, build from types rather than generic stats
        storyParts.push(
          `${cooperation.total_cooperation_stories} stories today showed cooperation at work, ${cooperation.cooperation_rate}% of everything we read.`
        );
        if (typeBreakdown.length > 0) {
          storyParts.push(`The biggest patterns: ${typeBreakdown.slice(0, 2).join('; ')}.`);
        }
        // Name specific sources even if we lack connection text
        const namedSources = highlights.slice(0, 3).map(h => h.source).filter(Boolean);
        if (namedSources.length > 0) {
          storyParts.push(`Stories came from outlets like ${namedSources.join(', ')}, the kind of coverage that rarely breaks through to national attention.`);
        }
      }
      synthesis = storyParts.join('\n\n');
    }

    // ── WHY THIS MATTERS: Construct from data if Pass 2 didn't provide it ──
    if (!whyThisMatters) {
      // Build a specific whyThisMatters from cooperation types rather than a platitude
      const topTypes = (cooperation.by_type || []).slice(0, 2).map(t => t.type);
      if (topTypes.length > 0) {
        whyThisMatters = `Today's biggest cooperation patterns were ${topTypes.join(' and ')}. These are the stories about whether the systems around you, from schools to courts to local government, are actually working. They don't make national news because they're slow and local, but they're the ones most likely to change your daily life.`;
      } else {
        whyThisMatters = 'These are the stories about whether the systems closest to your life are working. Local and specialist outlets tell the stories that national coverage skips, the ones most likely to show up in your school, your neighborhood, or your next bill.';
      }
    }

    const meanwhileSection: SectionStory = {
      title: 'Who Showed Up Today',
      synthesis,
      crossSpectrum,
      whyThisMatters,
      watchFor,
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
      whyThisMatters: 'The stories that local and specialist outlets tell are the stories most likely to affect your daily life, and most likely to be missing from the national cycle.',
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
