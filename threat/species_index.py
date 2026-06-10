"""Species danger index values."""

# Each species entry:
#   danger      : 1-10 danger level (10 = most dangerous)
#   category    : ecological category
#   risk_label  : human-readable risk label shown in UI, voice, and logs
SPECIES_DANGER_INDEX = {
    "tiger":      {"danger": 10, "category": "predator",  "risk_label": "HIGH RISK – TIGER"},
    "leopard":    {"danger": 9,  "category": "predator",  "risk_label": "HIGH RISK – LEOPARD"},
    "elephant":   {"danger": 9,  "category": "megafauna", "risk_label": "HIGH RISK – ELEPHANT"},
    # "bear" = direct output from the new trained model (wildlife_combined.pt)
    "bear":       {"danger": 8,  "category": "predator",  "risk_label": "HIGH RISK – BEAR"},
    "sloth_bear": {"danger": 8,  "category": "predator",  "risk_label": "HIGH RISK – SLOTH BEAR"},
    "wild_boar":  {"danger": 6,  "category": "medium",    "risk_label": "MODERATE RISK – WILD BOAR"},
    "gaur":       {"danger": 7,  "category": "megafauna", "risk_label": "HIGH RISK – GAUR"},
    "wolf":       {"danger": 7,  "category": "predator",  "risk_label": "HIGH RISK – WOLF"},
    "hyena":      {"danger": 6,  "category": "predator",  "risk_label": "MODERATE RISK – HYENA"},
    "nilgai":     {"danger": 3,  "category": "herbivore", "risk_label": "LOW RISK – NILGAI"},
    "deer":       {"danger": 1,  "category": "herbivore", "risk_label": "LOW RISK – DEER"},
    "monkey":     {"danger": 2,  "category": "primate",   "risk_label": "LOW RISK – MONKEY"},
    "peacock":    {"danger": 1,  "category": "bird",      "risk_label": "LOW RISK – PEACOCK"},
    "unknown":    {"danger": 5,  "category": "unknown",   "risk_label": "UNKNOWN RISK"},
}

SPECIES_CLASS_NAMES = list(SPECIES_DANGER_INDEX.keys())


def get_danger_score(species: str) -> int:
    """Return danger score in range 1-10, defaulting to 5 for unknown species."""
    return int(SPECIES_DANGER_INDEX.get(species.lower(), SPECIES_DANGER_INDEX["unknown"])["danger"])


def get_risk_label(species: str) -> str:
    """Return the human-readable risk label for a species (e.g. 'HIGH RISK – TIGER')."""
    return SPECIES_DANGER_INDEX.get(species.lower(), SPECIES_DANGER_INDEX["unknown"])["risk_label"]


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info(
        "Species index self-test: %s %s", get_danger_score("tiger"), get_danger_score("mystery")
    )
