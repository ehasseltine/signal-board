// Story selection logic ported from generate_today.py
// Works with both cross_spectrum format and sources-with-bias format

interface Synthesis {
  narrative: string;
  key_developments?: string[];
}

interface CrossSpectrum {
  left_lean?: string;
  center?: string;
  right_lean?: string;
  international?: string;
  independent?: string;
}

interface StoryData {
  title: string;
  article_count?: number;
  spectrum_count?: number;
  cross_spectrum?: CrossSpectrum | boolean;
  synthesis?: Synthesis;
  sources?: Record<string, any>;
  from_local?: boolean;
  local_angle?: boolean;
  community_action?: boolean;
  category?: string;
}

interface LocalRegional {
  narrative?: string;
  themes?: string[];
  notable_coverage?: Array<{ source: string; url?: string }>;
  community_actions?: string[];
}

/**
 * Count how many distinct bias categories are represented in sources.
 * Maps bias labels like "center-left" → "left_lean", etc.
 */
function countSpectrumFromSources(sources: Record<string, any>): number {
  const biasCategories = new Set<string>();
  for (const [, info] of Object.entries(sources)) {
    const bias = (info?.bias || '').toLowerCase();
    if (bias.includes('left')) biasCategories.add('left');
    if (bias.includes('right')) biasCategories.add('right');
    if (bias === 'center') biasCategories.add('center');
    if (bias.includes('international')) biasCategories.add('international');
    if (bias.includes('independent')) biasCategories.add('independent');
  }
  return biasCategories.size;
}

export function selectDailyThread(megaStories: StoryData[]): StoryData | null {
  let bestStory: StoryData | null = null;
  let bestScore = 0;

  for (const story of megaStories) {
    const sourceCount = story.sources ? Object.keys(story.sources).length : 0;
    const articleCount = story.article_count || sourceCount;

    // Try cross_spectrum object first
    let populatedCategories = 0;
    if (story.cross_spectrum && typeof story.cross_spectrum === 'object') {
      const cs = story.cross_spectrum as CrossSpectrum;
      populatedCategories = [
        'left_lean', 'center', 'right_lean', 'international', 'independent'
      ].filter(cat => cs[cat as keyof CrossSpectrum]).length;
    }

    // Fall back to counting bias diversity from sources
    if (populatedCategories === 0 && story.sources) {
      populatedCategories = countSpectrumFromSources(story.sources);
    }

    // Also accept spectrum_count or cross_spectrum === true
    if (populatedCategories === 0 && story.spectrum_count) {
      populatedCategories = story.spectrum_count;
    }
    if (populatedCategories === 0 && story.cross_spectrum === true) {
      populatedCategories = 3; // Treat boolean true as meeting threshold
    }

    // Score: prioritize spectrum breadth, then article count
    const score = populatedCategories * 1000 + articleCount;

    if (score > bestScore && populatedCategories >= 3) {
      bestScore = score;
      bestStory = story;
    }
  }

  return bestStory;
}

export function selectDailyGap(
  megaStories: StoryData[],
  localRegional: LocalRegional
): StoryData | null {
  let gapStory: StoryData | null = null;

  // Strategy 1: Look for stories with independent/international framing
  for (const story of megaStories) {
    // Check cross_spectrum object
    if (story.cross_spectrum && typeof story.cross_spectrum === 'object') {
      const cs = story.cross_spectrum as CrossSpectrum;
      const hasAlt = cs.independent || cs.international;
      const hasMain = cs.left_lean || cs.center || cs.right_lean;
      if (hasAlt && hasMain) {
        gapStory = story;
        break;
      }
    }

    // Check sources for bias diversity that suggests framing gap
    if (!gapStory && story.sources) {
      const biases = Object.values(story.sources).map((s: any) => (s?.bias || '').toLowerCase());
      const hasIndependent = biases.some(b => b.includes('independent'));
      const hasInternational = biases.some(b => b.includes('international'));
      const hasMainstream = biases.some(b => b.includes('left') || b.includes('right') || b === 'center');
      if ((hasIndependent || hasInternational) && hasMainstream) {
        gapStory = story;
        break;
      }
    }
  }

  // Strategy 2: Pick a story with fewest sources (likely underreported)
  if (!gapStory) {
    let fewest = Infinity;
    for (const story of megaStories) {
      const count = story.sources ? Object.keys(story.sources).length : 0;
      if (count > 0 && count < fewest) {
        fewest = count;
        gapStory = story;
      }
    }
  }

  // Strategy 3: Fall back to notable local/regional coverage
  if (!gapStory && localRegional?.notable_coverage?.length) {
    gapStory = {
      title: (localRegional.narrative || 'Local and Regional News').substring(0, 100),
      from_local: true,
      sources: Object.fromEntries(
        localRegional.notable_coverage.map(src => [src.source, { url: src.url || '' }])
      ),
      synthesis: {
        narrative: localRegional.narrative || '',
        key_developments: localRegional.themes || []
      }
    };
  }

  return gapStory;
}

export function selectMeanwhile(
  megaStories: StoryData[],
  localRegional: LocalRegional
): StoryData | null {
  // Keywords suggesting community action / "meanwhile" content
  const meanwhileKeywords = [
    'community', 'local', 'action', 'resistance', 'municipal',
    'council', 'support', 'care', 'organizing', 'initiative',
    'movement', 'solidarity', 'mutual aid', 'volunteer', 'neighbors'
  ];

  // Priority 1: Stories explicitly flagged as community_action
  for (const story of megaStories) {
    if (story.community_action) return story;
  }

  // Priority 2: Check local_regional community_actions or narrative
  if (localRegional) {
    const actions = localRegional.community_actions || [];
    const narrative = (localRegional.narrative || '').toLowerCase();
    const themes = localRegional.themes || [];

    if (
      actions.length > 0 ||
      meanwhileKeywords.some(kw => narrative.includes(kw)) ||
      themes.some(t => meanwhileKeywords.some(kw => String(t).toLowerCase().includes(kw)))
    ) {
      return {
        title: 'Communities Taking Action',
        from_local: true,
        synthesis: {
          narrative: localRegional.narrative || actions.join('. ') || '',
          key_developments: actions.length > 0 ? actions : themes
        },
        sources: Object.fromEntries(
          (localRegional.notable_coverage || []).map(src => [src.source, { url: src.url || '' }])
        )
      };
    }
  }

  // Priority 3: Search mega stories by keyword
  for (const story of megaStories) {
    const title = (story.title || '').toLowerCase();
    const narrative = (story.synthesis?.narrative || '').toLowerCase();

    if (meanwhileKeywords.some(kw => title.includes(kw) || narrative.includes(kw))) {
      return story;
    }
  }

  return null;
}
