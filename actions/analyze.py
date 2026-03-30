#!/usr/bin/env python3
"""
Signal Board — Daily narrative analysis generator.

Reads today's articles (with AI classification, domain tags, structural
force tags, and cross-domain connection insights), clusters them by
STRUCTURAL FORCE (not keyword overlap), analyzes how different source
tiers and perspectives frame each force, and produces a structured JSON
that the frontend renders.

The key insight: articles about tariffs, articles about AI job loss, and
articles about immigration policy may all be driven by the same structural
force — "labor market transformation." This engine finds those connections.

Principles:
  - Simple, clear, factual language. No moral opinions.
  - Humanize where people come from without justifying harm.
  - If something is illegal, state that clearly (confirmed by law).
  - Contextualize every source: they are all media organizations with interests.
  - Preempt what readers want to know.
  - Never be ambiguous.

Usage:
    python actions/analyze.py                    # analyze today
    python actions/analyze.py --date 2026-03-28  # analyze specific date
"""

import json
import re
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter

from domains import get_domain_labels

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
ARTICLES_FILE = ROOT / "data" / "articles.json"
DAILY_DIR = ROOT / "data" / "daily"

# Source context: factual, non-partisan descriptions of ownership/funding
SOURCE_CONTEXT = {
    "100 Days in Appalachia": "Nonprofit news project founded in 2016 at West Virginia University, covering culture, politics, and economic life across the Appalachian region.",
    "404 Media": "Journalist-owned technology publication founded in 2023 by former Motherboard staff, covering cybersecurity, digital culture, and internet policy investigations.",
    "AARP": "Magazine and digital news platform published by the nonprofit AARP, founded in 1958, covering health, caregiving, retirement, and policy affecting older Americans.",
    "ABC Australia": "Australian Broadcasting Corporation, a government-funded public broadcaster founded in 1932, covering Australian domestic and international news.",
    "ABC News": "Broadcast news division of the Walt Disney Company, founded in 1945, providing national and international news across television and digital platforms.",
    "AP News": "Nonprofit news cooperative founded in 1846 and owned by its member newspapers and broadcasters, operating as a global wire service in 100 countries.",
    "African Arguments": "Research and analysis platform published by the Royal African Society in London, covering politics, economics, and governance across the African continent.",
    "Al Jazeera": "International news network founded in 1996, funded by the government of Qatar, headquartered in Doha, covering global news with Middle East emphasis.",
    "Alabama Political Reporter": "Independent news outlet founded in 2011 covering Alabama state government, elections, and policy from Montgomery.",
    "Alaska Public Media": "Public radio and television network serving Alaska, funded by member donations and the Corporation for Public Broadcasting, covering Arctic and statewide issues.",
    "American Enterprise Institute": "Policy research organization founded in 1938 in Washington DC, funded by corporate and individual donors, publishing research on economics, foreign policy, and governance.",
    "American Prospect": "Magazine founded in 1990 by Robert Kuttner, Paul Starr, and Robert Reich, covering politics, policy, and economics from Washington DC.",
    "Americas Quarterly": "Policy publication founded in 2007 by the Americas Society and Council of the Americas, covering politics, business, and trade across Latin America.",
    "Anadolu Agency": "State-owned Turkish news agency founded in 1920 in Ankara, providing international news coverage as Turkey's official wire service.",
    "Arab American News": "Weekly community newspaper founded in 1984, based in Dearborn, Michigan, serving Arab American communities with news on local issues and Middle Eastern affairs.",
    "Arizona Mirror": "Nonprofit newsroom part of the States Newsroom network, founded in 2018, covering Arizona state government, elections, and public policy.",
    "Arkansas Times": "Alternative newsweekly founded in 1974 in Little Rock, covering Arkansas politics, arts, culture, and investigative reporting.",
    "Ars Technica": "Technology publication founded in 1998, owned by Conde Nast since 2008, covering science, technology policy, and digital culture with technical depth.",
    "AsAmNews": "Independent digital news outlet founded in 2014, covering news, politics, and cultural issues affecting Asian American and Pacific Islander communities.",
    "Atlanta Black Star": "Digital news publication founded in 2011, covering news, politics, culture, and opinion relevant to African American communities across the United States.",
    "BBC World": "British Broadcasting Corporation's international news service, funded by the UK license fee, providing global news coverage from bureaus in over 50 countries.",
    "Balkan Insight": "Nonprofit investigative news outlet run by the Balkan Investigative Reporting Network, covering politics, democracy, and corruption in Southeast Europe.",
    "Baltimore Banner": "Nonprofit newsroom founded in 2022 with funding from the Venetoulis family, covering Baltimore city government, Maryland politics, and community news.",
    "Bangkok Post": "Thai English-language newspaper founded in 1946, owned by the Post Publishing Public Company, covering Southeast Asian news, politics, and business.",
    "Bellingcat": "Netherlands-based investigative journalism collective founded in 2014 by Eliot Higgins, using open-source intelligence methods to verify conflicts and disinformation worldwide.",
    "Ben Shapiro Show": "Daily podcast hosted by Ben Shapiro and produced by the Daily Wire, founded in 2015, covering politics, culture, and news commentary.",
    "Bipartisan Policy Center": "Policy research organization founded in 2007 by former Senate majority leaders from both parties, publishing research promoting bipartisan governance solutions.",
    "Blavity": "Digital media company founded in 2014 by Morgan DeBaun, covering entertainment, news, and culture for Black millennial and Gen Z audiences.",
    "Bloomberg": "Financial data and news company founded in 1981 by Michael Bloomberg, dominant in financial information services, covering global markets, economics, and business.",
    "Bolts Magazine": "Publication launched in 2022 as a rebrand of The Appeal's political report, covering local elections, prosecutors, and how democracy works at the ground level.",
    "Borderland Beat": "Independent news blog founded in 2009, covering the Mexico-US border region, drug policy, cartel activity, and security issues along the frontier.",
    "Breitbart": "Online news outlet founded in 2007 by Andrew Breitbart, headquartered in Los Angeles, covering national politics, immigration, and cultural commentary.",
    "Brennan Center": "Nonpartisan law and policy institute at New York University, founded in 1995, researching democracy, voting rights, campaign finance, and criminal justice reform.",
    "Bridge Michigan": "Nonprofit newsroom founded in 2011 by the Center for Michigan, covering state government, education, environment, and public policy across Michigan.",
    "Brookings": "Policy research institution founded in 1916 in Washington DC, one of the oldest think tanks in the US, studying economics, governance, and foreign policy.",
    "Brown Girl Magazine": "Digital publication founded in 2008, covering identity, culture, career, and community life for South Asian women and the diaspora in North America.",
    "Bureau of Labor Statistics": "US federal government agency within the Department of Labor, founded in 1884, publishing employment, wage, inflation, and economic productivity data.",
    "Business Insider": "Digital news outlet founded in 2007, owned by Axel Springer since 2015, covering business, technology, finance, and corporate news for a global audience.",
    "CBO Reports": "Congressional Budget Office, a nonpartisan federal agency founded in 1974, publishing cost estimates of legislation and economic projections for Congress.",
    "CNBC": "Business television network owned by NBCUniversal, a division of Comcast, founded in 1989, covering financial markets, corporate earnings, and economic policy.",
    "CNN": "Cable news network founded in 1980 by Ted Turner, now owned by Warner Bros. Discovery, providing 24-hour national and international news coverage.",
    "CT Mirror": "Connecticut Mirror, a nonprofit newsroom founded in 2010, covering state government, public policy, education, and health care in Connecticut.",
    "CalMatters": "Nonprofit newsroom founded in 2015 in Sacramento, covering California state government, policy, elections, and the state legislature for a general audience.",
    "Canopy Forum": "Online publication of the Center for the Study of Law and Religion at Emory University, covering religion, law, and public life.",
    "Capital B": "Black-led nonprofit newsroom founded in 2021 by Lauren Williams and Akoto Ofori-Atta, covering local and national news for Black communities from Atlanta.",
    "Capital B News": "Nonprofit newsroom focused on Black entrepreneurship, business development, and economic empowerment across American cities, launched as part of the Capital B network.",
    "Capitol News Illinois": "Nonprofit newsroom part of the States Newsroom network, covering the Illinois state legislature, Governor's office, and statewide policy from Springfield.",
    "Carbon Brief": "UK-based publication founded in 2011, specializing in clear, data-driven reporting on climate science, energy policy, and global emissions tracking.",
    "Caribbean National Weekly": "Community newspaper and digital outlet serving Caribbean diaspora communities in the United States, covering island news, immigration, and cultural events.",
    "Carnegie Endowment": "International affairs research institution founded in 1910 by Andrew Carnegie, with offices in Washington DC and six other countries, publishing foreign policy analysis.",
    "Cato Institute": "Policy research organization founded in 1977 by Ed Crane and Charles Koch in Washington DC, publishing research on civil liberties, free markets, and limited government.",
    "Census Bureau": "US Census Bureau, a federal statistical agency within the Department of Commerce, established in 1902, publishing population, demographic, and economic data.",
    "Center for American Progress": "Policy research organization founded in 2003 by John Podesta in Washington DC, publishing research on domestic policy, health care, climate, and the economy.",
    "Center for Strategic and International Studies": "Policy research organization founded in 1962 in Washington DC, covering defense, international security, trade, and technology issues with a bipartisan approach.",
    "Center on Budget and Policy Priorities": "Nonpartisan research institute founded in 1981 in Washington DC, analyzing federal and state budget policies affecting people with low and moderate incomes.",
    "Channel News Asia": "News network launched in 1999 by Mediacorp, a Singaporean state-owned media company, covering Asia-Pacific politics, business, and regional affairs.",
    "Chatham House": "International affairs think tank formally known as the Royal Institute of International Affairs, founded in 1920 in London, publishing research on global governance and security.",
    "Christianity Today": "Evangelical magazine founded in 1956 by Billy Graham, based in Carol Stream, Illinois, covering faith, theology, church life, and cultural commentary.",
    "City Limits": "Nonprofit investigative news outlet founded in 1976 in New York City, covering housing, education, immigration, and public policy affecting urban communities.",
    "CityLab": "Urban policy publication now part of Bloomberg, originally founded in 2011 by The Atlantic, covering city governance, housing, transportation, and metropolitan life.",
    "Civil Eats": "Nonprofit publication founded in 2009, covering the American food system including food policy, sustainable agriculture, farm labor, and food justice.",
    "Colorado Sun": "Journalist-owned nonprofit newsroom founded in 2018 by former Denver Post staff, covering Colorado politics, environment, economy, and community life.",
    "Colorlines": "Online news publication founded in 1998 by the Applied Research Center, now Race Forward, covering race, culture, and intersections of policy and identity.",
    "Columbia Journalism Review": "Media criticism and journalism analysis publication founded in 1961 at the Columbia University Graduate School of Journalism in New York City.",
    "Congress.gov": "Official website of the US Congress, maintained by the Library of Congress, providing public access to federal legislation, voting records, and congressional activity.",
    "Council on Foreign Relations": "Nonpartisan membership organization and think tank founded in 1921 in New York City, publishing the journal Foreign Affairs and research on international relations.",
    "Crosscut": "Nonprofit news outlet founded in 2007 in Seattle, part of KCTS 9 public media, covering Pacific Northwest politics, culture, science, and civic life.",
    "Daily Maverick": "South African independent news publication founded in 2009, known for investigative journalism on corruption, governance, and accountability in South Africa and the continent.",
    "Daily Wire": "Media company founded in 2015 by Ben Shapiro and Jeremy Boreing, producing news, commentary, podcasts, and entertainment content from Nashville, Tennessee.",
    "Daily Yonder": "Nonprofit news outlet published by the Center for Rural Strategies, founded in 2007, covering rural America, small-town communities, agriculture, and rural policy.",
    "Dawn": "Pakistani English-language newspaper founded in 1941 by Muhammad Ali Jinnah, published from Karachi, covering national politics and South Asian affairs as Pakistan's oldest newspaper.",
    "Defense One": "Digital publication launched in 2013 by Atlantic Media, now owned by GovExec, covering US defense policy, military technology, and national security developments.",
    "Deutsche Welle": "German international broadcaster founded in 1953 and funded by the German federal government, providing news in 30 languages from Bonn and Berlin.",
    "Disability Scoop": "Independent news organization founded in 2008, covering disability policy, developmental disabilities, intellectual disability issues, and the disability rights community.",
    "Documented": "Nonprofit newsroom founded in 2018 in New York City, covering immigration policy, enforcement, and the daily lives of immigrant communities across the region.",
    "E&E News": "Energy and environment publication founded in 1998, now owned by Politico and Axel Springer, covering climate regulation, energy markets, and environmental policy.",
    "EPI Blog": "Publication of the Economic Policy Institute, a nonprofit research organization founded in 1986 in Washington DC, covering labor economics, wages, and workforce policy.",
    "Education Week": "National news publication founded in 1981, covering K-12 education policy, school reform, teaching practice, and educational equity across the United States.",
    "El Diario NY": "Spanish-language daily newspaper founded in 1913 in New York City, owned by ImpreMedia, serving Latino communities with coverage of immigration, politics, and culture.",
    "El País English": "English edition of El País, Spain's largest daily newspaper, founded in 1976 during Spain's democratic transition, covering global news and European affairs.",
    "Ezra Klein Show": "New York Times podcast hosted by journalist Ezra Klein, featuring long-form interviews and analysis on politics, policy, technology, and ideas.",
    "Federal Register": "Official daily journal of the US federal government, published by the Office of the Federal Register at the National Archives, containing rules and executive orders.",
    "Federal Reserve": "Central bank of the United States, established in 1913 by Congress, publishing monetary policy decisions, interest rate statements, and economic research data.",
    "Florida Phoenix": "Nonprofit newsroom part of the States Newsroom network, founded in 2018, covering Florida state government, policy, and the legislature from Tallahassee.",
    "Foreign Affairs": "Policy journal published since 1922 by the Council on Foreign Relations, featuring analysis from scholars and practitioners on international relations and diplomacy.",
    "Foreign Policy": "Global affairs magazine founded in 1970, owned by the FP Group since 2008, covering international relations, diplomacy, trade, and global security.",
    "Fox News": "Cable news network founded in 1996 by Rupert Murdoch, owned by Fox Corporation, providing 24-hour news, opinion, and political commentary from New York.",
    "France 24": "French international news network launched in 2006, funded by the French government through France Médias Monde, broadcasting in French, English, Arabic, and Spanish.",
    "Freakonomics Radio": "Podcast produced by Stephen Dubner, based on the Freakonomics book series with economist Steven Levitt, exploring economic thinking and human behavior through data and storytelling.",
    "Futuro Media": "Nonprofit media organization founded in 2012 by journalist Maria Hinojosa, producing award-winning journalism for and about communities of color from Harlem, New York.",
    "GAO Reports": "Government Accountability Office, the investigative arm of Congress founded in 1921, publishing audits and reports on how the federal government spends taxpayer money.",
    "GBH News": "Public media news division of GBH in Boston, formerly WGBH, founded in 1951, covering Massachusetts news, politics, education, and New England public affairs.",
    "Georgia Recorder": "Nonprofit newsroom part of the States Newsroom network, founded in 2019, covering Georgia state government, elections, and policy from Atlanta.",
    "Global Voices": "International nonprofit media platform founded in 2004 at Harvard Law School, publishing citizen journalism and translated reports from over 100 countries worldwide.",
    "Good Good Good": "Independent media organization founded in 2019 by Branden Harvey, reporting on positive developments, social change, and community-driven solutions across the world.",
    "Grist": "Nonprofit environmental news outlet founded in 1999 in Seattle, covering climate change, environmental justice, clean energy, and the intersection of race and sustainability.",
    "Haaretz": "Israeli daily newspaper founded in 1918, the country's oldest, published in Hebrew and English from Tel Aviv, covering Israeli politics and Middle Eastern affairs.",
    "Haitian Times": "Community newspaper founded in 1999 in Brooklyn, New York, covering news, politics, and culture relevant to Haitian American and Haitian diaspora communities.",
    "Hard Fork (NYT)": "New York Times technology podcast hosted by Kevin Roose and Casey Newton, covering artificial intelligence, social media, and the cultural impact of technology.",
    "Health Affairs": "Peer-reviewed health policy journal founded in 1981, published by Project HOPE, featuring original research and analysis on US and global health policy.",
    "Heather Cox Richardson": "Daily political history and analysis newsletter on Substack with over 1.5 million subscribers, written by a Boston College history professor since 2019.",
    "Hechinger Report": "Nonprofit newsroom founded in 2009 at Teachers College at Columbia University, covering education inequality, K-12 schools, and higher education policy.",
    "Heritage Foundation": "Policy research organization founded in 1973 in Washington DC, funded by individual and corporate donors, publishing research on domestic and foreign policy.",
    "High Country News": "Nonprofit magazine founded in 1970 in Paonia, Colorado, covering the environment, public lands, communities, and Indigenous issues across the American West.",
    "Honolulu Civil Beat": "Nonprofit newsroom founded in 2010 by Pierre Omidyar in Honolulu, covering Hawaii state government, Pacific issues, and community accountability reporting.",
    "Hoover Institution": "Policy research center founded in 1919 by Herbert Hoover at Stanford University, funded by endowments and donations, publishing research on economics and governance.",
    "Hudson Institute": "Policy research organization founded in 1961 by Herman Kahn in Washington DC, publishing analysis on defense, international relations, and technology strategy.",
    "Idaho Capital Sun": "Nonprofit newsroom part of the States Newsroom network, founded in 2020, covering Idaho state government, public lands, and policy from Boise.",
    "In These Times": "Independent magazine founded in 1976 by James Weinstein in Chicago, covering labor movements, social justice, politics, and worker organizing.",
    "InForum": "Regional newspaper based in Fargo, North Dakota, owned by Forum Communications, covering North Dakota and the Upper Midwest including agriculture and energy policy.",
    "Indian Country Today": "Nonprofit digital news platform founded in 1981 as the Lakota Times, covering news, policy, and culture for American Indian and Alaska Native communities.",
    "Indiana Capital Chronicle": "Nonprofit newsroom part of the States Newsroom network, founded in 2022, covering Indiana state government, legislation, and policy from Indianapolis.",
    "Inequality.org": "Publication of the Institute for Policy Studies, a research organization founded in 1963 in Washington DC, tracking wealth concentration, CEO pay, and economic inequality.",
    "Inside Climate News": "Pulitzer Prize-winning nonprofit newsroom founded in 2007, covering climate change, renewable energy, and environmental justice through investigative and explanatory reporting.",
    "Inside Higher Ed": "Digital publication founded in 2004, covering higher education news, campus governance, academic policy, faculty issues, and the business of universities.",
    "Iowa Capital Dispatch": "Nonprofit newsroom part of the States Newsroom network, founded in 2021, covering Iowa state government, agriculture policy, and legislative affairs from Des Moines.",
    "Jamaica Observer": "Jamaican daily newspaper founded in 1993, based in Kingston, covering Caribbean politics, regional economics, tourism, and Jamaican community life.",
    "Jewish Telegraphic Agency": "International news agency founded in 1917, the oldest English-language Jewish news service, covering Jewish communities, Israel, and interfaith issues worldwide.",
    "Just Security": "Online forum at the NYU School of Law Reiss Center on Law and Security, publishing expert analysis on national security, human rights, and international law.",
    "KFF Health News": "Independent nonprofit newsroom formerly known as Kaiser Health News, founded in 2009 and published by KFF, covering health policy, insurance, and the healthcare system.",
    "Kansas Reflector": "Nonprofit newsroom part of the States Newsroom network, founded in 2020, covering Kansas state government, education, and policy from Topeka.",
    "Kentucky Lantern": "Nonprofit newsroom part of the States Newsroom network, founded in 2022, covering Kentucky state government, politics, and Appalachian policy from Frankfort.",
    "Kyla Scanlon": "Economics and financial markets newsletter and video series by creator Kyla Scanlon, making macroeconomic trends, Federal Reserve policy, and market movements accessible to general audiences.",
    "Labor Notes": "Media and organizing project founded in 1979 in Detroit, publishing a monthly magazine covering union strategy, labor disputes, and worker organizing campaigns.",
    "Latin America Reports": "Digital publication covering politics, economic development, elections, and trade across Latin America and the Caribbean for an English-speaking international audience.",
    "Latino Rebels": "Digital media platform founded in 2011 by Julio Ricardo Varela, covering news, politics, culture, and identity issues relevant to Latino communities in the United States.",
    "Latino USA": "Public radio program founded in 1992 and produced by Futuro Media Group, the longest-running Latino-focused show on US public media, covering culture and news.",
    "Lawfare": "Publication founded in 2010 by Benjamin Wittes at the Brookings Institution, covering national security law, surveillance, cybersecurity, and executive power legal questions.",
    "MIT Technology Review": "Technology magazine founded in 1899 and published by the Massachusetts Institute of Technology, covering artificial intelligence, biotechnology, and emerging technology impacts.",
    "Marketplace (APM)": "Daily business and economics radio show produced by American Public Media since 1989, reaching over 14 million weekly listeners on public radio stations.",
    "Marshall Fund": "German Marshall Fund of the United States, a transatlantic policy think tank founded in 1972, funded by a German government gift, researching US-Europe relations.",
    "Matt Taibbi (Racket News)": "Independent journalism newsletter on Substack by veteran reporter Matt Taibbi, formerly of Rolling Stone, covering media criticism, civil liberties, and political accountability.",
    "Meduza": "Russian-language and English-language independent news outlet founded in 2014 in Riga, Latvia, by former staff of Lenta.ru, covering Russian and global affairs.",
    "Migration Policy Institute": "Nonpartisan research organization founded in 2001 in Washington DC, studying international migration, refugee policy, and immigrant integration across the world.",
    "Military Times": "Independent news organization owned by Sightline Media Group, covering military policy, defense spending, veteran affairs, and service member communities across all branches.",
    "MinnPost": "Nonprofit news organization founded in 2007 in Minneapolis by former Star Tribune editor Joel Kramer, covering Minnesota government, politics, and civic life.",
    "Mississippi Free Press": "Nonprofit newsroom founded in 2020 in Jackson, Mississippi, covering state government, civil rights, education, and community issues across the state.",
    "Montana Free Press": "Nonprofit newsroom founded in 2018, covering Montana state government, public lands, energy policy, and community affairs from Helena and Missoula.",
    "Mother Jones": "Nonprofit investigative magazine founded in 1976 in San Francisco, named after labor organizer Mary Harris Jones, known for long-form investigative and political reporting.",
    "Mountain State Spotlight": "Nonprofit newsroom founded in 2020 covering West Virginia state government, the opioid crisis, economic development, and Appalachian community issues.",
    "Muslim Matters": "Online magazine founded in 2007, covering Islamic faith, Muslim American community life, religious education, and civil rights issues from a community perspective.",
    "NBC News": "Broadcast news division of NBCUniversal, a subsidiary of Comcast, founded in 1940, providing national and international news across television and digital platforms.",
    "NBC News Latino": "Digital news section of NBC News covering news, politics, immigration, and culture relevant to Latino and Hispanic communities across the United States.",
    "NC Health News": "Nonprofit newsroom founded in 2012 in Durham, covering health policy, rural health access, Medicaid, and public health issues across North Carolina.",
    "NHK World": "International broadcasting service of Japan's national public broadcaster NHK, founded in 1935, providing global news coverage in 17 languages from Tokyo.",
    "NJ Spotlight News": "New Jersey news organization covering state government, politics, business, education, environment, and health policy, part of NJTV public television.",
    "NPR": "National Public Radio, a nonprofit media organization founded in 1970, funded by member stations and corporate sponsors, producing news programming for over 1,000 stations.",
    "NPR Up First": "NPR's flagship morning news briefing podcast launched in 2017, delivering a daily ten-minute summary of the top news stories to over 3.5 million listeners.",
    "Naked Capitalism": "Independent financial and economics blog founded in 2006 by Susan Webber under the pen name Yves Smith, covering financial industry practices, economics, and policy.",
    "National Catholic Reporter": "Independent Catholic news organization founded in 1964 in Kansas City, Missouri, not owned by or affiliated with any diocese, covering faith, church, and social issues.",
    "National Review": "Magazine founded in 1955 by William F. Buckley Jr., based in New York, covering politics, domestic policy, foreign affairs, and culture.",
    "Nature News": "News section of Nature, the international scientific journal founded in 1869 by Macmillan Publishers, now owned by Springer Nature, covering research across all sciences.",
    "Navajo Times": "Independent newspaper founded in 1959, owned by the Navajo Nation, the largest Indigenous newspaper in the US, covering tribal government and community life.",
    "Nebraska Examiner": "Nonprofit newsroom part of the States Newsroom network, founded in 2021, covering Nebraska state government, agriculture, and policy from Lincoln.",
    "Nevada Independent": "Nonprofit newsroom founded in 2017 by journalist Jon Ralston in Las Vegas, covering Nevada state government, gaming industry policy, and Western politics.",
    "New America": "Policy research organization founded in 1999 in Washington DC, funded by foundations and tech industry donors, covering technology, education, and national security policy.",
    "New Hampshire Bulletin": "Nonprofit newsroom part of the States Newsroom network, founded in 2021, covering New Hampshire state government, elections, and policy from Concord.",
    "New York Times": "Daily newspaper founded in 1851, owned by the New York Times Company, the largest newspaper by digital subscriptions globally, covering national and world affairs.",
    "Newsmax": "News media company founded in 1998 by Christopher Ruddy, based in Boca Raton, Florida, operating a cable television channel and digital news platform.",
    "Next Avenue": "Digital publication produced by PBS, launched in 2012, covering issues relevant to older Americans including aging, health, work, caregiving, and retirement planning.",
    "NextShark": "Digital news outlet founded in 2014, covering news, culture, entertainment, and identity issues relevant to Asian American and Pacific Islander communities.",
    "Nieman Lab": "Research and journalism project at the Nieman Foundation for Journalism at Harvard University, covering the future of news, media innovation, and journalism industry trends.",
    "Nikkei Asia": "English-language publication of Nikkei Inc., Japan's largest financial news company founded in 1876, covering business, markets, and politics across the Asia-Pacific region.",
    "Ohio Capital Journal": "Nonprofit newsroom part of the States Newsroom network, founded in 2019, covering Ohio state government, elections, and policy from Columbus.",
    "Oklahoma Watch": "Nonprofit newsroom founded in 2012 in Oklahoma City, covering investigative reporting, education, health, criminal justice, and public policy in Oklahoma.",
    "On the Media (WNYC)": "Weekly radio program and podcast produced by WNYC Studios in New York since 2001, hosted by Brooke Gladstone, analyzing how news media shapes public understanding.",
    "OnLabor": "Academic and policy blog founded in 2012 by Harvard Law School scholars, covering labor law, worker organizing, union strategy, and employment policy.",
    "Optimist Daily": "Digital publication founded in 2019, curating and reporting on solutions-focused news, scientific breakthroughs, and positive developments happening around the world.",
    "Oregon Public Broadcasting": "Public media organization founded in 1922, funded by member donations and the Corporation for Public Broadcasting, covering Oregon and Pacific Northwest news and culture.",
    "Payday Report": "Independent labor news outlet founded in 2016 by journalist Mike Elk in Pittsburgh, covering strikes, union organizing, and worker safety issues across the United States.",
    "Pew Research Center": "Nonpartisan research organization founded in 2004 as a subsidiary of the Pew Charitable Trusts, conducting public opinion polling, demographic research, and media analysis.",
    "Pivot (Kara Swisher)": "Technology and business podcast hosted by journalists Kara Swisher and Scott Galloway, covering tech industry power, corporate strategy, and market disruption.",
    "Planet Money (NPR)": "NPR economics podcast launched in 2008, producing narrative stories that make trade, finance, and economic policy accessible to two million weekly listeners.",
    "Platformer": "Technology newsletter founded in 2020 by journalist Casey Newton, covering social media platform governance, content moderation, and internet policy decisions.",
    "Politico": "Political news organization founded in 2007 by John Harris and Jim VandeHei, now owned by Axel Springer, covering Congress, the White House, campaigns, and policy.",
    "Popular Information (Judd Legum)": "Investigative newsletter founded in 2018 on Substack by journalist Judd Legum, tracking corporate political donations, lobbying, and accountability.",
    "Positive News": "UK-based media cooperative founded in 1993, covering constructive journalism focused on social progress, sustainability, and solutions across the world.",
    "Post and Courier": "Daily newspaper founded in 1803 in Charleston, South Carolina, the oldest newspaper in the South, covering state politics, culture, and investigative reporting.",
    "Press Freedom Tracker": "Database launched in 2017 by the Freedom of the Press Foundation and the Committee to Protect Journalists, documenting press freedom violations in the US.",
    "Press Gazette": "UK-based trade publication founded in 1965, covering the global media industry, journalism business models, press freedom, and media economics.",
    "Prism": "Nonprofit newsroom founded in 2020, reporting on how systemic inequality and injustice affect communities of color through policy, housing, education, and the economy.",
    "ProPublica": "Nonprofit investigative newsroom founded in 2008 by Paul Steiger with funding from Herbert and Marion Sandler, producing accountability journalism on government and corporate power.",
    "Protocol Africa": "News publication covering technology innovation, startup ecosystems, digital infrastructure, and business development across the African continent.",
    "RAND": "Policy research organization founded in 1948 as a project of the Douglas Aircraft Company, now independent in Santa Monica, analyzing defense, health, and education policy.",
    "Radiolab": "Podcast and radio program produced by WNYC Studios since 2002, hosted by Lulu Miller and Latif Nasser, exploring science, philosophy, and human experience through storytelling.",
    "Rappler": "Philippine digital news organization founded in 2012 by journalist Maria Ressa in Manila, covering Southeast Asian politics, governance, and social media disinformation.",
    "RealClearPolitics": "Political news aggregation website founded in 2000 by John McIntyre and Tom Bevan, curating articles and polling averages from across the political spectrum.",
    "Reason": "Magazine founded in 1968 and published by the Reason Foundation in Los Angeles, covering civil liberties, free markets, criminal justice reform, and governance.",
    "Reasons to be Cheerful": "Solutions journalism publication founded in 2018 by musician David Byrne, reporting on evidence-based stories of progress and practical change happening around the world.",
    "Religion News Service": "Nonprofit wire service and news outlet founded in 1934, providing independent coverage of religion, faith communities, spirituality, and ethics across all traditions.",
    "Remezcla": "Digital media company founded in 2006, covering Latino art, music, film, culture, and identity for a bilingual English and Spanish-speaking audience.",
    "Rest of World": "Nonprofit global technology publication founded in 2020 by journalist Sophie Schmidt, covering how technology shapes the lives of people outside the Western tech industry.",
    "Reuters": "International news agency founded in 1851 in London, now owned by Thomson Reuters, operating as one of the largest global wire services.",
    "Rhode Island Current": "Nonprofit newsroom part of the States Newsroom network, founded in 2022, covering Rhode Island state government, legislation, and policy from Providence.",
    "Roosevelt Institute": "Policy think tank founded in 1987 and inspired by Franklin and Eleanor Roosevelt, publishing research on economic policy, inequality, and democratic governance.",
    "STAT News": "Health and science news publication founded in 2015 by Boston Globe Media Partners, covering the pharmaceutical industry, biotechnology, medicine, and health policy.",
    "Salt Lake Tribune": "Daily newspaper founded in 1871 in Salt Lake City, converted to nonprofit status in 2019, covering Utah politics, religion, public lands, and the environment.",
    "Scalawag": "Nonprofit digital media organization founded in 2014 in Durham, North Carolina, covering power structures, storytelling, and civic life across the American South.",
    "Science News": "Independent science journalism magazine founded in 1921 by the Society for Science, covering research developments across physics, biology, earth science, and medicine.",
    "Scroll.in": "Indian English-language digital news publication founded in 2014, covering politics, culture, science, and public policy with an independent editorial approach.",
    "Slow Boring (Matt Yglesias)": "Policy analysis newsletter on Substack by journalist and author Matt Yglesias, formerly of Vox, covering governance, urban policy, economics, and institutional reform.",
    "Sojourners": "Faith-based magazine and community founded in 1971 by Jim Wallis in Washington DC, covering the intersection of Christian faith, social justice, and public policy.",
    "Source NM": "Nonprofit newsroom part of the States Newsroom network, founded in 2021, covering New Mexico state government, tribal affairs, and water policy from Santa Fe.",
    "South China Morning Post": "English-language newspaper founded in 1903 in Hong Kong, owned by Alibaba Group since 2016, covering Asia-Pacific business, geopolitics, and Chinese affairs.",
    "South Dakota Searchlight": "Nonprofit newsroom part of the States Newsroom network, founded in 2022, covering South Dakota state government, Indigenous affairs, and Plains policy from Sioux Falls.",
    "Spotlight PA": "Nonprofit investigative newsroom founded in 2019 through a collaboration of Philadelphia Inquirer, Pittsburgh Post-Gazette, and PennLive, covering Pennsylvania state government.",
    "Stars and Stripes": "Independent newspaper authorized by the US Department of Defense, continuously published since 1942, covering military news and affairs for service members and veterans.",
    "Stateline": "Nonprofit news service founded in 1998 by the Pew Charitable Trusts, covering state government trends, policy innovations, and legislative developments across all 50 states.",
    "Straits Times": "Singapore's English-language broadsheet newspaper, founded in 1845, owned by Singapore Press Holdings, covering Southeast Asian and global news, politics, and business.",
    "Supreme Court": "Official website of the Supreme Court of the United States, publishing opinions, orders, oral argument transcripts, and case filings for the nation's highest court.",
    "Taipei Times": "Taiwanese English-language daily newspaper founded in 1999, covering Taiwan domestic politics, cross-strait relations, and Asia-Pacific regional affairs.",
    "Task and Purpose": "Digital military news publication founded in 2014 by Iraq War veteran Zach Iscol, covering military life, defense policy, and veteran community issues.",
    "TechCrunch": "Technology industry publication founded in 2005 by Michael Arrington, now owned by Yahoo, covering startups, venture capital, product launches, and Silicon Valley.",
    "Teen Vogue": "Digital publication owned by Conde Nast, relaunched online in 2017 with expanded political and cultural coverage aimed at young adult and Gen Z readers.",
    "Tennessee Lookout": "Nonprofit newsroom part of the States Newsroom network, founded in 2021, covering Tennessee state politics, legislation, and policy from Nashville.",
    "Texas Observer": "Independent nonprofit magazine founded in 1954 in Austin, covering Texas politics, civil rights, border issues, and investigative reporting for over seven decades.",
    "Texas Tribune": "Nonprofit digital news organization founded in 2009 by Evan Smith, Ross Ramsey, and John Thornton, covering Texas state government, elections, and policy from Austin.",
    "The 19th": "Independent nonprofit newsroom founded in 2020, named for the 19th Amendment, covering gender equity, women in politics, and LGBTQ+ policy across the United States.",
    "The 19th News": "Nonprofit newsroom founded in 2020, covering women, gender, and LGBTQ+ policy at the intersection of politics, providing national reporting on equity and representation.",
    "The Advocate": "LGBTQ+ news magazine founded in 1967 in Los Angeles, the oldest and largest publication serving LGBTQ+ communities, covering rights, culture, and politics.",
    "The Atlantic": "Magazine founded in 1857 in Boston by Ralph Waldo Emerson and others, owned by Laurene Powell Jobs since 2017, covering politics, culture, and ideas.",
    "The Blaze": "Media company founded in 2011 by Glenn Beck, based in Irving, Texas, producing news, opinion, and entertainment content across digital and video platforms.",
    "The Chronicle of Higher Education": "Weekly publication founded in 1966 in Washington DC, covering the academic world including university governance, faculty employment, and higher education policy.",
    "The Conversation US": "Nonprofit media outlet launched in the US in 2014, part of a global network, publishing research-based articles written by university academics for a general audience.",
    "The Daily": "New York Times flagship daily news podcast launched in 2017, hosted by Michael Barbaro, reaching over four million listeners per day with in-depth news storytelling.",
    "The Diplomat": "International current affairs magazine founded in 2002, based in Washington DC, covering Asia-Pacific politics, security, economics, and diplomacy.",
    "The Dispatch": "Online news and commentary publication founded in 2019 by Jonah Goldberg and Stephen Hayes, covering politics, policy, and cultural analysis from Washington DC.",
    "The East African": "Weekly regional newspaper published by Nation Media Group of Kenya, founded in 1994, covering politics, economics, and society across East and Central Africa.",
    "The Federalist": "Online publication founded in 2013 by Ben Domenech and Sean Davis, covering politics, policy, culture, and religion from Washington DC.",
    "The Forward": "Jewish American news organization founded in 1897 as a Yiddish-language daily, now digital and in English, covering Jewish culture, politics, and community issues.",
    "The Free Press (Bari Weiss)": "Independent journalism outlet founded in 2021 by journalist Bari Weiss, covering culture, politics, free speech, and institutional debates through a newsletter and podcast.",
    "The Globe Post": "International news outlet founded in 2017, covering global affairs, geopolitics, and international analysis from correspondents in multiple countries.",
    "The Globe and Mail": "Canadian national newspaper of record, founded in 1844 in Toronto, owned by the Woodbridge Company, covering Canadian politics, business, and international affairs.",
    "The Grio": "Digital news platform launched in 2009, now owned by Byron Allen's Allen Media Group, covering news, culture, politics, and entertainment for Black American audiences.",
    "The Guardian World": "British newspaper founded in 1821, owned by the Scott Trust nonprofit, one of the most-read English-language news sites globally, covering international affairs.",
    "The Hill": "Political news organization founded in 1994 in Washington DC, owned by Nexstar Media Group since 2021, covering Congress, the White House, and campaigns.",
    "The Hindu": "Indian English-language newspaper founded in 1878 in Chennai, owned by the Kasturi and Sons family trust, covering national and international news.",
    "The Imprint": "Nonprofit newsroom founded in 2015, covering child welfare, foster care, juvenile justice, and youth policy issues in the United States.",
    "The Intercept": "Online news publication founded in 2014 by Glenn Greenwald, Laura Poitras, and Jeremy Scahill, initially funded by Pierre Omidyar, covering national security and civil liberties.",
    "The Japan Times": "Japan's oldest English-language newspaper, founded in 1897 in Tokyo, owned by News2u Holdings, covering Japanese politics, culture, and Asia-Pacific affairs.",
    "The Korea Herald": "South Korean English-language newspaper founded in 1953, designated as the country's only English-language national daily, covering Korean and Asia-Pacific affairs.",
    "The Lens": "Nonprofit investigative newsroom founded in 2009 in New Orleans, covering criminal justice, government accountability, and coastal issues in Louisiana.",
    "The Lever (David Sirota)": "Investigative journalism newsletter founded in 2021 by journalist and former speechwriter David Sirota, covering corporate power, government corruption, and political money.",
    "The Maine Monitor": "Nonprofit newsroom founded in 2020 as a project of the Maine Center for Public Interest Reporting, covering state government, health, and environment in Maine.",
    "The Markup": "Nonprofit newsroom founded in 2018 by journalist Julia Angwin, investigating how technology and algorithms affect society, privacy, and public accountability.",
    "The Marshall Project": "Nonprofit newsroom founded in 2014 by Neil Barsky, covering the US criminal justice system, incarceration, policing, and immigration detention.",
    "The New Humanitarian": "Independent nonprofit news organization founded in 1995, originally part of the UN, covering humanitarian crises, refugees, conflict, and disaster response worldwide.",
    "The Plug": "Digital publication founded in 2017, covering Black entrepreneurship, venture capital, technology startups, and economic opportunity in the Black business community.",
    "The Root": "Online magazine founded in 2008 by Henry Louis Gates Jr., now owned by G/O Media, covering news, politics, and culture for Black audiences.",
    "The Trace": "Nonprofit newsroom founded in 2015, covering gun violence, firearm policy, and the public health dimensions of gun ownership in the United States.",
    "The Verge": "Technology news outlet founded in 2011 by Vox Media, covering consumer electronics, science, internet culture, and the intersection of technology and society.",
    "The War Zone": "Military technology publication part of The Drive, covering weapons systems, defense industry developments, geopolitical military events, and aviation technology.",
    "The Weeds (Vox)": "Policy podcast produced by Vox Media, taking deep analytical dives into domestic policy debates, legislative mechanics, and the details behind political headlines.",
    "Times of India": "India's largest English-language daily newspaper by circulation, founded in 1838, owned by the Bennett Coleman family, covering national and international news.",
    "Urban Institute": "Nonpartisan research organization founded in 1968 by President Lyndon Johnson in Washington DC, studying social and economic policy including housing, taxes, and poverty.",
    "VTDigger": "Vermont nonprofit news organization founded in 2009 by journalist Anne Galloway, covering state government, environment, education, and investigative reporting.",
    "Voice of San Diego": "Nonprofit news organization founded in 2005, covering San Diego city government, housing, education, border policy, and community accountability journalism.",
    "Vox": "Explanatory news publication founded in 2014 by Ezra Klein, Matt Yglesias, and Melissa Bell, owned by Vox Media, covering policy, politics, and culture.",
    "Wall Street Journal": "Daily business newspaper founded in 1889, owned by News Corp through Dow Jones, the largest US newspaper by total circulation, covering finance and global affairs.",
    "War on the Rocks": "National security and foreign policy analysis platform founded in 2013, publishing expert commentary on military strategy, defense policy, and international security.",
    "Washington Examiner": "Daily news and opinion publication based in Washington DC, owned by Clarity Media Group and Philip Anschutz, covering politics, policy, and government.",
    "Washington Post": "Daily newspaper founded in 1877, purchased by Jeff Bezos in 2013, one of the largest US newspapers, covering national politics, government, and world affairs.",
    "Washington Times": "Daily newspaper founded in 1982 in Washington DC, originally funded by Unification Church founder Sun Myung Moon, covering national politics and world affairs.",
    "White House": "Official website of the Executive Office of the President of the United States, publishing presidential statements, executive orders, and administration policy documents.",
    "Wired": "Technology and culture magazine founded in 1993 in San Francisco, owned by Conde Nast, covering digital technology, science, business, and the future of innovation.",
    "Wisconsin Examiner": "Nonprofit newsroom part of the States Newsroom network, founded in 2019, covering Wisconsin state government, elections, and public policy from Madison.",
    "WyoFile": "Nonprofit news organization founded in 2009, covering Wyoming people, politics, public lands, energy development, and community issues from across the state.",
    "YES! Magazine": "Nonprofit media organization founded in 1996 by David Korten and Frances Moore Lappé, covering solutions journalism focused on sustainability, equity, and community action.",
    "Al-Monitor": "Independent news website founded in 2011 by Jamal Daniel, covering Middle East politics, policy, and society through regional correspondents and expert analysis.",
    "AllAfrica": "Pan-African digital media platform founded in 1996, aggregating and distributing news content from over 100 African newsrooms to a global English-language audience.",
    "Animal Politico": "Independent Mexican digital newsroom founded in 2010, covering government corruption, human rights, and accountability journalism across Mexico and Central America.",
    "Atlantic Council": "Nonpartisan think tank founded in 1961 in Washington DC, focused on international affairs, including transatlantic relations, NATO, cybersecurity, and global energy policy.",
    "Bhekisisa Health Journalism": "South African nonprofit health journalism center founded in 2013, covering public health, HIV/AIDS, pandemic preparedness, and healthcare policy across the African continent.",
    "Bulletin of the Atomic Scientists": "Nonprofit organization founded in 1945 by Manhattan Project scientists, publishing on nuclear risk, biosecurity, climate threats, and disruptive technologies through its Doomsday Clock.",
    "Center for Public Integrity": "Nonprofit investigative newsroom founded in 1989 by journalist Charles Lewis, covering money in politics, government accountability, and institutional power in Washington DC.",
    "Detroit Free Press": "Daily newspaper founded in 1831 in Detroit, owned by Gannett since 2019, covering Detroit, Michigan state affairs, the auto industry, and Midwest economic issues.",
    "FiveThirtyEight Politics": "Data-driven political analysis podcast originally founded by statistician Nate Silver in 2008, now operated by ABC News, covering elections, polling, and quantitative politics.",
    "Fix by Grist": "Solutions journalism section of Grist launched in 2021, covering climate solutions, clean energy innovations, and community-driven responses to environmental challenges.",
    "Folha de S.Paulo": "Brazil's largest-circulation newspaper, founded in 1921 in Sao Paulo, owned by the Frias family through Grupo Folha, known for investigative journalism and political coverage.",
    "Honolulu Star-Advertiser": "Hawaii's largest daily newspaper, formed in 2010 from a merger of the Honolulu Advertiser and Star-Bulletin, owned by Oahu Publications, covering Pacific and island issues.",
    "Indian Express": "Indian English-language daily newspaper founded in 1932, owned by the Indian Express Group, known for independent editorial positions and investigative reporting across India.",
    "Irish Times": "Ireland's newspaper of record, founded in 1859 in Dublin, owned by the Irish Times Trust since 1974, covering Irish politics, European affairs, and international news.",
    "Jakarta Post": "Indonesia's leading English-language daily newspaper, founded in 1983 in Jakarta, covering Southeast Asian politics, economics, culture, and Indonesia's democratic development.",
    "Michael Knowles Show": "Daily podcast produced by the Daily Wire and hosted by Michael Knowles, covering politics, culture, and religion through Catholic intellectual and cultural commentary.",
    "Middle East Eye": "London-based independent news website founded in 2014, covering Middle East and North African politics, conflict, and human rights through regional and international correspondents.",
    "NPR Politics Podcast": "NPR's political reporting podcast launched in 2015, covering elections, Congress, the White House, and American governance with analysis from NPR's political team.",
    "OpenSecrets": "Nonpartisan research organization formerly known as the Center for Responsive Politics, founded in 1983, tracking campaign finance, lobbying expenditures, and political spending data.",
    "Philadelphia Inquirer": "Daily newspaper founded in 1829, the third-oldest surviving daily in the United States, covering Philadelphia, Pennsylvania politics, and the Delaware Valley region.",
    "Politico Europe": "European edition of Politico launched in 2015 in Brussels through a partnership with Axel Springer, covering EU institutions, policy, and European governance.",
    "Premium Times Nigeria": "Nigerian investigative newspaper founded in 2011 by former NEXT editors, covering government accountability, corruption, and West African politics from Abuja.",
    "Reveal from The Center for Investigative Reporting": "Investigative newsroom founded in 1977, the oldest nonprofit investigative reporting organization in the United States, producing in-depth journalism on systemic failures and accountability.",
    "Tampa Bay Times": "Florida's largest newspaper by circulation, founded in 1884 in St. Petersburg, owned by the nonprofit Poynter Institute, known for Pulitzer Prize-winning investigative journalism.",
    "The Conversation": "Global nonprofit media network founded in 2011 in Melbourne, Australia, publishing research-based articles written by academics and edited by journalists for general audiences.",
    "The Daily NYT": "New York Times daily news podcast launched in 2017, hosted by Michael Barbaro, the most-listened-to news podcast in the US with four million daily listeners.",
    "The Oregonian": "Oregon's largest newspaper, founded in 1850 in Portland, owned by Advance Publications, covering Pacific Northwest politics, environment, and urban issues.",
    "The Wire": "Indian independent digital news platform founded in 2015, covering politics, governance, science, rights, and accountability journalism in the world's largest democracy.",
    "Undark": "Nonprofit science journalism magazine founded in 2016 at MIT's Knight Science Journalism program, covering the intersection of science, society, and public policy.",
    "Univision News": "News division of Univision, the largest Spanish-language broadcast network in the United States, founded in 1962, reaching millions of Hispanic and Latino viewers.",
    "VnExpress International": "English-language edition of VnExpress, Vietnam's most-read online newspaper owned by FPT Corporation, covering Vietnamese politics, economics, and society.",
    "Word on Fire": "Catholic media ministry founded in 2000 by Bishop Robert Barron, producing articles, videos, and commentary engaging faith, culture, and intellectual life.",
}

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_articles():
    if not ARTICLES_FILE.exists():
        print(f"ERROR: {ARTICLES_FILE} not found")
        return []
    with open(ARTICLES_FILE, "r") as f:
        data = json.load(f)
        return data.get("articles", [])


