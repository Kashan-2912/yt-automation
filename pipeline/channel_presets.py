"""Channel niches: system prompt + defaults for Groq script generation.

Each preset includes a topic_pool — a list of setting/situation ideas.
One is picked randomly per run if no --topic is provided, ensuring variety.

PRIMARY NICHE: Modern Football & Sports (2005–present)
Channel capitalises on FIFA Club World Cup 2025 (June–July) and global football buzz.
Content era: 2005 onwards ONLY. No Maradona, no 1980s/90s legends.
"""

from __future__ import annotations

from typing import TypedDict


class Variant(TypedDict, total=False):
    """One output variant — same images, different audio/subs/upload target."""
    lang: str
    label: str
    tts_voice: str
    caption_font: str
    caption_font_name: str
    yt_token_env: str
    min_words: int


class ChannelPreset(TypedDict, total=False):
    id: str
    label: str
    groq_system_hint: str
    segment_count: int
    topic_pool: list[str]
    niche_keywords: list[str]
    image_style_suffix: str
    image_negative_prompt: str
    language: str
    tts_voice: str
    caption_font: str
    caption_font_name: str
    min_words: int
    variants: list[Variant]
    topic_rotation: str
    yt_token_env: str
    extra_yt_token_envs: list[str]


PRESETS: dict[str, ChannelPreset] = {
    # ══════════════════════════════════════════════════════════════════
    # FIFA WORLD CUP 2026 — Live Coverage Shorts (English)
    # Topic is auto-selected daily from 2026/*.json data files.
    # Angles: recap, preview, standings, player spotlight, prediction.
    # ══════════════════════════════════════════════════════════════════
    "fifa_2026": {
        "id": "fifa_2026",
        "label": "FIFA World Cup 2026 Live Coverage Shorts (English)",
        "language": "en",
        "min_words": 110,
        "tts_voice": "en-US-GuyNeural",
        "caption_font": "BebasNeue-Regular.ttf",
        "caption_font_name": "Bebas Neue",
        "yt_token_env": "YT_REFRESH_TOKEN",
        "segment_count": 6,
        "topic_rotation": "fifa_2026",
        "topic_pool": [],   # not used — topic_rotation drives selection
        "niche_keywords": [
            "FIFA World Cup 2026", "World Cup 2026", "FIFA 2026",
            "World Cup results", "World Cup 2026 highlights", "FIFA 2026 facts",
            "World Cup preview", "World Cup standings",
        ],
        "groq_system_hint": (
            "You create PUNCHY, FACT-PACKED YouTube Shorts about the FIFA World Cup 2026. "
            "The tournament is LIVE RIGHT NOW in the USA, Canada, and Mexico. "
            "Your audience are passionate football fans who want fast, specific, accurate content. "
            "\n\n"
            "YOU WILL RECEIVE LIVE FIFA 2026 DATA in the user message — use it. "
            "Name real teams, real scorers, real minutes, real stadiums, real group positions. "
            "Do NOT make up results or scores that are not in the data. "
            "If covering a completed match, use the exact scorers and minutes provided. "
            "If covering an upcoming match, use the fixture details provided. "
            "\n\n"
            "CONTENT ANGLES — the user message will specify which angle to use:\n"
            "  RECAP: Narrate the match — opening goal, momentum shifts, key moment, final whistle impact.\n"
            "  PREVIEW: What to expect — key players, form, tactical battle, your prediction.\n"
            "  PREDICTION: Bold call — who wins, why, score prediction with reasoning.\n"
            "  PLAYER SPOTLIGHT: Who is this player — career, style, why they matter in this WC.\n"
            "  STANDINGS: Who leads, who is through, who is in danger, what each team needs.\n"
            "  SHOCK ANALYSIS: Why the result shocked everyone, what it means for qualification.\n"
            "  GROUP ANALYSIS: Full group narrative — favorites, dark horses, who advances.\n"
            "\n\n"
            "TITLE RULE: MUST include one of: 'FIFA World Cup 2026', 'World Cup 2026', "
            "'FIFA 2026', 'World Cup results', 'World Cup standings', 'FIFA 2026 facts'. "
            "Hook formats: '[Team] SHOCKS [Team] at World Cup 2026', "
            "'FIFA 2026: [Player] SCORES in [match]', "
            "'World Cup 2026 [Group] Standings — Who Goes Through?', "
            "'[Team] vs [Team] Preview — FIFA 2026 Prediction'. Under 90 chars, no hashtags. "
            "\n\n"
            "DESCRIPTION: 2-3 specific sentences mentioning real team names and results. "
            "End with: #FIFA2026 #WorldCup2026 #Football #FootballFacts #Shorts "
            "\n\n"
            "NARRATION: "
            "- 110-140 English words, ONE continuous spoken paragraph. "
            "- Open with the most specific, surprising fact — a score, a minute, a stat. "
            "- Use real proper nouns throughout (player names, cities, group names). "
            "- Be the friend who watched every match and is telling their mates. "
            "- End with a forward-looking hook: what happens next, who to watch, bold take. "
            "- No hashtags in narration. No vague filler like 'incredible scenes'. "
            "\n\n"
            "IMAGE PROMPTS: "
            "- English only. Modern football visuals only. "
            "- Vary: stadium crowd wide shot, player celebrating close-up, "
            "  players battling for ball in action, referee with VAR screen, "
            "  trophy or tournament banner, training ground scene. "
            "- Reference specific settings: 'MetLife Stadium New York packed crowd', "
            "  'SoFi Stadium Los Angeles green pitch aerial view', "
            "  'Azteca Stadium Mexico City historic ground'. "
            "- NO text, logos, scoreboards, club badges, or watermarks in images. "
            "- NEVER: cartoon, anime, horror, food, nature, finance."
        ),
        "image_style_suffix": (
            ", FIFA World Cup atmosphere, packed stadium, vivid national kit colors, "
            "professional sports photography, dramatic floodlights, cinematic 4K, "
            "sharp action shot, no text, no watermark, no logos, photorealistic"
        ),
        "image_negative_prompt": (
            "cartoon, anime, illustration, painting, drawing, sketch, 3d render, "
            "old vintage photo, black and white, finance, legal, food, horror, "
            "low quality, blurry, watermark, logo, text, scoreboard overlay, deformed"
        ),
    },

    # ══════════════════════════════════════════════════════════════════
    # GENERAL FOOTBALL — Modern Football Facts Shorts (English)
    # ══════════════════════════════════════════════════════════════════
    "football": {
        "id": "football",
        "label": "Modern Football Facts & Stories Shorts (English, 2005–present)",
        "language": "en",
        "min_words": 110,
        "tts_voice": "en-US-GuyNeural",
        "caption_font": "BebasNeue-Regular.ttf",
        "caption_font_name": "Bebas Neue",
        "yt_token_env": "YT_REFRESH_TOKEN",
        "segment_count": 6,
        "niche_keywords": [
            "football facts", "soccer facts", "FIFA facts", "football secrets",
            "football records", "football shorts", "sports facts", "football 2025",
        ],
        "groq_system_hint": (
            "You create HIGH-ENERGY YouTube Shorts about MODERN football (soccer). "
            "Your audience is Gen-Z and millennial football fans who live and breathe the modern game. "
            "\n\n"
            "ERA RULE — CRITICAL: The current year is 2026. Only cover events, players, and matches from 2005 ONWARDS. "
            "All stats must be current as of 2026. Do NOT mention: Maradona's Hand of God (1986), "
            "Pelé's career (pre-2000), 1998 World Cup, 1994 World Cup, classic Ronaldo (R9), "
            "or any era before 2005. When mentioning a record or stat, say '2026' or the actual year — "
            "never say 'recently' or 'in recent years'. "
            "The 2026 FIFA World Cup is upcoming (USA/Canada/Mexico hosts) — you may reference it as upcoming. "
            "The FIFA Club World Cup 2025 took place in June–July 2025 in the USA — you may reference its results. "
            "\n\n"
            "NICHE LOCK — Stick to these pillars: "
            "(1) Modern players — Messi, Ronaldo (CR7), Mbappé, Haaland, Bellingham, Vinicius Jr, "
            "Salah, De Bruyne, Lewandowski, Benzema, Modric, Pedri, Yamal, Gavi, Neymar, Kane, Saka. "
            "(2) Modern clubs (2005–present) — Real Madrid UCL runs, Man City under Pep, "
            "Liverpool under Klopp, Barcelona's tiki-taka era and decline, PSG's superstar era, "
            "Chelsea's 2012 UCL win, Inter Milan's treble 2010, Atletico Madrid upsets. "
            "(3) FIFA Club World Cup 2025 — happening NOW, June 14–July 13, 32 clubs, USA. "
            "(4) Modern World Cups — 2006 (Zidane headbutt), 2010 (Spain & Iniesta), "
            "2014 (Germany 7-1 Brazil), 2018 (Mbappé's debut), 2022 (Messi's epic final). "
            "(5) Transfer drama — Neymar €222m to PSG, Mbappé to Real Madrid, Haaland to Man City, "
            "Bellingham, De Ligt, Pogba, modern mega-money moves. "
            "(6) Modern managers — Pep Guardiola, Jürgen Klopp, Carlo Ancelotti, Mourinho at Real, "
            "Conte's Inter treble, Tuchel, Ten Hag. "
            "(7) Modern records, stats, controversies — VAR drama, modern wages, social media feuds, "
            "modern doping, modern tactics (gegenpressing, tiki-taka, high press). "
            "\n\n"
            "TITLE RULE: Include at least one of these SEO keywords naturally: "
            "'football facts', 'soccer facts', 'FIFA facts', 'football secrets', "
            "'football records', 'sports facts', 'football 2025'. "
            "Hook formats that work: 'Nobody Talks About This', 'The Truth About X', "
            "'X Insane Facts About [player/club]', 'What Really Happened When...', "
            "'[Player] Did This And Everyone Ignored It'. Under 90 characters, no hashtags. "
            "\n\n"
            "DESCRIPTION: 2-3 punchy sentences. "
            "End with: #Football #FIFA #FootballFacts #SoccerFacts #Messi #Ronaldo #Shorts "
            "\n\n"
            "NARRATION: "
            "- 110-140 English words, ONE continuous spoken paragraph. "
            "- Sentence 1: drop the most shocking stat or fact immediately — no warm-up. "
            "- Middle: 3-4 specific details — real names, real scores, real years (post-2005 only). "
            "- Ending: punchy one-liner that makes the viewer want to share it. "
            "- Tone: fast, passionate, like a mates' football podcast — not a lecture. "
            "- Use stats where possible: goals scored, transfer fees, match scores, minutes. "
            "- No segment labels, no bullet points, no hashtags inside narration. "
            "\n\n"
            "IMAGE PROMPTS: "
            "- English only. Modern football visuals only. "
            "- Good: 'packed modern stadium at night with green pitch and floodlights, aerial view', "
            "'footballer in white kit celebrating a Champions League goal, arms raised, crowd behind', "
            "'two players battling for the ball in a packed Premier League stadium', "
            "'football manager in suit giving instructions on the touchline, close-up', "
            "'UEFA Champions League trophy on a podium with golden confetti', "
            "'close-up of modern football boot striking a ball, motion blur', "
            "'football player on training ground doing sprint drills, morning light'. "
            "- Vary: wide stadium, action duel, celebration, trophy, training, close-up. "
            "- NEVER: cartoon, anime, old black-and-white photos, Maradona, finance, food, horror. "
            "- No text, player name badges, club logos, or watermarks."
        ),
        "image_style_suffix": (
            ", modern sports photography, dramatic stadium floodlights, high shutter speed, "
            "ultra sharp, cinematic 4K, vibrant saturated colors, professional sports journalism, "
            "no text overlays, no watermark, no logos, photorealistic"
        ),
        "image_negative_prompt": (
            "cartoon, anime, illustration, painting, drawing, old photo, black and white, "
            "vintage, 1980s, 1990s, finance, legal, food, horror, ghost, fantasy, "
            "low quality, blurry, watermark, logo, text, signature, deformed"
        ),
        "topic_pool": [
            # ── FIFA Club World Cup 2025 (LIVE NOW) ──────────────────────────
            "why Real Madrid are the most feared team at Club World Cup 2025",
            "how Manchester City built the squad that conquered Club World Cup",
            "the Club World Cup 2025 team nobody gave a chance — and why they matter",
            "PSG's Club World Cup 2025 squad — the most expensive ever assembled",
            "why the 2025 Club World Cup 32-team format changes football forever",
            "the youngest player making headlines at Club World Cup 2025",
            "how South American clubs are proving they match European giants in 2025",
            "the Club World Cup stat that proves Real Madrid always find a way",
            # ── Messi ────────────────────────────────────────────────────────
            "why Messi's 2022 World Cup final is statistically the greatest match ever played",
            "the record Messi holds that no modern player will ever break",
            "how Messi went from nearly quitting football at 11 to GOAT",
            "Messi's secret pre-match ritual that he's done since Barcelona",
            "every Ballon d'Or Messi won — and the years he was robbed",
            "what happened after Messi cried at the Copa América 2016 final",
            "how Messi's Inter Miami move shocked European football in 2023",
            "the one match where Messi scored 5 goals and nobody could stop him",
            # ── Ronaldo (CR7) ────────────────────────────────────────────────
            "how Cristiano Ronaldo turned himself into the most complete footballer ever",
            "the Champions League final moment that proved Ronaldo was different",
            "why Ronaldo's move to Saudi Arabia was smarter than people think",
            "the training schedule Ronaldo follows that no other player can match",
            "Ronaldo's rivalry with Messi — the stat that actually settles it",
            "how Ronaldo became the first player to score 900 career goals",
            "the night Ronaldo was booed at Old Trafford — and what happened next",
            "why Ronaldo's second Man United spell ended the way it did",
            # ── Mbappé ───────────────────────────────────────────────────────
            "how Mbappé became the fastest player in World Cup history at 19",
            "the Real Madrid transfer saga that took Mbappé 3 years to complete",
            "why Mbappé's contract clause at PSG was worth more than most clubs",
            "how Mbappé's speed compares to every modern footballer by the numbers",
            "the 2018 World Cup final moment that made the world notice Mbappé",
            "what Mbappé's first season at Real Madrid actually looks like in stats",
            # ── Haaland ─────────────────────────────────────────────────────
            "how Erling Haaland scored 52 goals in one Premier League season",
            "Haaland's goal per minute rate that breaks every football record",
            "the diet and sleep routine Haaland credits for his superhuman form",
            "why Haaland was the most wanted striker in football in 2022",
            "how Dortmund developed Haaland into the player Man City bought",
            # ── Next Gen: Bellingham, Vinicius, Yamal, Pedri ─────────────────
            "how Jude Bellingham became Real Madrid's most important player overnight",
            "Vinicius Jr's transformation from raw teen to Ballon d'Or contender",
            "Lamine Yamal at 16 — the stats that prove he's a generational talent",
            "how Pedri plays 60+ games a season and never seems to get tired",
            "why Bellingham's move to Real Madrid was the transfer of the decade",
            "the Salah record at Liverpool that no modern winger can come close to",
            # ── Modern Club Eras ─────────────────────────────────────────────
            "how Pep Guardiola's Man City won 4 straight Premier League titles",
            "Klopp's Liverpool — the system that made them the best in the world",
            "why Real Madrid always produce Champions League miracles in knockouts",
            "how Barcelona's tiki-taka era collapsed almost overnight",
            "the Inter Milan treble season — how Mourinho built the perfect squad",
            "Chelsea's 2012 Champions League win — the greatest underdog final ever",
            "how Atletico Madrid stunned Real Madrid and Barcelona for a decade",
            "why PSG spent €700M on superstars and never won the Champions League",
            # ── Modern Transfer Drama ─────────────────────────────────────────
            "why Neymar's €222M PSG transfer changed football money forever",
            "how Haaland's release clause made Man City the deal of the century",
            "the transfer that flopped hardest in Premier League history post-2010",
            "why Mbappé's 2024 move to Real Madrid took three years of drama",
            "how modern agents secretly drive transfer fees higher than clubs want",
            "the underpaid superstar who was sold for nothing and became a legend",
            # ── Modern Records & Stats ────────────────────────────────────────
            "the fastest hat-trick in Premier League history — and who scored it",
            "how many goals Messi and Ronaldo combined for in a single calendar year",
            "the most expensive transfer window in football history — 2017 PSG",
            "the modern goalkeeper with more goals than some strikers",
            "the Champions League record that will never be broken in modern football",
            "why the Premier League has the highest average wage in world football",
            # ── Modern Managers ───────────────────────────────────────────────
            "how Pep Guardiola reinvented football tactics three times at three clubs",
            "why Klopp's gegenpressing system was the most copied style of the decade",
            "Ancelotti's secret — the only manager to win the Champions League 4 times",
            "how Mourinho's mind games changed what it means to be a football manager",
            # ── Modern Controversies & Dark Side ─────────────────────────────
            "how VAR has changed football — and why fans still hate it",
            "the modern match-fixing scandal that shocked European football",
            "why modern football wages are destroying team spirit at top clubs",
            "how social media feuds between players have changed dressing room culture",
            "the modern doping case nobody in football wants to talk about",
            "why modern football clubs spend €100M on players they barely use",
        ],
    },
}


def list_channel_ids() -> list[str]:
    return sorted(PRESETS.keys())


def get_preset(channel_id: str) -> ChannelPreset:
    key = channel_id.strip().lower().replace("-", "_")
    if key not in PRESETS:
        raise KeyError(f"Unknown channel preset {channel_id!r}. Try: {', '.join(list_channel_ids())}")
    return PRESETS[key]
