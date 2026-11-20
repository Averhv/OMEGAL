"""Data models for laser-diffraction granulometer measurements and conditions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import numpy as np

from . import config


@dataclass
class Measurement:
    """Représente un export d'instrument unique.

    Attributes:
        name: Nom d'affichage de la mesure (ex: SF1_1611_1.5mL_30s_5W_63C 1).
        source: Chemin du fichier source ou référence Excel.
        diameter: Tableau NumPy des diamètres (µm).
        q: Tableau NumPy de la distribution différentielle q (%).
        passant: Tableau NumPy de la distribution cumulée Passant (%).
        stats: Dictionnaire des métadonnées extraites (D10, D50, D90, basis, etc.).
        group: Identifiant de groupe / condition (base du nom sans le réplicat).
        replicate: Identifiant du réplicat (ex: '1', '2', 'a').
        sample: Identifiant de l'échantillon principal (ex: 'SF1_1611').
        volume: Volume de suspension/solvant en mL.
        time: Durée de sonication en secondes.
        temperature: Traitement thermique optionnel (ex: '63C', '72C', None pour témoin).
        flags: Liste d'avertissements de qualité ou d'état de l'appareil.
    """
    name: str
    source: str
    diameter: "np.ndarray"
    q: "np.ndarray"
    passant: "np.ndarray"
    stats: dict
    group: str = ""
    replicate: str = ""
    sample: str = ""
    volume: Optional[float] = None
    time: Optional[float] = None
    temperature: Optional[str] = None
    flags: list = field(default_factory=list)

    @property
    def label(self) -> str:
        """Renvoie l'étiquette de légende personnalisée si définie, sinon name."""
        return config.CUSTOM_LEGEND_LABELS.get(self.name, self.name)


@dataclass
class Condition:
    """Regroupe un ensemble de réplicats partageant le même traitement expérimental.

    Attributes:
        name: Nom du groupe conditionnel.
        members: Liste des objets Measurement appartenant au groupe.
        sample: Nom de l'échantillon de base.
        volume: Volume en mL (si applicable).
        time: Temps de sonication en s (si applicable).
        temperature: Température de traitement thermique (ex: '63C', None pour ambiante).
    """
    name: str
    members: list
    sample: str
    volume: Optional[float]
    time: Optional[float]
    temperature: Optional[str] = None