def load_daily_history(days=7):
    history = {}
    if not DAILY_DIR.exists():
        return history
    for daily_file in sorted(DAILY_DIR.glob("*.json")):
        if daily_file.name == "latest.json":
            continue
        try:
            with open(daily_file, "r") as f:
                data = json.load(f)
                date_str = data.get("date")
                if date_str:
                    history[date_str] = data
        except (json.JSONDecodeError, IOError):
            pass
    return history


# ---------------------------------------------------------------------------
# TEXT ANALYSIS UTILITIES
# ---------------------------------------------------------------------------

def extract_keywords(text, min_len=5, top_n=20):
    """Extract the most frequent meaningful words from text."""
    stop = {'about','after','again','against','along','already','among',
            'another','around','based','because','before','being','between',
            'could','during','every','first','found','going','group',
            'house','including','known','large','later','least','level',
            'likely','major','making','might','never','number','often',
            'other','party','place','point','press','program','public',
            'really','since','small','something','still','system',
            'their','there','these','thing','think','those','three',
            'through','times','today','under','united','until',
            'using','watch','where','which','while','world','would',
            'years','state','states','house','report','officials',
            'according','tuesday','wednesday','thursday','friday',
            'saturday','sunday','monday','march','april','reuters',
            'associated','update','watch','people','trump','says',
            'president','could','should','would'}
    words = re.findall(r'[a-z]{%d,}' % min_len, text.lower())
    filtered = [w for w in words if w not in stop]
    return [w for w, _ in Counter(filtered).most_common(top_n)]


