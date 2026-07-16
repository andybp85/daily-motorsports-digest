"""Guards on the terms actually shipped in config.example.toml.

The other term tests use a small hand-built REGISTRY, so they can't catch a bad
term in the real config. These can: the f1/indycar terms are sent to GDELT as
search keywords against a *general world-news* corpus, and is_relevant() then
re-checks that same list — so an ambiguous term is both what pulls junk in and
what waves it through. A bare surname here is a live pipe from world news into
the digest, not a hypothetical.

Regression for the 2026-07-16 leak: ~45 of 79 GDELT articles were non-motorsport
(Hamilton, Ontario city council; Russell 1000 ETF; Xabi Alonso; Alexander
Hamilton; Hamilton Insurance Group).
"""

from digest.config import load_config
from digest.normalize import classify_series

REGISTRY = load_config("config.example.toml").series

# Real headlines pulled from a live GDELT query using the pre-fix f1 terms.
NON_MOTORSPORT_HEADLINES = (
    "Hamilton to vote on pausing new data centres",
    "Body found after Hamilton furniture store fire identified as 48-year-old man",
    "Hamilton police arrest two men after separate violent incidents in city downtown core",
    "Hamilton County man accused of having sexual relationship with teenager",
    "Does the Future of Conservative Economics Belong to Alexander Hamilton or to Milton Friedman?",
    "Hamilton Insurance Group (NYSE:HG) Shares Down 3.9% - Time to Sell?",
    "The Open Championship matchup picks: Chris Gotterup, Russell Henley among best bets",
    "Vanguard Small-Cap Growth ETF vs Russell 1000 Growth ETF",
    "REPLAY: Russell Vought Testifies on CFPB Semi-Annual Report",
    "Allison Russell and Norah Jones harmonious collab, and 4 more songs you need to hear",
    "Nancy Sheryl Johnson Norris",
    "Xabi Alonso dispensa 160 milhoes e promete nao ficar por aqui",
    "Alonso wants Fernandez stay - Ghanaian Times",
    "Drome. Philippe Leclerc, specialiste de la restauration de voitures anciennes et rares",
)

# Headlines the digest exists to deliver — anchoring terms must not cost us these.
MOTORSPORT_HEADLINES = (
    ("Lewis Hamilton tops final practice at Spa", "f1"),
    ("George Russell responds to Mercedes crisis claims", "f1"),
    ("Lando Norris takes pole in Hungary", "f1"),
    ("Charles Leclerc on the online criticism", "f1"),
    ("Fernando Alonso reflects on his Aston Martin season", "f1"),
    ("What Max Verstappen said about Ferrari's big performance upgrade", "f1"),
    ("Oscar Piastri wins from lights to flag", "f1"),
    ("Alex Palou dominates at the Indy 500", "indycar"),
    ("Scott Dixon charges through the field at Mid-Ohio", "indycar"),
    ("Josef Newgarden reveals regret over Indy 500 behaviour", "indycar"),
)


def test_shipped_terms_reject_non_motorsport_headlines():
    leaked = [h for h in NON_MOTORSPORT_HEADLINES if classify_series(h, "", REGISTRY) != ""]
    assert leaked == [], f"non-motorsport headlines classified as a followed series: {leaked}"


def test_shipped_terms_still_keep_real_motorsport_headlines():
    missed = [(h, want, classify_series(h, "", REGISTRY)) for h, want in MOTORSPORT_HEADLINES if classify_series(h, "", REGISTRY) != want]
    assert missed == [], f"real motorsport headlines misclassified: {missed}"


def test_indycar_terms_exclude_multi_series_teams():
    """Penske and Ganassi field NASCAR and IMSA entries too.

    As indycar keywords they pulled NASCAR stories out of GDELT (Blaney drives
    for Penske), which then classified as indycar and claimed core_floor slots.
    """
    indycar = next(s for s in REGISTRY if s.id == "indycar")
    lowered = {t.lower() for t in indycar.terms}
    assert "penske" not in lowered
    assert "ganassi" not in lowered
