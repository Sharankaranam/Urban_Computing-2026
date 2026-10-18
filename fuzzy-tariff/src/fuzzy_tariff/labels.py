"""User-facing labels and messages (DE/FR/IT/EN).

Translations are DRAFTS and must be validated with native speakers and in user tests.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

Lang = Literal["en", "de", "fr", "it"]
SUPPORTED_LANGS: tuple[Lang, ...] = ("en", "de", "fr", "it")


class Label(StrEnum):
    """Output sets of the stage-1 FIS, ordered from worst to best time to consume."""

    AVOID = "avoid"
    WAIT = "wait"
    OKAY = "okay"
    GOOD = "good"
    IDEAL = "ideal"

    @property
    def rank(self) -> int:
        return list(Label).index(self)

    @property
    def is_cheap(self) -> bool:
        return self in (Label.GOOD, Label.IDEAL)


class Action(StrEnum):
    """Output sets of the stage-2 (device advisor) FIS."""

    WAIT = "wait"
    START_NOW = "start_now"
    MUST_START = "must_start"


LABEL_TEXT: dict[Lang, dict[Label, str]] = {
    "en": {
        Label.AVOID: "Very expensive: avoid",
        Label.WAIT: "Expensive: better later",
        Label.OKAY: "Normal",
        Label.GOOD: "Cheap",
        Label.IDEAL: "Very cheap: best time",
    },
    "de": {
        Label.AVOID: "Sehr teuer: meiden",
        Label.WAIT: "Teuer: später besser",
        Label.OKAY: "Normal",
        Label.GOOD: "Günstig",
        Label.IDEAL: "Sehr günstig: beste Zeit",
    },
    "fr": {
        Label.AVOID: "Très cher : à éviter",
        Label.WAIT: "Cher : mieux plus tard",
        Label.OKAY: "Normal",
        Label.GOOD: "Bon marché",
        Label.IDEAL: "Très bon marché : meilleur moment",
    },
    "it": {
        Label.AVOID: "Molto caro: da evitare",
        Label.WAIT: "Caro: meglio più tardi",
        Label.OKAY: "Normale",
        Label.GOOD: "Conveniente",
        Label.IDEAL: "Molto conveniente: momento migliore",
    },
}

ACTION_TEXT: dict[Lang, dict[Action, str]] = {
    "en": {
        Action.WAIT: "Wait for a cheaper window",
        Action.START_NOW: "Good time to start now",
        Action.MUST_START: "Start now to be ready in time",
    },
    "de": {
        Action.WAIT: "Auf ein günstigeres Zeitfenster warten",
        Action.START_NOW: "Jetzt ist ein guter Zeitpunkt zum Starten",
        Action.MUST_START: "Jetzt starten, damit es rechtzeitig fertig ist",
    },
    "fr": {
        Action.WAIT: "Attendre une période moins chère",
        Action.START_NOW: "Bon moment pour démarrer maintenant",
        Action.MUST_START: "Démarrer maintenant pour être prêt à temps",
    },
    "it": {
        Action.WAIT: "Aspettare una fascia più conveniente",
        Action.START_NOW: "Buon momento per avviare ora",
        Action.MUST_START: "Avviare ora per essere pronti in tempo",
    },
}


def label_text(label: Label | str, lang: Lang = "en") -> str:
    return LABEL_TEXT[lang][Label(label)]


def action_text(action: Action | str, lang: Lang = "en") -> str:
    return ACTION_TEXT[lang][Action(action)]
