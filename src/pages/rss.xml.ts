import type { APIContext } from 'astro';
import { listDailyDates, loadDailyData } from '../lib/data';

export async function GET(context: APIContext) {
  const siteUrl = 'https://www.elisehasseltine.com/signal-board';
  const dates = listDailyDates().slice(0, 30); // Last 30 days

  const items = dates.map(date => {
    const data = loadDailyData(date);
    if (!data) return '';

    const editorial = data.editorial || {};
    const headline = editorial.accessible_headline || editorial.headline || `Signal Board - ${date}`;
    const description = editorial.subheadline || editorial.coverage_gap_note || `Daily news analysis from 300 sources for ${date}`;
    const synthesis = editorial.synthesis || '';
    // Build a short excerpt (first paragraph, no HTML)
    const excerpt = synthesis.split('\n\n')[0] || description;

    const summary = data.summary || {};
    const sourceCount = summary.sources_reporting || 0;
    const articleCount = summary.total_stories || 0;

    return `    <item>
      <title>${escapeXml(headline)}</title>
      <link>${siteUrl}/archive/${date}/</link>
      <guid isPermaLink="true">${siteUrl}/archive/${date}/</guid>
      <pubDate>${new Date(date + 'T07:00:00Z').toUTCString()}</pubDate>
      <description>${escapeXml(excerpt)}</description>
      <dc:creator>Elise Hasseltine</dc:creator>
      ${sourceCount ? `<signal:sources>${sourceCount}</signal:sources>` : ''}
      ${articleCount ? `<signal:articles>${articleCount}</signal:articles>` : ''}
    </item>`;
  }).filter(Boolean);

  const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:signal="https://www.elisehasseltine.com/signal-board/ns">
  <channel>
    <title>Signal Board</title>
    <link>${siteUrl}</link>
    <description>Daily news analysis from 300 sources across the political spectrum, across borders, and across languages. See what no single outlet can show you.</description>
    <language>en-us</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${siteUrl}/rss.xml" rel="self" type="application/rss+xml" />
    <copyright>Elise Hasseltine</copyright>
    <managingEditor>elise@elisehasseltine.com (Elise Hasseltine)</managingEditor>
    <ttl>1440</ttl>
    <image>
      <url>${siteUrl}/favicon-192.png</url>
      <title>Signal Board</title>
      <link>${siteUrl}</link>
    </image>
${items.join('\n')}
  </channel>
</rss>`;

  return new Response(rss, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
    },
  });
}

function escapeXml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}
