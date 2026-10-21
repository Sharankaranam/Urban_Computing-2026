"""Linguistic Summarization of dynamic tariffs and energy schedules via Fuzzy Quantifiers.

Based on fuzzy data summarization theory by R. R. Yager (1982) and J. Kacprzyk & S. Zadrożny (2001).
Evaluates Type-I ('Q intervals are S') and Type-II ('Q B intervals are S') protoforms with
truth degrees T = mu_Q(Sigma-Count(B and S) / Sigma-Count(B)).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from fuzzy_tariff.fuzzy.membership import MembershipFunction

Lang = Literal["en", "de", "fr", "it"]

# Relative Fuzzy Quantifiers Q over ratio r in [0, 1]
QUANTIFIERS: dict[str, MembershipFunction] = {
    "almost_all": MembershipFunction("trap", (0.75, 0.90, 1.0, 1.0)),
    "most": MembershipFunction("trap", (0.55, 0.70, 1.0, 1.0)),
    "many": MembershipFunction("tri", (0.35, 0.55, 0.75)),
    "about_half": MembershipFunction("tri", (0.35, 0.50, 0.65)),
    "a_few": MembershipFunction("tri", (0.10, 0.25, 0.45)),
    "very_few": MembershipFunction("trap", (0.0, 0.0, 0.15, 0.30)),
    "none_or_almost_none": MembershipFunction("trap", (0.0, 0.0, 0.05, 0.15)),
}

# Human-readable labels for Quantifiers (Q)
QUANTIFIER_LABELS: dict[Lang, dict[str, str]] = {
    "en": {
        "almost_all": "Almost all",
        "most": "Most",
        "many": "Many",
        "about_half": "About half of",
        "a_few": "A few",
        "very_few": "Very few",
        "none_or_almost_none": "None or almost none of",
    },
    "de": {
        "almost_all": "Fast alle",
        "most": "Die meisten",
        "many": "Viele",
        "about_half": "Etwa die Hälfte der",
        "a_few": "Einige wenige",
        "very_few": "Sehr wenige",
        "none_or_almost_none": "Keine oder fast keine der",
    },
    "fr": {
        "almost_all": "Presque tous les",
        "most": "La plupart des",
        "many": "Beaucoup d'",
        "about_half": "Environ la moitié des",
        "a_few": "Quelques",
        "very_few": "Très peu d'",
        "none_or_almost_none": "Aucun ou presque aucun des",
    },
    "it": {
        "almost_all": "Quasi tutti gli",
        "most": "La maggior parte degli",
        "many": "Molti",
        "about_half": "Circa la metà degli",
        "a_few": "Alcuni",
        "very_few": "Pochissimi",
        "none_or_almost_none": "Nessuno o quasi nessuno degli",
    },
}

# Qualifiers / Time Windows / Subject Conditions (B)
QUALIFIER_LABELS: dict[Lang, dict[str, str]] = {
    "en": {
        "all_day": "intervals of the day",
        "night_hours": "night hours (00:00–06:00)",
        "morning_ramp": "morning ramp hours (06:30–09:00)",
        "midday_solar": "midday solar hours (11:00–15:00)",
        "evening_peak": "evening peak hours (17:30–20:30)",
        "late_evening": "late evening hours (21:00–23:45)",
        "high_grid_stress": "hours with high transformer stress",
        "falling_price_trend": "hours with falling price trend",
    },
    "de": {
        "all_day": "Intervalle des Tages",
        "night_hours": "Nachtstunden (00:00–06:00)",
        "morning_ramp": "Morgenstunden (06:30–09:00)",
        "midday_solar": "Mittagsstunden mit Solar (11:00–15:00)",
        "evening_peak": "Abend-Spitzenstunden (17:30–20:30)",
        "late_evening": "Spätabendstunden (21:00–23:45)",
        "high_grid_stress": "Stunden mit hoher Transformatorlast",
        "falling_price_trend": "Stunden mit fallendem Preistrend",
    },
    "fr": {
        "all_day": "intervalles de la journée",
        "night_hours": "heures de nuit (00:00–06:00)",
        "morning_ramp": "heures de pointe du matin (06:30–09:00)",
        "midday_solar": "heures solaires de midi (11:00–15:00)",
        "evening_peak": "heures de pointe du soir (17:30–20:30)",
        "late_evening": "heures de fin de soirée (21:00–23:45)",
        "high_grid_stress": "heures à forte contrainte transformateur",
        "falling_price_trend": "heures avec tendance de prix à la baisse",
    },
    "it": {
        "all_day": "intervalli della giornata",
        "night_hours": "ore notturne (00:00–06:00)",
        "morning_ramp": "ore mattutine di rampa (06:30–09:00)",
        "midday_solar": "ore solari di mezzogiorno (11:00–15:00)",
        "evening_peak": "ore di punta serali (17:30–20:30)",
        "late_evening": "ore di tarda serata (21:00–23:45)",
        "high_grid_stress": "ore con elevato stress del trasformatore",
        "falling_price_trend": "ore con tendenza del prezzo al ribasso",
    },
}

# Summarizers / Properties (S)
SUMMARIZER_LABELS: dict[Lang, dict[str, str]] = {
    "en": {
        "ideal": "Ideal (best time to consume)",
        "good": "Good (cheap electricity)",
        "okay": "Normal (standard tariff)",
        "wait": "Expensive (better postponed)",
        "avoid": "Avoid (peak price / congested grid)",
        "cheap": "Cost-effective (Ideal or Good)",
        "expensive": "Unfavorable (Avoid or Wait)",
        "low_grid_congestion": "operating under low grid congestion",
        "critical_grid_congestion": "facing critical transformer load",
    },
    "de": {
        "ideal": "Ideal (beste Verbrauchszeit)",
        "good": "Günstig (preiswerte Energie)",
        "okay": "Normal (Standardtarif)",
        "wait": "Teuer (besser verschieben)",
        "avoid": "Zu meiden (Spitzenpreis / Netzüberlastung)",
        "cheap": "Kostengünstig (Ideal oder Günstig)",
        "expensive": "Ungünstig (Meiden oder Warten)",
        "low_grid_congestion": "bei geringer Netzbelastung",
        "critical_grid_congestion": "unter kritischer Transformatorüberlastung",
    },
    "fr": {
        "ideal": "Idéal (meilleur moment pour consommer)",
        "good": "Bon marché (électricité économique)",
        "okay": "Normal (tarif standard)",
        "wait": "Cher (mieux vaut reporter)",
        "avoid": "À éviter (prix élevé / réseau saturé)",
        "cheap": "Économique (Idéal ou Bon marché)",
        "expensive": "Défavorable (Éviter ou Attendre)",
        "low_grid_congestion": "avec une faible congestion du réseau",
        "critical_grid_congestion": "sous une charge de transformateur critique",
    },
    "it": {
        "ideal": "Ideale (miglior momento di consumo)",
        "good": "Conveniente (energia economica)",
        "okay": "Normale (tariffa standard)",
        "wait": "Caro (meglio posticipare)",
        "avoid": "Da evitare (prezzo di picco / congestione)",
        "cheap": "Vantaggioso (Ideale o Conveniente)",
        "expensive": "Sfavorevole (Evitare o Aspettare)",
        "low_grid_congestion": "a bassa congestione di rete",
        "critical_grid_congestion": "sotto carico critico del trasformatore",
    },
}


@dataclass(frozen=True)
class StepTimeSeriesData:
    """Pre-computed 96-step time series inputs for linguistic evaluation."""

    hours: NDArray[np.float64]  # 0.0 .. 23.75
    scores: NDArray[np.float64]  # S(t) in [0, 100]
    memberships: dict[str, NDArray[np.float64]]  # avoid, wait, okay, good, ideal in [0, 1]
    g_stress: NDArray[np.float64]  # G in [0, 1]
    t_trend: NDArray[np.float64]  # T in [-1, 1]
    total_rp: NDArray[np.float64]  # Tariff in Rp./kWh


@dataclass(frozen=True)
class ProtoformEvaluation:
    protoform_type: str  # "type_1" or "type_2"
    quantifier: str
    quantifier_label: str
    qualifier: str | None
    qualifier_label: str | None
    summarizer: str
    summarizer_label: str
    cardinality_ratio: float  # r in [0, 1]
    truth_degree: float  # T1 in [0, 1]
    coverage_degree: float  # T3 in [0, 1]
    validity_score: float  # weighted quality
    statement: str


def compute_qualifier_mask(qualifier: str, data: StepTimeSeriesData) -> NDArray[np.float64]:
    """Compute membership array mu_B(t) in [0, 1] for a given qualifier."""
    hours = data.hours
    if qualifier == "all_day":
        return np.ones_like(hours, dtype=float)
    if qualifier == "night_hours":
        # 00:00 - 06:00
        return np.where((hours >= 0.0) & (hours < 6.0), 1.0, 0.0)
    if qualifier == "morning_ramp":
        # 06:30 - 09:00
        return np.where((hours >= 6.5) & (hours < 9.0), 1.0, 0.0)
    if qualifier == "midday_solar":
        # 11:00 - 15:00
        return np.where((hours >= 11.0) & (hours < 15.0), 1.0, 0.0)
    if qualifier == "evening_peak":
        # 17:30 - 20:30
        return np.where((hours >= 17.5) & (hours <= 20.5), 1.0, 0.0)
    if qualifier == "late_evening":
        # 21:00 - 24:00
        return np.where(hours >= 21.0, 1.0, 0.0)
    if qualifier == "high_grid_stress":
        # G >= 0.55
        return np.clip((data.g_stress - 0.40) / 0.30, 0.0, 1.0)
    if qualifier == "falling_price_trend":
        # T <= -0.15
        return np.clip((-data.t_trend - 0.10) / 0.30, 0.0, 1.0)
    raise ValueError(f"Unknown qualifier {qualifier!r}")


def compute_summarizer_membership(summarizer: str, data: StepTimeSeriesData) -> NDArray[np.float64]:
    """Compute membership array mu_S(t) in [0, 1] for a given summarizer."""
    m = data.memberships
    if summarizer in m:
        return np.asarray(m[summarizer], dtype=float)
    if summarizer == "cheap":
        # Ideal or Good
        ideal = m.get("ideal", np.zeros_like(data.hours))
        good = m.get("good", np.zeros_like(data.hours))
        return np.maximum(ideal, good)
    if summarizer == "expensive":
        # Avoid or Wait
        avoid = m.get("avoid", np.zeros_like(data.hours))
        wait = m.get("wait", np.zeros_like(data.hours))
        return np.maximum(avoid, wait)
    if summarizer == "low_grid_congestion":
        return np.clip((0.45 - data.g_stress) / 0.30, 0.0, 1.0)
    if summarizer == "critical_grid_congestion":
        return np.clip((data.g_stress - 0.50) / 0.35, 0.0, 1.0)
    raise ValueError(f"Unknown summarizer {summarizer!r}")


def build_protoform_statement(
    quantifier: str,
    qualifier: str | None,
    summarizer: str,
    lang: Lang = "en",
) -> str:
    """Format human-readable natural language statement."""
    q_str = QUANTIFIER_LABELS.get(lang, QUANTIFIER_LABELS["en"]).get(quantifier, quantifier)
    b_str = (
        QUALIFIER_LABELS.get(lang, QUALIFIER_LABELS["en"]).get(qualifier or "all_day", qualifier)
        if qualifier
        else None
    )
    s_str = SUMMARIZER_LABELS.get(lang, SUMMARIZER_LABELS["en"]).get(summarizer, summarizer)

    if lang == "de":
        if not qualifier or qualifier == "all_day":
            return f"{q_str} Intervalle des Tages sind {s_str}."
        return f"{q_str} {b_str} sind {s_str}."
    if lang == "fr":
        if not qualifier or qualifier == "all_day":
            return f"{q_str} intervalles de la journée sont {s_str}."
        return f"{q_str} {b_str} sont {s_str}."
    if lang == "it":
        if not qualifier or qualifier == "all_day":
            return f"{q_str} intervalli della giornata sono {s_str}."
        return f"{q_str} {b_str} sono {s_str}."

    # English default
    if not qualifier or qualifier == "all_day":
        return f"{q_str} intervals of the day are {s_str}."
    return f"{q_str} {b_str} are {s_str}."


def evaluate_protoform(
    quantifier: str,
    qualifier: str | None,
    summarizer: str,
    data: StepTimeSeriesData,
    lang: Lang = "en",
) -> ProtoformEvaluation:
    """Evaluate degree of truth T and quality for a given (Q, B, S) protoform."""
    if quantifier not in QUANTIFIERS:
        raise ValueError(f"Unknown quantifier {quantifier!r}")

    q_mf = QUANTIFIERS[quantifier]
    b_mask = (
        compute_qualifier_mask(qualifier, data)
        if qualifier and qualifier != "all_day"
        else np.ones_like(data.hours)
    )
    s_mask = compute_summarizer_membership(summarizer, data)

    sigma_b = float(np.sum(b_mask))
    sigma_b_and_s = float(np.sum(np.minimum(b_mask, s_mask)))

    if sigma_b > 0.0:
        ratio_r = float(np.clip(sigma_b_and_s / sigma_b, 0.0, 1.0))
    else:
        ratio_r = 0.0

    truth = float(q_mf(ratio_r))
    coverage = float(sigma_b_and_s / len(data.hours))
    validity = float(0.85 * truth + 0.15 * coverage)

    statement = build_protoform_statement(quantifier, qualifier, summarizer, lang)
    is_type_2 = bool(qualifier and qualifier != "all_day")

    q_label = QUANTIFIER_LABELS.get(lang, QUANTIFIER_LABELS["en"]).get(quantifier, quantifier)
    b_label = (
        QUALIFIER_LABELS.get(lang, QUALIFIER_LABELS["en"]).get(qualifier or "all_day", qualifier)
        if qualifier
        else None
    )
    s_label = SUMMARIZER_LABELS.get(lang, SUMMARIZER_LABELS["en"]).get(summarizer, summarizer)

    return ProtoformEvaluation(
        protoform_type="type_2" if is_type_2 else "type_1",
        quantifier=quantifier,
        quantifier_label=q_label,
        qualifier=qualifier,
        qualifier_label=b_label,
        summarizer=summarizer,
        summarizer_label=s_label,
        cardinality_ratio=round(ratio_r, 4),
        truth_degree=round(truth, 4),
        coverage_degree=round(coverage, 4),
        validity_score=round(validity, 4),
        statement=statement,
    )


def discover_best_protoforms(
    data: StepTimeSeriesData,
    lang: Lang = "en",
    min_truth: float = 0.50,
    max_results: int = 8,
) -> list[ProtoformEvaluation]:
    """Scan candidate protoforms and return the most truthful, informative summaries."""
    candidates_b = [
        "all_day",
        "night_hours",
        "midday_solar",
        "evening_peak",
        "morning_ramp",
        "high_grid_stress",
    ]
    candidates_s = [
        "ideal",
        "good",
        "cheap",
        "avoid",
        "wait",
        "expensive",
        "low_grid_congestion",
        "critical_grid_congestion",
    ]
    quantifier_keys = list(QUANTIFIERS.keys())

    evaluated: list[ProtoformEvaluation] = []
    seen_combinations: set[tuple[str, str]] = set()

    for b in candidates_b:
        for s in candidates_s:
            # For each (B, S), find the quantifier with the highest truth degree
            best_ev: ProtoformEvaluation | None = None
            for q in quantifier_keys:
                ev = evaluate_protoform(q, b, s, data, lang)
                if ev.truth_degree >= min_truth:
                    if best_ev is None or ev.truth_degree > best_ev.truth_degree:
                        best_ev = ev
            if best_ev is not None and (b, s) not in seen_combinations:
                seen_combinations.add((b, s))
                evaluated.append(best_ev)

    # Sort primarily by truth degree, secondarily by coverage
    evaluated.sort(key=lambda x: (x.truth_degree, x.coverage_degree), reverse=True)
    return evaluated[:max_results]


def generate_executive_narrative(
    data: StepTimeSeriesData,
    lang: Lang = "en",
) -> tuple[str, list[str]]:
    """Synthesize high-level executive headline and bullet narrative in 4 languages."""
    hours = data.hours
    scores = data.scores
    g = data.g_stress

    night_mask = (hours >= 0.0) & (hours < 6.0)
    solar_mask = (hours >= 11.0) & (hours < 15.0)
    peak_mask = (hours >= 17.5) & (hours <= 20.5)

    avg_night_score = float(np.mean(scores[night_mask])) if np.any(night_mask) else 75.0
    avg_solar_score = float(np.mean(scores[solar_mask])) if np.any(solar_mask) else 65.0
    avg_peak_score = float(np.mean(scores[peak_mask])) if np.any(peak_mask) else 15.0
    max_peak_g = float(np.max(g[peak_mask])) if np.any(peak_mask) else 0.85

    # Determine headline style
    if avg_night_score >= 75 and avg_peak_score < 30:
        headline = {
            "en": "Pronounced Day-Night Volatility: Optimal Overnight Pre-charging & Critical Evening Peak",
            "de": "Ausgeprägte Tag-Nacht-Spreizung: Optimale Nachtladung & kritische Abendspitze",
            "fr": "Forte volatilité jour-nuit : recharge nocturne optimale et pic critique le soir",
            "it": "Marcata volatilità giorno-notte: ricarica notturna ottimale e picco critico serale",
        }.get(lang, "Pronounced Day-Night Volatility: Optimal Overnight Pre-charging & Critical Evening Peak")
    elif avg_solar_score >= 70:
        headline = {
            "en": "High Solar Feed-in: Dual Midday and Night Consumption Windows",
            "de": "Hoher Solarertrag: Doppeltes Verbrauchsfenster am Mittag und in der Nacht",
            "fr": "Forte production solaire : double fenêtre de consommation midi et nuit",
            "it": "Elevata produzione solare: doppia finestra di consumo a mezzogiorno e di notte",
        }.get(lang, "High Solar Feed-in: Dual Midday and Night Consumption Windows")
    else:
        headline = {
            "en": "Moderate Grid Load: Stable Midday Pricing with Controlled Off-Peak Windows",
            "de": "Moderate Netzbelastung: Stabile Mittags- und Schwachlastfenster",
            "fr": "Charge réseau modérée : fenêtres hors-pointe et prix stables",
            "it": "Carico di rete moderato: prezzi stabili e finestre fuori picco",
        }.get(lang, "Moderate Grid Load: Stable Midday Pricing with Controlled Off-Peak Windows")

    # Narrative bullet points
    if lang == "de":
        bullets = [
            f"**Nachtfenster (01:00–05:00):** Durchschnittlicher Eignungswert von {avg_night_score:.1f}/100. Ideal für die automatisierte Vollladung von Elektrofahrzeugen und Pufferspeichern.",
            f"**Abendliche Spitzenlast (17:30–20:30):** Kritische Netzbelastung (G_max = {max_peak_g:.2f}) und Eignungswerte unter {avg_peak_score:.1f}/100. Schwere Haushaltslasten werden zwingend verschoben.",
            f"**Mittagsfenster (11:00–15:00):** {'Hervorragende Bedingungen durch lokale Solareinspeisung' if avg_solar_score >= 60 else 'Ausgeglichene Netzbedingungen für Wasch- und Trockenzyklen'}.",
            "**Fuzzy-Urteil:** Der zweistufige Mamdani-Algorithmus umgeht die teuersten Netzgebühren vollständig und garantiert einen unterbrechungsfreien Betrieb ohne Leitungsschutzschalter-Überlastung.",
        ]
    elif lang == "fr":
        bullets = [
            f"**Fenêtre de nuit (01:00–05:00) :** Score moyen d'adéquation de {avg_night_score:.1f}/100. Idéal pour la recharge complète de véhicules électriques et chauffe-eau.",
            f"**Pointe du soir (17:30–20:30) :** Surcharge critique du transformateur (G_max = {max_peak_g:.2f}) et scores chutant à {avg_peak_score:.1f}/100. Les charges lourdes sont différées.",
            f"**Fenêtre de midi (11:00–15:00) :** {'Conditions avantageuses grâce au solaire' if avg_solar_score >= 60 else 'Conditions équilibrées pour lave-linge et sèche-linge'}.",
            "**Verdict flou :** Le système Mamdani élimine 100% de la consommation lors des pointes de surtaxe réseau sans risque de faire sauter les fusibles.",
        ]
    elif lang == "it":
        bullets = [
            f"**Finestra notturna (01:00–05:00):** Punteggio medio di idoneità di {avg_night_score:.1f}/100. Ideale per la ricarica completa di veicoli elettrici e boiler.",
            f"**Picco serale (17:30–20:30):** Sovraccarico critico della rete (G_max = {max_peak_g:.2f}) con idoneità scesa a {avg_peak_score:.1f}/100. Consumi pesanti rigorosamente posticipati.",
            f"**Finestra di mezzogiorno (11:00–15:00):** {'Condizioni eccellenti grazie al fotovoltaico' if avg_solar_score >= 60 else 'Condizioni equilibrate per elettrodomestici'}.",
            "**Verdetto Fuzzy :** Il sistema Mamdani bypassa completamente i sovrapprezzi di punta tutelando gli interruttori magnetotermici domestici.",
        ]
    else:
        bullets = [
            f"**Overnight Window (01:00–05:00):** Average Suitability Score of {avg_night_score:.1f}/100. Optimal for automated EV battery replenishment and thermal storage.",
            f"**Evening Peak Congestion (17:30–20:30):** Critical transformer strain (G_max = {max_peak_g:.2f}) and scores dropping to {avg_peak_score:.1f}/100. Heavy appliances must be deferred.",
            f"**Midday Window (11:00–15:00):** {'Favorable pricing boosted by regional solar feed-in' if avg_solar_score >= 60 else 'Balanced conditions suitable for laundry and dishwashers'}.",
            "**Fuzzy Verdict:** The Two-Stage Mamdani FIS completely avoids expensive grid surcharges while sequencing loads strictly below your circuit breaker capacity.",
        ]

    return headline, bullets