def normalize_force_tag(tag: str) -> str:
    """Normalize force tags for grouping (lowercase, strip whitespace)."""
    return tag.lower().strip().rstrip(".")


def compute_force_similarity(tag1: str, tag2: str) -> float:
    """
    Compute similarity between two force tags using word overlap.
    Returns 0-1 score.
    """
    words1 = set(tag1.lower().split())
    words2 = set(tag2.lower().split())
    if not words1 or not words2:
        return 0
    # Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    return intersection / union if union > 0 else 0


# ---------------------------------------------------------------------------
# STRUCTURAL FORCE CLUSTERING
# ---------------------------------------------------------------------------

def cluster_by_structural_force(articles):
    """
    Cluster articles by structural force — the underlying pattern driving the story.

    This is fundamentally different from keyword clustering. Two articles might
    share zero keywords but be driven by the same force:
    - "Tariffs on Chinese EVs" (economics + geopolitics)
    - "Auto workers fear plant closures" (labor + economics)
    Both are driven by "trade policy reshaping labor markets."

    Strategy:
    1. Group articles with identical or near-identical force_tags
    2. Then merge groups whose force_tags are semantically similar
    3. Fall back to domain-pair + keyword clustering for articles without force_tags
    """
    # Separate AI-tagged from keyword-only
    ai_articles = [a for a in articles if a.get("force_tag") and a.get("domains")]
    keyword_articles = [a for a in articles if not a.get("force_tag") and a.get("domains")]

    # Step 1: Group by normalized force tag
    force_groups = defaultdict(list)
    for a in ai_articles:
        tag = normalize_force_tag(a["force_tag"])
        force_groups[tag].append(a)

    # Step 2: Merge similar force tags (e.g., "military escalation" and "regional military escalation")
    merged_groups = []
    used_tags = set()
    tag_list = sorted(force_groups.keys(), key=lambda t: len(force_groups[t]), reverse=True)

    for tag in tag_list:
        if tag in used_tags:
            continue
        group = list(force_groups[tag])
        used_tags.add(tag)

        # Find similar tags to merge
        for other_tag in tag_list:
            if other_tag in used_tags:
                continue
            sim = compute_force_similarity(tag, other_tag)
            if sim >= 0.4:  # 40% word overlap = same structural force
                group.extend(force_groups[other_tag])
                used_tags.add(other_tag)

        if len(group) >= 2:  # Need at least 2 articles to form a cluster
            merged_groups.append(group)

    # Step 3: For keyword-only articles, try to assign them to existing force clusters
    # based on domain overlap + keyword similarity
    for a in keyword_articles:
        best_group = None
        best_score = 0
        a_domains = set(a.get("domains", []))
        a_keywords = set(extract_keywords(a.get("title", "") + " " + a.get("summary", "")[:200], min_len=4, top_n=10))

        for group in merged_groups:
            # Check domain overlap
            group_domains = set()
            group_keywords = set()
            for ga in group[:5]:  # Sample first 5
                group_domains.update(ga.get("domains", []))
                group_keywords.update(extract_keywords(ga.get("title", ""), min_len=4, top_n=5))

            domain_overlap = len(a_domains & group_domains) / max(len(a_domains | group_domains), 1)
            keyword_overlap = len(a_keywords & group_keywords) / max(len(a_keywords | group_keywords), 1)
            score = domain_overlap * 0.6 + keyword_overlap * 0.4

            if score > best_score and score >= 0.3:
                best_score = score
                best_group = group

        if best_group is not None:
            best_group.append(a)

    return merged_groups


