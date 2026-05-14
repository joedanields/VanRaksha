"""Species danger index values."""

SPECIES_DANGER_INDEX = {
    "tiger": {"danger": 10, "category": "predator"},
    "leopard": {"danger": 9, "category": "predator"},
    "elephant": {"danger": 9, "category": "megafauna"},
    "sloth_bear": {"danger": 8, "category": "predator"},
    "wild_boar": {"danger": 6, "category": "medium"},
    "gaur": {"danger": 7, "category": "megafauna"},
    "wolf": {"danger": 7, "category": "predator"},
    "hyena": {"danger": 6, "category": "predator"},
    "nilgai": {"danger": 3, "category": "herbivore"},
    "deer": {"danger": 1, "category": "herbivore"},
    "monkey": {"danger": 2, "category": "primate"},
    "peacock": {"danger": 1, "category": "bird"},
    "unknown": {"danger": 5, "category": "unknown"},
}

SPECIES_CLASS_NAMES = list(SPECIES_DANGER_INDEX.keys())


def get_danger_score(species: str) -> int:
    """Return danger score in range 1-10, defaulting to 5 for unknown species."""
    return int(SPECIES_DANGER_INDEX.get(species.lower(), SPECIES_DANGER_INDEX["unknown"])["danger"])


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info(
        "Species index self-test: %s %s", get_danger_score("tiger"), get_danger_score("mystery")
    )
