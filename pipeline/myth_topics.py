"""Hindi mythology Shorts — theme-of-day rotation + no-repeat within each theme.

- **Theme cycle** (IST calendar day): Ganesha → Shiva → Vishnu & avatars → …
  Same theme all day in India; next calendar day advances to the next deity block.
- **Topic pick**: random among topics in today's theme that are not yet marked used.
  When a theme's pool is exhausted, its used-list resets and topics can appear again.

State file: `output/history/myth_topic_rotation.json` (cache this path in CI like story history).
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "output" / "history" / "myth_topic_rotation.json"

IST = ZoneInfo("Asia/Kolkata")

# Order of themes by calendar day (cycles forever).
THEME_ORDER: list[str] = [
    "ganesha",
    "shiva",
    "vishnu_avatars",
    "devi_shakti",
    "ramayana",
    "mahabharata",
    "other_deities",
    "after_stories",
    "moral",
]

MYTH_POOLS: dict[str, list[str]] = {
    "ganesha": [
        "Why Ganesha has one tusk — the Mahabharata writing story",
        "Why Ganesha's vehicle is a tiny mouse",
        "The story of why Moon got cursed by Ganesha",
        "Why Ganesha is worshipped first before all gods",
        "The real story of how Ganesha got his elephant head (Shiva version)",
        "Why Ganesha is called Ekdanta",
        "The time Ganesha raced his brother Kartikeya around the world",
        "Why Ganesha loves modak — the original story",
        "Ganesha's 108 names and what they each mean",
        "The story of Ganesha and the cat — why he has a mark on his stomach",
        "Why Ganesha is also called Vighneshwara",
        "The story of Ganesha defeating the demon Gajamukhasura",
        "Why Ganesha's trunk curves left vs right — significance",
        "The time Ganesha humbled Kubera with his hunger",
        "Ganesha and Tulsi — why she is not offered to him",
        "The lesser-known form: Heramba Ganapati (5 heads, lion vehicle)",
        "Why Ganesha is worshipped during Diwali alongside Lakshmi",
        "The story of Ganesha and the demon Sindura",
        "32 forms of Ganesha — what each represents",
        "Why Ganesha is considered the god of new beginnings, not just obstacles",
    ],
    "shiva": [
        "Why Shiva has a crescent moon on his head",
        "The story of how Ganga came to rest in Shiva's hair",
        "Why Shiva wears a snake around his neck — Vasuki's story",
        "The real meaning of Shiva's Tandava dance",
        "Why Shiva is called Neelakantha — the blue throat story",
        "The story of Shiva and the demon Andhaka",
        "Why Shiva lives in a cremation ground",
        "The time Shiva disguised himself to test Arjuna",
        "Why Shiva's trident (trishul) has three prongs — symbolism",
        "The story of Shiva defeating Tripurasura (burning three cities)",
        "Why Shiva is also called Bholenath — the innocent god",
        "The story of Shiva and Daksha — why Sati jumped into fire",
        "What the Damaru drum of Shiva represents",
        "The 12 Jyotirlingas — origin story of each",
        "Why Shiva's eyes are half open in meditation",
        "The time Shiva became Ardhanarishvara — half man half woman",
        "Why Shiva is the only god worshipped as a formless Lingam",
        "The story of Shiva cursing Brahma — why Brahma has no temples",
        "Why Shiva is called Mahakala — lord of time",
        "The story of Shiva and Goddess Parvati's first meeting",
    ],
    "vishnu_avatars": [
        "What each object in Vishnu's 4 hands means",
        "Why Vishnu sleeps on a serpent in the cosmic ocean",
        "The story of Vishnu's Sudarshana Chakra — how he got it",
        "Why Vishnu is blue — the real mythological reason",
        "The story of Garuda — Vishnu's eagle vehicle",
        "Matsya Avatar — Vishnu as a fish, saving the Vedas",
        "Kurma Avatar — why Vishnu became a tortoise",
        "Varaha Avatar — the boar who lifted the Earth",
        "Narasimha Avatar — the half-lion who came through a pillar",
        "Vamana Avatar — the dwarf who measured three worlds",
        "Parashurama — the warrior brahmin who cleared earth 21 times",
        "The story of Balarama — why he is sometimes the 8th avatar",
        "Kalki Avatar — what will happen when Vishnu's final form arrives",
        "Why Vishnu took the form of Mohini — the enchantress",
        "The story of Vishnu and Goddess Lakshmi's marriage",
        "Why Vishnu has Shrivatsa mark on his chest",
        "The time Vishnu tricked the demons during Samudra Manthan",
        "Why Vishnu is called Trivikrama after the Vamana avatar",
        "The story of Vishnu saving Draupadi — the unending sari",
        "Why Vishnu's vehicle Garuda is enemies with snakes",
        "The lesser-known Hayagriva avatar — Vishnu with a horse head",
        "Dattatreya — the three-headed avatar of Brahma, Vishnu, Shiva",
        "The story of Prahlada and why Vishnu came as Narasimha",
        "Why Vishnu is called Sheshashayi — sleeping on Shesha serpent",
        "The time Vishnu had to become a woman to save the universe",
    ],
    "devi_shakti": [
        "Why Durga rides a lion and carries 8 weapons",
        "The story of Mahishasura — why Durga was created",
        "Why Kali's tongue is out — the story of Raktabija",
        "The 9 forms of Navdurga and what each destroys",
        "Why Saraswati is associated with the swan",
        "The story of Lakshmi leaving Indra's heaven — why gods lost power",
        "Why Lakshmi stands on a lotus — the symbolism",
        "The story of Goddess Chinnamasta — the self-beheaded goddess",
        "Why Kamakhya temple has no idol — only a yoni shaped rock",
        "The story of Sati's body parts falling — origin of Shakti Peethas",
        "Why there are 51 Shakti Peethas across India",
        "Bagalamukhi — the goddess who paralyzes enemies",
        "The story of Goddess Bhairavi and her 64 forms",
        "Why Parvati did severe tapasya to win Shiva",
        "The story of Annapurna — goddess who feeds the world",
        "Why Saraswati and Lakshmi don't get along — the rivalry story",
        "The origin story of Goddess Santoshi Mata",
        "Why Goddess Varahi is worshipped only at night",
        "Matangi — the outcaste goddess of speech and music",
        "The story of the goddess who defeated the demon Shumba-Nishumba",
    ],
    "ramayana": [
        "Who was Jatayu and how old was he when he fought Ravana",
        "The story of Shabari — why Ram ate her half-eaten berries",
        "Who was Vibhishana's wife — the untold story",
        "Why Ravana is considered a great devotee of Shiva",
        "The story of Kumbhakarna — why he sleeps 6 months",
        "Who was Ahiravana — the underworld version of Ravana",
        "The story of Sita's real birth — she came from the earth",
        "Why Lakshmana never slept for 14 years in the forest",
        "The story of Urmila — Lakshmana's wife who slept for 14 years",
        "Who was Atikaya — Ravana's giant son nobody talks about",
        "The real story of Surpanakha — more than just a villain",
        "Why Hanuman has a mark on his chin — the story",
        "The story of the squirrel who helped build the Ram Setu",
        "What happened to Ravana's wife Mandodari after the war",
        "The story of Indrajit (Meghnad) — the son who defeated Indra",
        "Why Rama had to perform Ashwamedha Yajna after killing Ravana",
        "The story of Luv and Kush — Rama's sons who defeated his army",
        "Why Ram sent Sita to the forest even after she proved her purity",
        "The story of Kalanemi — the demon disguised as a sage",
        "Who was Malyavan — Ravana's grandfather who warned him",
        "The story of the golden deer Maricha and his real identity",
        "Why Hanuman tore his chest to show Ram and Sita inside",
        "The story of Sampati — the elder brother of Jatayu",
        "What happened to Hanuman after the Ramayana ended",
        "The story of the final day — how Rama left the world",
    ],
    "mahabharata": [
        "Who was Barbarika — the warrior who could end the war in 1 minute",
        "The story of Eklavya — the greatest student who was betrayed",
        "Why Karna is the most tragic hero of the Mahabharata",
        "Who was Iravan — Arjuna's son who sacrificed himself",
        "The story of Ghatotkacha — Bhima's demon son",
        "Why Bheeshma chose to die on a bed of arrows",
        "The story of Amba — the woman whose revenge caused the war",
        "Who was Vidura — the wisest man who couldn't stop the war",
        "The story of Dhritarashtra's 100 sons — how they were born",
        "Why Draupadi had 5 husbands — the past life reason",
        "The story of Shikhandi — born female, lived as male, killed Bheeshma",
        "Who was Vikarna — the Kaurava who spoke against Draupadi's humiliation",
        "The story of Yudhishthira's dog — who was it really",
        "Why Ashwatthama is still alive today — the cursed immortal",
        "The story of Duryodhana's iron body — why only his thighs were weak",
        "Who was Satyaki — Arjuna's cousin who fought the whole war alone",
        "The story of Narayanastra — the weapon that no one could fight",
        "Why Krishna did not fight in the Mahabharata war",
        "The story of Karna returning Kunti's sons — his secret deal",
        "Who was Yuyutsu — the only Kaurava who switched sides",
        "The story of Parikshit — the baby saved by Krishna in the womb",
        "Why Yudhishthira was the only one who could enter heaven with his body",
        "The story of the dice game — who really planned it",
        "Who was Shakuni's real motive — revenge for his family",
        "The story of Draupadi's swayamvara — why only Arjuna could win",
        "Why Drona refused to teach Eklavya — the political reason",
        "The story of Hidimba — the demoness who loved Bhima",
        "Who was Jarasandha and why Krishna feared fighting him directly",
        "The story of the Kurukshetra war's 18th day — how it ended",
        "Why the Pandavas lost everything in one dice game",
        "The story of Krishna's Vishwaroopa — what Arjuna actually saw",
        "Who was Ulupi — the Naga princess who married Arjuna",
        "The story of Abhimanyu in the Chakravyuha — the unfair trap",
        "Why Kunti kept Karna a secret her whole life",
        "The story of what happened to all Pandavas after the war",
    ],
    "other_deities": [
        "Who is Kartikeya and why he left home — the peacock story",
        "The story of Surya (Sun God) and his two wives",
        "Why Indra lost his throne multiple times — the pattern",
        "The story of Kubera — how he became the god of wealth",
        "Who is Yama — and is he really the god of death or justice",
        "The story of Chitragupta — the one who writes your karma",
        "Why Saraswati's vehicle is a swan — the symbolism",
        "The story of Agni (fire god) — why he hides in water",
        "Who is Vayu — the wind god and father of Hanuman",
        "The story of Varuna — the forgotten god of oceans",
        "Why Brihaspati is the guru of gods — his origin story",
        "The story of Chandra (Moon God) and his 27 wives",
        "Who is Kamadeva — the god of love who was burned by Shiva",
        "The story of Rati — Kamadeva's wife who brought him back",
        "Why Vishwakarma built Lanka for Ravana — then gave it away",
        "The story of Narada — the gossip god who created great stories",
        "Who is Revanta — the forgotten son of Surya",
        "The story of Manasa Devi — the snake goddess of Bengal",
        "Who is Ayyappa — the son of Shiva and Mohini",
        "The story of Bhairava — Shiva's fierce form and why he roams",
    ],
    "after_stories": [
        "What happened to Lanka after Ravana died",
        "What happened to Hanuman after Ram returned to heaven",
        "What happened to Draupadi after the Pandavas died",
        "Where did Krishna go after the Mahabharata war ended",
        "What happened to the Yadava clan after Krishna left",
        "What happened to Ashwatthama — is he still wandering",
        "What happened to Gandhari after the war — her curse on Krishna",
        "What happened to Vibhishana — did he rule Lanka forever",
        "Where did the Pandavas go after they left the throne",
        "What happened in heaven when Yudhishthira arrived",
        "What happened to Karna's armor — the Kavach and Kundal",
        "What happened to Subhadra after Abhimanyu died",
        "What happened to Eklavya after he gave his thumb",
        "What happened to the bow Gandiva after the war",
        "What happened to Balarama — how he left the world",
        "What happened to Parikshit — Arjuna's grandson who became king",
        "What happened to Drona's son Ashwatthama's gem",
        "What happened to the city of Dwarka after Krishna died",
        "What happened to Surpanakha after the war",
        "What happened to the Vanaras (monkey army) after the Ramayana",
    ],
    "moral": [
        "The time Yudhishthira lied once — and what it cost him",
        "Why Karna's generosity still couldn't save him — the lesson",
        "What Bhagavad Gita says about doing your duty without reward",
        "The story of Nachiketa — a boy who questioned Yama about death",
        "Why Prahlada's faith was stronger than his father's power",
        "The lesson from Eklavya — talent vs. the system",
        "What Vidura's wisdom says about speaking truth to power",
        "The story of King Harishchandra — who never told a lie",
        "Why Bheeshma's promise destroyed his entire family — the lesson",
        "The story of Savitri — who argued with Yama and won her husband back",
        "What the story of Shakuntala teaches about memory and identity",
        "The story of Sudama — Krishna's poor friend and true friendship",
        "Why Duryodhana refused peace — pride vs. wisdom",
        "The lesson from Dronacharya — how a guru can be wrong",
        "The story of Arjuna's doubt — why even the best warriors fear",
    ],
}


def _load_state() -> dict[str, dict]:
    if not STATE_PATH.is_file():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(data: dict[str, dict]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def theme_for_today_ist() -> str:
    """Which myth block today (India calendar). Cycles through THEME_ORDER."""
    d = datetime.now(IST).date()
    idx = d.toordinal() % len(THEME_ORDER)
    return THEME_ORDER[idx]


def pick_myth_topic(channel_id: str) -> tuple[str, str]:
    """Return (topic_hint, theme_key) for Groq. Does not persist yet."""
    theme = theme_for_today_ist()
    pool = MYTH_POOLS.get(theme, [])
    if not pool:
        raise RuntimeError(f"No myth topics for theme {theme!r}")

    state = _load_state()
    ch = state.setdefault(channel_id, {"used": {}})

    used_list = ch["used"].setdefault(theme, [])
    used_set = set(used_list)
    available = [t for t in pool if t not in used_set]

    if not available:
        ch["used"][theme] = []
        available = list(pool)

    topic = random.choice(available)
    return topic, theme


def commit_myth_topic(channel_id: str, theme: str, topic: str) -> None:
    """Call after a full successful run so this topic is not chosen again until pool resets."""
    state = _load_state()
    ch = state.setdefault(channel_id, {"used": {}})
    used = ch["used"].setdefault(theme, [])
    if topic not in used:
        used.append(topic)
    _save_state(state)