def score_force_cluster(cluster):
    """
    Score a structural force cluster for significance.

    Factors:
    - Source diversity (more unique sources = more significant)
    - Domain breadth (touches more domains = more structurally important)
    - Tier diversity (covered by national + local-regional + intl = broader relevance)
    - AI connection quality (articles with connection insights are richer)
    """
    sources = set(a["source"] for a in cluster)
    domains = set()
    tiers = set()
    has_connection = 0

    for a in cluster:
        for d in a.get("domains", []):
            domains.add(d)
        tier = a.get("tier", "")
        if tier in ("local-regional", "lived"):
            tiers.add("local-regional")
        elif tier in ("specialist", "domain"):
            tiers.add("specialist")
        else:
            tiers.add(tier)
        if a.get("connection"):
            has_connection += 1

    source_score = len(sources)
    domain_score = len(domains) * 2  # domain breadth matters most
    tier_score = len(tiers)
    connection_bonus = min(has_connection, 5)  # cap the bonus

    return source_score * domain_score + tier_score * 3 + connection_bonus


# ---------------------------------------------------------------------------
# CORE ANALYSIS FUNCTIONS
# ---------------------------------------------------------------------------

def analyze_top_stories(articles):
    """
    Cluster articles by structural force, then for each force produce:
    - The structural force at work
    - A factual headline from the most representative article
    - How many sources from how many tiers cover it
    - How framing differs across tiers
    - What domains it touches
    - AI-generated connection insights
    """
    domain_labels = get_domain_labels()

    # Only cluster articles that have BOTH domain tags AND force_tags (AI-classified)
    # This prevents unclassified articles from creating junk clusters
    classified_articles = [a for a in articles if a.get("domains") and a.get("force_tag")]
    clusters = cluster_by_structural_force(classified_articles)

    # Score and sort
    clusters.sort(key=score_force_cluster, reverse=True)

    stories = []
    for cluster in clusters[:10]:  # Top 10 structural forces
        sources = list(set(a["source"] for a in cluster))
        tiers = list(set(
            ("local-regional" if a.get("tier") in ("local-regional", "lived") else
             "specialist" if a.get("tier") in ("specialist", "domain") else
             a.get("tier", "unknown"))
            for a in cluster
        ))

        # Domains this force touches
        all_domains = Counter()
        for a in cluster:
            for d in a.get("domains", []):
                all_domains[d] += 1
        top_domains = [domain_labels.get(d, d) for d, _ in all_domains.most_common(4)]

        # Extract the structural force label
        force_tags = Counter(normalize_force_tag(a.get("force_tag", "")) for a in cluster if a.get("force_tag"))
        primary_force = force_tags.most_common(1)[0][0] if force_tags else ""

        # All force tags in this cluster (shows the breadth)
        all_forces = [tag for tag, _ in force_tags.most_common(5) if tag]

        # Sort articles: prefer those with connection insights, then by tier
        tier_order = {"national": 0, "international": 1, "local-regional": 2,
                      "specialist": 3, "explainer": 4, "analysis": 5}
        sorted_arts = sorted(cluster,
                             key=lambda a: (0 if a.get("connection") else 1,
                                           tier_order.get(a.get("tier", ""), 9)))

        # Headline = best connection insight (explanatory), NOT an article title
        # If we have a connection insight, use it. Otherwise synthesize from force + domains.
        best_conn = next((a.get("connection", "") for a in sorted_arts if a.get("connection")), "")
        if best_conn:
            lead_title = best_conn
        else:
            # Synthesize: "Force at the intersection of Domain1 and Domain2"
            lead_title = f"{primary_force.title()} across {', '.join(top_domains[:3])}" if primary_force else sorted_arts[0]["title"] if sorted_arts else ""

        # Collect connection insights (the gold)
        connections = []
        seen_connections = set()
        for a in cluster:
            conn = a.get("connection", "")
            if conn and conn not in seen_connections:
                connections.append({
                    "text": conn,
                    "source": a["source"],
                    "title": a["title"][:80],
                    "domains": a.get("domains", []),
                    "context": SOURCE_CONTEXT.get(a["source"], ""),
                })
                seen_connections.add(conn)

        # How different tiers frame it
        tier_framing = {}
        for tier_name in ["national", "international", "local-regional", "specialist", "analysis"]:
            tier_arts = [a for a in cluster
                         if a.get("tier") == tier_name or
                         (tier_name == "local-regional" and a.get("tier") in ("local-regional", "lived")) or
                         (tier_name == "specialist" and a.get("tier") in ("specialist", "domain"))]
            if not tier_arts:
                continue
            tier_titles = " ".join(a["title"] for a in tier_arts)
            tier_kw = extract_keywords(tier_titles, min_len=4, top_n=8)
            sample = tier_arts[0]
            tier_framing[tier_name] = {
                "count": len(tier_arts),
                "keywords": tier_kw[:5],
                "sample": {
                    "title": sample["title"][:120],
                    "source": sample["source"],
                    "url": sample.get("url", ""),
                    "context": SOURCE_CONTEXT.get(sample["source"], ""),
                },
            }

        # Sample articles (one per source, max 6)
        seen_sources = set()
        sample_articles = []
        for a in sorted_arts:
            if a["source"] not in seen_sources and len(sample_articles) < 6:
                seen_sources.add(a["source"])
                sample_articles.append({
                    "title": a["title"][:120],
                    "source": a["source"],
                    "url": a.get("url", ""),
                    "tier": a.get("tier", ""),
                    "paywall": a.get("paywall", False),
                    "context": SOURCE_CONTEXT.get(a["source"], ""),
                    "connection": a.get("connection", ""),
                    "force_tag": a.get("force_tag", ""),
                })

        stories.append({
            "headline": lead_title,
            "structural_force": primary_force,
            "all_forces": all_forces,
            "source_count": len(sources),
            "tier_count": len(tiers),
            "tiers": tiers,
            "domains": top_domains,
            "domain_keys": [d for d, _ in all_domains.most_common(4)],
            "article_count": len(cluster),
            "connections": connections[:5],  # Top 5 connection insights
            "tier_framing": tier_framing,
            "articles": sample_articles,
        })

    return stories


def analyze_what_connects(articles):
    """
    Find stories where sources from across the political/demographic spectrum
    converge on the same structural force.
    """
    LEFT = {'New York Times', 'Washington Post', 'NPR', 'CNN', 'The Atlantic',
            'NBC News', 'ABC News', 'Vox', 'American Prospect', 'The Intercept',
            'Prism', 'Mother Jones', 'Center for American Progress',
            'Roosevelt Institute', 'Brookings'}
    RIGHT = {'Fox News', 'National Review', 'Washington Examiner', 'Washington Times',
             'Daily Wire', 'The Dispatch', 'Reason', 'RealClearPolitics',
             'The Federalist', 'Newsmax', 'The Blaze', 'Breitbart',
             'Heritage Foundation', 'American Enterprise Institute',
             'Hoover Institution', 'Hudson Institute', 'Cato Institute'}
    INTL = {'BBC World', 'The Guardian World', 'Al Jazeera', 'Deutsche Welle',
            'France 24', 'South China Morning Post', 'The Hindu', 'NHK World',
            'ABC Australia', 'Rappler', 'Meduza', 'Times of India', 'Straits Times',
            'Haaretz', 'Dawn', 'The Korea Herald', 'Bangkok Post', 'Taipei Times',
            'Channel News Asia', 'Daily Maverick', 'Jamaica Observer',
            'The Japan Times', 'Anadolu Agency', 'Global Voices',
            'The New Humanitarian', 'Scroll.in', 'Balkan Insight', 'Nikkei Asia',
            'The East African', 'The Globe and Mail', 'Press Gazette'}

    clusters = cluster_by_structural_force(articles)
    bridging = []

    for cluster in clusters:
        left = set(); right = set(); intl = set(); local_regional = set()
        for a in cluster:
            src = a["source"]
            if src in LEFT: left.add(src)
            elif src in RIGHT: right.add(src)
            elif src in INTL: intl.add(src)
            elif a.get("tier") in ("local-regional", "lived"): local_regional.add(src)

        segments = sum(1 for g in [left, right, intl, local_regional] if g)
        if segments >= 2 and len(left | right | intl | local_regional) >= 4:
            # Get the structural force
            force_tags = Counter(normalize_force_tag(a.get("force_tag", ""))
                               for a in cluster if a.get("force_tag"))
            primary_force = force_tags.most_common(1)[0][0] if force_tags else ""

            lead = sorted(cluster, key=lambda a: (0 if a.get("connection") else 1))[0]
            bridging.append({
                "headline": lead["title"][:120],
                "structural_force": primary_force,
                "total_sources": len(set(a["source"] for a in cluster)),
                "spectrum_segments": segments,
                "left_sources": list(left)[:3],
                "right_sources": list(right)[:3],
                "international_sources": list(intl)[:3],
                "local_regional_sources": list(local_regional)[:3],
                "article_count": len(cluster),
                "domains": [d for d, _ in Counter(
                    d for a in cluster for d in a.get("domains", [])
                ).most_common(3)],
                "sample_connection": lead.get("connection", ""),
            })

    bridging.sort(key=lambda x: (x["spectrum_segments"], x["total_sources"]),
                  reverse=True)
    return bridging[:8]


def analyze_structural_forces_map(articles):
    """
    Build a map of ALL structural forces detected today and how they relate.
    This is the high-level "what's actually happening" view.

    Groups individual force_tags into force families, counts how many articles
    and domains each force family touches, and identifies which forces are
    connected (share articles or domains).
    """
    domain_labels = get_domain_labels()

    # Collect all force tags with their articles
    force_articles = defaultdict(list)
    for a in articles:
        tag = a.get("force_tag", "")
        if tag and a.get("domains"):
            force_articles[normalize_force_tag(tag)].append(a)

    # Build force families by merging similar tags
    families = []
    used = set()
    sorted_tags = sorted(force_articles.keys(), key=lambda t: len(force_articles[t]), reverse=True)

    for tag in sorted_tags:
        if tag in used:
            continue
        family_articles = list(force_articles[tag])
        family_tags = [tag]
        used.add(tag)

        for other in sorted_tags:
            if other in used:
                continue
            if compute_force_similarity(tag, other) >= 0.35:
                family_articles.extend(force_articles[other])
                family_tags.append(other)
                used.add(other)

        if len(family_articles) >= 2:
            domains = set()
            for a in family_articles:
                for d in a.get("domains", []):
                    domains.add(d)

            families.append({
                "force": tag,
                "related_forces": family_tags[1:] if len(family_tags) > 1 else [],
                "article_count": len(family_articles),
                "source_count": len(set(a["source"] for a in family_articles)),
                "domains": [domain_labels.get(d, d) for d in sorted(domains)],
                "domain_keys": sorted(domains),
                "sample_title": family_articles[0]["title"][:100],
            })

    families.sort(key=lambda f: f["article_count"] * len(f["domain_keys"]), reverse=True)
    return families[:25]


def analyze_cooperation_stories(articles):
    """
    The Seventh Question: Where are people being decent, and why is that
    not the headline?

    This surfaces articles where the AI classification detected cooperation,
    mutual aid, community response, institutional integrity, or cross-group
    solidarity. These are the stories the current information architecture
    is structurally incapable of conveying.

    Groups cooperation stories by type and connects them to the structural
    forces they exist within, because cooperation doesn't happen in a vacuum.
    It happens in response to pressure, inside crisis, alongside conflict.
    The darkness is real and the goodness is real and Signal Board shows both.
    """
    domain_labels = get_domain_labels()

    # Filter to articles with cooperation signals
    coop_articles = [a for a in articles if a.get("cooperation")]

    if not coop_articles:
        return {
            "total_cooperation_stories": 0,
            "cooperation_rate": 0,
            "by_type": [],
            "by_force": [],
            "highlights": [],
            "coverage_gap": [],
        }

    total = len(articles)
    coop_count = len(coop_articles)
    coop_rate = round(coop_count / max(total, 1) * 100)

    # Group by cooperation type
    type_groups = defaultdict(list)
    for a in coop_articles:
        ctype = a.get("cooperation_type", "unspecified").strip().lower()
        if ctype:
            type_groups[ctype].append(a)

    by_type = []
    for ctype, arts in sorted(type_groups.items(), key=lambda x: len(x[1]), reverse=True):
        sources = list(set(a["source"] for a in arts))
        domains = Counter()
        for a in arts:
            for d in a.get("domains", []):
                domains[d] += 1

        by_type.append({
            "type": ctype,
            "count": len(arts),
            "sources": sources[:5],
            "domains": [domain_labels.get(d, d) for d, _ in domains.most_common(3)],
            "sample": {
                "title": arts[0]["title"][:120],
                "source": arts[0]["source"],
                "url": arts[0].get("url", ""),
                "connection": arts[0].get("connection", ""),
            },
        })

    # Group by structural force (cooperation within crisis)
    force_coop = defaultdict(list)
    for a in coop_articles:
        tag = a.get("force_tag", "")
        if tag:
            force_coop[normalize_force_tag(tag)].append(a)

    by_force = []
    for force, arts in sorted(force_coop.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
        coop_types = list(set(a.get("cooperation_type", "") for a in arts if a.get("cooperation_type")))
        by_force.append({
            "force": force,
            "cooperation_count": len(arts),
            "cooperation_types": coop_types[:3],
            "sample_title": arts[0]["title"][:120],
            "sample_source": arts[0]["source"],
        })

    # Highlight stories: cooperation stories from tiers that typically
    # get less attention (local-regional, specialist, solutions)
    highlights = []
    highlight_tiers = {"local-regional", "specialist", "solutions"}
    for a in coop_articles:
        tier = a.get("tier", "")
        if tier in highlight_tiers or any(alias == tier for alias in ["lived", "domain"]):
            highlights.append({
                "title": a["title"][:120],
                "source": a["source"],
                "url": a.get("url", ""),
                "tier": tier,
                "cooperation_type": a.get("cooperation_type", ""),
                "force_tag": a.get("force_tag", ""),
                "connection": a.get("connection", ""),
                "context": SOURCE_CONTEXT.get(a["source"], ""),
            })

    # Coverage gap: forces with MANY articles but ZERO cooperation signals
    # These are the places where the architecture might be hiding goodness
    force_total = defaultdict(int)
    force_coop_count = defaultdict(int)
    for a in articles:
        tag = a.get("force_tag", "")
        if tag:
            nt = normalize_force_tag(tag)
            force_total[nt] += 1
            if a.get("cooperation"):
                force_coop_count[nt] += 1

    coverage_gap = []
    for force, total_count in sorted(force_total.items(), key=lambda x: x[1], reverse=True):
        if total_count >= 5 and force_coop_count.get(force, 0) == 0:
            coverage_gap.append({
                "force": force,
                "article_count": total_count,
                "note": "No cooperation signals detected. Is goodness happening here that the coverage isn't showing?",
            })

    return {
        "total_cooperation_stories": coop_count,
        "cooperation_rate": coop_rate,
        "by_type": by_type[:10],
        "by_force": by_force,
        "highlights": highlights[:8],
        "coverage_gap": coverage_gap[:5],
    }


def analyze_local_regional_exclusive(articles):
    """
    Find stories that local-regional/specialist sources cover but national
    outlets do not. These are the gaps in mainstream coverage.
    """
    national_keywords = set()
    for a in articles:
        if a.get("tier") == "national":
            for w in re.findall(r'[a-z]{6,}', a.get("title", "").lower()):
                national_keywords.add(w)

    local_regional_stories = []
    for a in articles:
        if a.get("tier") not in ("local-regional", "lived", "specialist", "domain"):
            continue
        title_words = set(re.findall(r'[a-z]{6,}', a.get("title", "").lower()))
        if not title_words:
            continue
        overlap = len(title_words & national_keywords) / len(title_words)
        if overlap < 0.35:
            text = a.get("text", "") or a.get("summary", "")
            local_regional_stories.append({
                "title": a["title"][:120],
                "source": a["source"],
                "url": a.get("url", ""),
                "tier": a.get("tier", ""),
                "text_preview": text[:250] if text else "",
                "domains": a.get("domains", []),
                "connection": a.get("connection", ""),
                "force_tag": a.get("force_tag", ""),
                "context": SOURCE_CONTEXT.get(a["source"], ""),
            })

    seen = set()
    unique = []
    for s in local_regional_stories:
        if s["source"] not in seen:
            seen.add(s["source"])
            unique.append(s)

    return unique[:12]


def analyze_domain_collisions(articles, history):
    """
    Track which domain pairs are most active and whether they're
    rising or falling vs. the 7-day average. Now enriched with
    AI connection insights.
    """
    domain_labels = get_domain_labels()

    pair_today = defaultdict(int)
    pair_articles = defaultdict(list)
    pair_connections = defaultdict(list)

    for a in articles:
        doms = sorted(a.get("domains", []))
        for i in range(len(doms)):
            for j in range(i + 1, len(doms)):
                pair = (doms[i], doms[j])
                pair_today[pair] += 1
                if len(pair_articles[pair]) < 3:
                    pair_articles[pair].append({
                        "title": a["title"][:80],
                        "source": a["source"],
                        "url": a.get("url", ""),
                    })
                conn = a.get("connection", "")
                if conn and len(pair_connections[pair]) < 2:
                    pair_connections[pair].append(conn)

    # Rolling average from history
    pair_avg = defaultdict(float)
    hist_dates = sorted(history.keys())[-6:]
    if hist_dates:
        for date_key in hist_dates:
            for thread in history[date_key].get("active_threads", []):
                pair = thread.get("pair")
                if pair and isinstance(pair, list):
                    key = tuple(sorted(pair))
                    pair_avg[key] += thread.get("today_count", 0)
        for p in pair_avg:
            pair_avg[p] /= len(hist_dates)

    # Domain pair explanations
    PAIR_EXPLANATIONS = {
        'ai+climate': 'AI development and its energy costs or climate applications',
        'ai+economics': 'AI affecting markets, investment, and business models',
        'ai+governance': 'Government efforts to regulate or deploy AI',
        'ai+information': 'AI changing how information is produced and consumed',
        'ai+labor': 'AI and automation changing jobs and wages',
        'ai+legal': 'Courts and lawmakers addressing AI liability and rights',
        'ai+security': 'AI as military tool or national security concern',
        'climate+economics': 'Energy costs, food prices, and insurance rates linked to environmental change',
        'climate+domestic_politics': 'Environmental policy as a political issue',
        'climate+governance': 'Environmental regulation and climate policy implementation',
        'climate+labor': 'Energy transition affecting workers and communities',
        'climate+legal': 'Environmental lawsuits and climate litigation',
        'climate+security': 'Environmental change creating security challenges',
        'domestic_politics+economics': 'Economic conditions shaping political debate',
        'domestic_politics+governance': 'Political conflict over how government agencies operate',
        'domestic_politics+information': 'How political information reaches voters',
        'domestic_politics+legal': 'Political disputes reaching the courts',
        'domestic_politics+security': 'Defense and public safety as political issues',
        'economics+geopolitics': 'Trade, sanctions, and global economic competition',
        'economics+governance': 'Tax policy, trade agreements, and government spending',
        'economics+labor': 'Jobs, wages, and whether economic growth reaches workers',
        'economics+legal': 'Antitrust enforcement, financial regulation, and corporate law',
        'economics+security': 'Military spending and conflict affecting markets',
        'geopolitics+governance': 'International diplomacy and alliance management',
        'geopolitics+legal': 'International law, treaties, and war crimes',
        'geopolitics+security': 'Military tensions between nations',
        'governance+information': 'Government regulation of media and information platforms',
        'governance+labor': 'Workplace regulation and labor law enforcement',
        'governance+legal': 'Government actions challenged or upheld in courts',
        'governance+security': 'Defense policy and military strategy',
        'information+legal': 'Free speech, media law, and platform regulation',
        'labor+legal': 'Employment law, worker rights cases, and workplace litigation',
    }

    threads = []
    for pair, count in sorted(pair_today.items(), key=lambda x: x[1], reverse=True):
        d1, d2 = pair
        pair_key = "+".join(sorted([d1, d2]))
        explanation = PAIR_EXPLANATIONS.get(pair_key,
            f"{domain_labels.get(d1, d1)} and {domain_labels.get(d2, d2)}")

        avg = pair_avg.get(pair, 0)
        if avg == 0:
            trend = "new" if count > 0 else "stable"
        elif count > avg * 1.25:
            trend = "rising"
        elif count < avg * 0.75:
            trend = "falling"
        else:
            trend = "stable"

        threads.append({
            "pair": list(pair),
            "label": f"{domain_labels.get(d1, d1)} + {domain_labels.get(d2, d2)}",
            "explanation": explanation,
            "today_count": count,
            "trend": trend,
            "sample_articles": pair_articles[pair],
            "ai_connections": pair_connections.get(pair, []),
        })

    return threads[:15]


def analyze_source_spectrum(articles):
    """Count articles by source tier — all tiers, no gaps."""
    from collections import Counter
    tier_counts = Counter(a.get("tier", "unknown") for a in articles)
    # Merge legacy aliases
    if "domain" in tier_counts:
        tier_counts["specialist"] += tier_counts.pop("domain")
    if "lived" in tier_counts:
        tier_counts["local-regional"] += tier_counts.pop("lived")
    # Drop unknowns
    tier_counts.pop("unknown", None)
    tier_counts.pop("", None)
    return dict(tier_counts.most_common())


def generate_questions_people_are_asking(articles):
    """
    Based on the structural forces and domain collisions, generate
    the questions regular people would likely have.
    """
    domain_labels = get_domain_labels()

    pair_counts = Counter()
    for a in articles:
        doms = sorted(a.get("domains", []))
        for i in range(len(doms)):
            for j in range(i + 1, len(doms)):
                pair_counts[(doms[i], doms[j])] += 1

    PAIR_QUESTIONS = {
        'economics+security': "How is the conflict affecting prices and the economy?",
        'domestic_politics+governance': "What is the government actually doing right now?",
        'domestic_politics+legal': "What legal challenges are being filed, and what do they mean?",
        'domestic_politics+security': "How are defense and security decisions being shaped by politics?",
        'governance+legal': "Which government actions are being challenged in court?",
        'climate+economics': "How are energy and environmental changes affecting costs?",
        'climate+security': "How is environmental change creating security risks?",
        'ai+labor': "How is automation changing the job market?",
        'economics+labor': "Are wages keeping up with costs?",
        'geopolitics+security': "What is the current state of international military tensions?",
        'domestic_politics+information': "How is political information reaching voters differently?",
        'governance+security': "What military and defense policy decisions are being made?",
        'ai+economics': "How is AI affecting markets and investment?",
        'economics+geopolitics': "How are trade and global power shifts affecting the US economy?",
        'ai+information': "How is AI changing what information you see and trust?",
        'governance+information': "How is the government shaping what information reaches you?",
        'ai+governance': "How are governments trying to regulate AI, and is it working?",
        'labor+economics': "Are workers benefiting from economic growth?",
    }

    questions = []
    for (d1, d2), count in pair_counts.most_common(12):
        pair_key = "+".join(sorted([d1, d2]))
        q = PAIR_QUESTIONS.get(pair_key)
        if q and count >= 2:
            relevant = [a for a in articles
                        if d1 in a.get("domains", []) and d2 in a.get("domains", [])]
            source_tiers = defaultdict(list)
            for a in relevant[:10]:
                tier = a.get("tier", "")
                if tier in ("local-regional", "lived"): tier = "local-regional"
                if tier in ("specialist", "domain"): tier = "specialist"
                if a["source"] not in [s["source"] for s in source_tiers[tier]]:
                    source_tiers[tier].append({
                        "source": a["source"],
                        "title": a["title"][:100],
                        "url": a.get("url", ""),
                        "context": SOURCE_CONTEXT.get(a["source"], ""),
                        "connection": a.get("connection", ""),
                    })

            # Get AI connection insights for this pair
            pair_connections = [a.get("connection", "") for a in relevant if a.get("connection")]

            questions.append({
                "question": q,
                "article_count": count,
                "domains": [domain_labels.get(d1, d1), domain_labels.get(d2, d2)],
                "sources_by_tier": {k: v[:2] for k, v in source_tiers.items()},
                "ai_insights": pair_connections[:3],
            })

    return questions[:8]


# ---------------------------------------------------------------------------
# MAIN ANALYSIS
# ---------------------------------------------------------------------------

def build_temporal_context(today_articles, analysis_date):
    """
    Compare today's data to yesterday's to surface what's shifting,
    surging, or emerging. This gives readers temporal orientation —
    'geopolitics coverage nearly tripled today' is more meaningful
    than a raw number.
    """
    from datetime import timedelta
    domain_labels = get_domain_labels()

    # Load all articles to find yesterday
    all_articles = load_articles()
    try:
        today_dt = datetime.strptime(analysis_date, "%Y-%m-%d")
        yesterday_str = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        return {}

    yesterday_articles = [a for a in all_articles if a.get("date") == yesterday_str]
    if not yesterday_articles:
        return {"has_yesterday": False}

    # Domain comparison
    y_domains = Counter()
    t_domains = Counter()
    for a in yesterday_articles:
        for d in (a.get("domains") or []):
            y_domains[d] += 1
    for a in today_articles:
        for d in (a.get("domains") or []):
            t_domains[d] += 1

    domain_shifts = []
    for key in set(list(y_domains.keys()) + list(t_domains.keys())):
        y_count = y_domains.get(key, 0)
        t_count = t_domains.get(key, 0)
        if y_count == 0:
            change_pct = 100
        else:
            change_pct = round((t_count - y_count) / y_count * 100)
        label = domain_labels.get(key, key)
        domain_shifts.append({
            "domain": key,
            "label": label,
            "yesterday": y_count,
            "today": t_count,
            "change_pct": change_pct,
        })

    # Sort by absolute change magnitude
    domain_shifts.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    # Volume change
    y_total = len(yesterday_articles)
    t_total = len(today_articles)
    volume_change_pct = round((t_total - y_total) / max(y_total, 1) * 100)

    # Biggest surges and drops (top 3 each)
    surges = [d for d in domain_shifts if d["change_pct"] > 20][:3]
    drops = [d for d in domain_shifts if d["change_pct"] < -20][:3]

    # ── Force tag comparison (requires AI classification on both days) ──
    y_forces = Counter(a.get("force_tag", "") for a in yesterday_articles if a.get("force_tag"))
    t_forces = Counter(a.get("force_tag", "") for a in today_articles if a.get("force_tag"))

    # Cluster similar force tags using same similarity as main analysis
    y_force_clusters = cluster_by_structural_force(
        [a for a in yesterday_articles if a.get("force_tag")]
    )
    t_force_clusters = cluster_by_structural_force(
        [a for a in today_articles if a.get("force_tag")]
    )

    # cluster_by_structural_force returns list of lists — convert to dict
    # keyed by the most common force_tag in each cluster
    def clusters_to_dict(cluster_list):
        result = {}
        for group in cluster_list:
            tags = Counter(a.get("force_tag", "") for a in group if a.get("force_tag"))
            label = tags.most_common(1)[0][0] if tags else "unknown"
            label = normalize_force_tag(label)
            result[label] = group
        return result

    y_force_dict = clusters_to_dict(y_force_clusters)
    t_force_dict = clusters_to_dict(t_force_clusters)

    # Build named cluster summaries for comparison
    def summarize_clusters(clusters_dict):
        result = {}
        for label, arts in clusters_dict.items():
            dom_counts = Counter()
            for a in arts:
                for d in (a.get("domains") or []):
                    dom_counts[d] += 1
            top_domains = [d for d, _ in dom_counts.most_common(3)]
            conns = [a.get("connection", "") for a in arts if a.get("connection")]
            result[label] = {
                "count": len(arts),
                "domains": top_domains,
                "sample_insight": conns[0] if conns else "",
            }
        return result

    y_cluster_summary = summarize_clusters(y_force_dict)
    t_cluster_summary = summarize_clusters(t_force_dict)

    # Persisting forces (appeared both days) and new forces (only today)
    shared_forces = set(y_cluster_summary.keys()) & set(t_cluster_summary.keys())
    persisting = []
    for f in shared_forces:
        persisting.append({
            "force": f,
            "yesterday_count": y_cluster_summary[f]["count"],
            "today_count": t_cluster_summary[f]["count"],
            "domains": t_cluster_summary[f]["domains"],
            "insight": t_cluster_summary[f]["sample_insight"],
        })
    persisting.sort(key=lambda x: x["today_count"], reverse=True)

    new_forces = []
    for f in set(t_cluster_summary.keys()) - shared_forces:
        if t_cluster_summary[f]["count"] >= 3:  # only meaningful clusters
            new_forces.append({
                "force": f,
                "count": t_cluster_summary[f]["count"],
                "domains": t_cluster_summary[f]["domains"],
                "insight": t_cluster_summary[f]["sample_insight"],
            })
    new_forces.sort(key=lambda x: x["count"], reverse=True)

    faded_forces = []
    for f in set(y_cluster_summary.keys()) - set(t_cluster_summary.keys()):
        if y_cluster_summary[f]["count"] >= 3:
            faded_forces.append({
                "force": f,
                "count": y_cluster_summary[f]["count"],
                "domains": y_cluster_summary[f]["domains"],
            })
    faded_forces.sort(key=lambda x: x["count"], reverse=True)

    return {
        "has_yesterday": True,
        "yesterday_date": yesterday_str,
        "yesterday_total": y_total,
        "today_total": t_total,
        "volume_change_pct": volume_change_pct,
        "domain_shifts": domain_shifts,
        "surges": surges,
        "drops": drops,
        "persisting_forces": persisting[:8],
        "new_forces": new_forces[:8],
        "faded_forces": faded_forces[:5],
        "yesterday_classified": sum(1 for a in yesterday_articles if a.get("force_tag")),
        "today_classified": sum(1 for a in today_articles if a.get("force_tag")),
    }


def generate_daily_analysis(articles, analysis_date, history):
    domain_labels = get_domain_labels()
    unique_sources = set(a.get("source") for a in articles)
    cross_domain = sum(1 for a in articles if a.get("cross_domain", False))
    ai_classified = sum(1 for a in articles if a.get("force_tag"))
    has_connection = sum(1 for a in articles if a.get("connection"))

    dom_counts = Counter()
    for a in articles:
        for d in a.get("domains", []):
            dom_counts[d] += 1

    top_domain = ""
    if dom_counts:
        top_key = dom_counts.most_common(1)[0][0]
        top_domain = domain_labels.get(top_key, top_key)

    # Run all analysis components
    top_stories = analyze_top_stories(articles)
    structural_forces = analyze_structural_forces_map(articles)
    what_connects = analyze_what_connects(articles)
    cooperation = analyze_cooperation_stories(articles)
    local_regional_exclusive = analyze_local_regional_exclusive(articles)
    active_threads = analyze_domain_collisions(articles, history)
    source_spectrum = analyze_source_spectrum(articles)
    questions = generate_questions_people_are_asking(articles)

    # ── Temporal context: compare today vs yesterday ──
    temporal_context = build_temporal_context(articles, analysis_date)

    return {
        "date": analysis_date,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_stories": len(articles),
            "sources_reporting": len(unique_sources),
            "cross_domain": cross_domain,
            "cross_domain_pct": round(cross_domain / max(len(articles), 1) * 100),
            "ai_classified": ai_classified,
            "ai_classified_pct": round(ai_classified / max(len(articles), 1) * 100),
            "connection_insights": has_connection,
            "top_domain": top_domain,
            "domain_distribution": {
                domain_labels.get(d, d): count
                for d, count in dom_counts.most_common()
            },
        },
        "temporal_context": temporal_context,
        "top_stories": top_stories,
        "structural_forces": structural_forces,
        "what_connects": what_connects,
        "cooperation": cooperation,
        "local_regional_exclusive": local_regional_exclusive,
        "active_threads": active_threads,
        "source_spectrum": source_spectrum,
        "questions": questions,
        # Backward compat
        "narrative_divergence": [
            {
                "topic": s["domains"][0] + " + " + s["domains"][1] if len(s["domains"]) >= 2 else s["domains"][0] if s["domains"] else "",
                "theme": s["headline"],
                "source_count": s["source_count"],
                "structural_force": s.get("structural_force", ""),
                "articles": s["articles"],
            }
            for s in top_stories[:3]
        ],
    }


def print_summary(analysis):
    s = analysis["summary"]
    print("\n" + "=" * 60)
    print("  SIGNAL BOARD — DAILY STRUCTURAL ANALYSIS")
    print("=" * 60)
    print(f"Date:                  {analysis['date']}")
    print(f"Total stories:         {s['total_stories']}")
    print(f"Sources reporting:     {s['sources_reporting']}")
    print(f"AI classified:         {s['ai_classified']} ({s['ai_classified_pct']}%)")
    print(f"Connection insights:   {s['connection_insights']}")
    print(f"Cross-domain:          {s['cross_domain']} ({s['cross_domain_pct']}%)")
    print(f"Top domain:            {s['top_domain']}")

    if analysis.get("top_stories"):
        print(f"\n--- TOP STRUCTURAL FORCES ({len(analysis['top_stories'])} found) ---")
        for i, st in enumerate(analysis["top_stories"][:8], 1):
            force = st.get("structural_force", "")
            domains = ", ".join(st["domains"][:3])
            print(f"\n  {i}. [{force.upper()}]")
            print(f"     {st['headline'][:80]}")
            print(f"     {st['source_count']} sources | {st['article_count']} articles | {domains}")
            if st.get("connections"):
                print(f"     Insight: {st['connections'][0]['text']}")

    if analysis.get("structural_forces"):
        print(f"\n--- STRUCTURAL FORCES MAP ({len(analysis['structural_forces'])} forces) ---")
        for f in analysis["structural_forces"][:10]:
            print(f"  • {f['force']:40s}  {f['article_count']:3d} articles  {f['source_count']:2d} sources  [{', '.join(f['domains'][:3])}]")

    if analysis.get("what_connects"):
        print(f"\n--- BRIDGING STORIES ({len(analysis['what_connects'])} found) ---")
        for i, b in enumerate(analysis["what_connects"][:3], 1):
            print(f"  {i}. {b['headline'][:60]}")
            print(f"     Force: {b.get('structural_force', 'n/a')} | {b['spectrum_segments']}/4 segments | {b['total_sources']} sources")

    if analysis.get("cooperation"):
        coop = analysis["cooperation"]
        print(f"\n--- WHERE PEOPLE ARE BEING DECENT ({coop['total_cooperation_stories']} stories, {coop['cooperation_rate']}% of coverage) ---")
        for ct in coop.get("by_type", [])[:5]:
            print(f"  • {ct['type']:30s}  {ct['count']:3d} articles  [{', '.join(ct['domains'][:2])}]")
            print(f"    Example: {ct['sample']['title'][:70]}")
        if coop.get("coverage_gap"):
            print(f"\n  Coverage gaps (forces with no cooperation signals):")
            for gap in coop["coverage_gap"][:3]:
                print(f"    ? {gap['force']} ({gap['article_count']} articles)")

    if analysis.get("questions"):
        print(f"\n--- QUESTIONS PEOPLE ARE ASKING ---")
        for q in analysis["questions"][:5]:
            print(f"  ? {q['question']} ({q['article_count']} articles)")
            if q.get("ai_insights"):
                print(f"    → {q['ai_insights'][0]}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Signal Board daily analysis")
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
            analysis_date = args.date
        except ValueError:
            print(f"ERROR: Invalid date '{args.date}'")
            sys.exit(1)
    else:
        analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"Analyzing articles for {analysis_date}")

    all_articles = load_articles()
    if not all_articles:
        print("ERROR: No articles found.")
        sys.exit(1)

    history = load_daily_history(days=7)
    articles = [a for a in all_articles if a.get("date") == analysis_date]

    if not articles:
        print(f"WARNING: No articles for {analysis_date}, using all recent")
        articles = all_articles[:1500]

    analysis = generate_daily_analysis(articles, analysis_date, history)

    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    dated_file = DAILY_DIR / f"{analysis_date}.json"
    with open(dated_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"Wrote {dated_file}")

    latest_file = DAILY_DIR / "latest.json"
    with open(latest_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"Wrote {latest_file}")

    print_summary(analysis)


if __name__ == "__main__":
    main()
