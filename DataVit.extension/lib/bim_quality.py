# -*- coding: utf-8 -*-
"""
bim_quality.py – Contrôles qualité des données BIM.

Fournit des fonctions de vérification de la qualité des données BIM :
- Complétude des paramètres obligatoires
- Conventions de nommage
- Cohérence géométrique
- Génération de rapports de qualité
"""
from collections import namedtuple

# ---------------------------------------------------------------------------
# Types de résultat
# ---------------------------------------------------------------------------
CheckResult = namedtuple("CheckResult", ["passed", "element_id", "category", "message"])
QualityReport = namedtuple("QualityReport", ["total", "passed", "failed", "results"])


# ---------------------------------------------------------------------------
# Paramètres BIM obligatoires par catégorie
# ---------------------------------------------------------------------------

REQUIRED_PARAMS_BY_CATEGORY = {
    "Murs": ["Type Comments", "Description"],
    "Portes": ["Mark", "Comments"],
    "Fenêtres": ["Mark", "Comments"],
    "Sols": ["Type Comments", "Description"],
    "Plafonds": ["Type Comments"],
    "Toits": ["Type Comments", "Description"],
    "Escaliers": ["Mark", "Comments"],
    "Colonnes": ["Mark", "Comments"],
    "Poutres structurelles": ["Mark", "Comments"],
    "Piliers": ["Mark", "Comments"],
    "Tuyaux": ["Mark", "System Name"],
    "Conduits": ["Mark", "System Name"],
    "Appareils mécaniques": ["Mark", "Comments"],
}

NAMING_FORBIDDEN_CHARS = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
NAMING_MAX_LENGTH = 100


# ---------------------------------------------------------------------------
# Vérifications des paramètres
# ---------------------------------------------------------------------------

def check_required_parameters(elements, required_params=None):
    """Vérifie que les éléments possèdent les paramètres obligatoires renseignés.

    Args:
        elements (list): Liste d'éléments Revit.
        required_params (dict, optional): Dictionnaire ``{catégorie: [params]}``.
            Si ``None``, utilise :data:`REQUIRED_PARAMS_BY_CATEGORY`.

    Returns:
        :class:`QualityReport`.
    """
    if required_params is None:
        required_params = REQUIRED_PARAMS_BY_CATEGORY

    results = []
    for element in elements:
        cat_name = ""
        try:
            if element.Category:
                cat_name = element.Category.Name
        except Exception:
            pass

        params_to_check = required_params.get(cat_name, [])
        for param_name in params_to_check:
            param = element.LookupParameter(param_name)
            passed = _parameter_has_value(param)
            elem_id = _safe_id(element)
            if passed:
                msg = "Paramètre '{}' renseigné".format(param_name)
            else:
                msg = "Paramètre obligatoire '{}' manquant ou vide".format(param_name)
            results.append(
                CheckResult(
                    passed=passed,
                    element_id=elem_id,
                    category=cat_name,
                    message=msg,
                )
            )

    return _build_report(results)


def _parameter_has_value(param):
    """Retourne True si un paramètre existe et possède une valeur non vide."""
    if param is None:
        return False
    try:
        from Autodesk.Revit import DB  # noqa: PLC0415

        storage = param.StorageType
        if storage == DB.StorageType.String:
            val = param.AsString()
            return bool(val and val.strip())
        elif storage == DB.StorageType.Integer:
            return param.AsInteger() != 0
        elif storage == DB.StorageType.Double:
            return True
        elif storage == DB.StorageType.ElementId:
            eid = param.AsElementId()
            return eid is not None and eid.IntegerValue != -1
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Vérifications du nommage
# ---------------------------------------------------------------------------

def check_naming_conventions(elements, forbidden_chars=None, max_length=None):
    """Vérifie les conventions de nommage des éléments.

    Les règles appliquées :
    - Le nom ne doit pas être vide.
    - Le nom ne doit pas contenir de caractères interdits.
    - Le nom ne doit pas dépasser la longueur maximale autorisée.

    Args:
        elements (list): Liste d'éléments Revit.
        forbidden_chars (list[str], optional): Caractères interdits dans les noms.
            Par défaut :data:`NAMING_FORBIDDEN_CHARS`.
        max_length (int, optional): Longueur maximale du nom.
            Par défaut :data:`NAMING_MAX_LENGTH`.

    Returns:
        :class:`QualityReport`.
    """
    if forbidden_chars is None:
        forbidden_chars = NAMING_FORBIDDEN_CHARS
    if max_length is None:
        max_length = NAMING_MAX_LENGTH

    results = []
    for element in elements:
        cat_name = _safe_category(element)
        name = _safe_name(element)
        elem_id = _safe_id(element)

        if not name or not name.strip():
            results.append(
                CheckResult(
                    passed=False,
                    element_id=elem_id,
                    category=cat_name,
                    message="Nom vide ou non défini",
                )
            )
            continue

        bad_chars = [c for c in forbidden_chars if c in name]
        if bad_chars:
            results.append(
                CheckResult(
                    passed=False,
                    element_id=elem_id,
                    category=cat_name,
                    message="Nom contient des caractères interdits : {}".format(
                        ", ".join(repr(c) for c in bad_chars)
                    ),
                )
            )
            continue

        if len(name) > max_length:
            results.append(
                CheckResult(
                    passed=False,
                    element_id=elem_id,
                    category=cat_name,
                    message="Nom trop long ({} caractères, max {})".format(
                        len(name), max_length
                    ),
                )
            )
            continue

        results.append(
            CheckResult(
                passed=True,
                element_id=elem_id,
                category=cat_name,
                message="Nommage conforme",
            )
        )

    return _build_report(results)


# ---------------------------------------------------------------------------
# Vérifications géométriques
# ---------------------------------------------------------------------------

def check_geometry_validity(elements):
    """Vérifie la validité géométrique des éléments (volume et surface).

    Signale les éléments dont le volume ou la surface est nul ou négatif.

    Args:
        elements (list): Liste d'éléments Revit.

    Returns:
        :class:`QualityReport`.
    """
    results = []
    for element in elements:
        cat_name = _safe_category(element)
        elem_id = _safe_id(element)

        volume = _get_double_param(element, "Volume")
        area = _get_double_param(element, "Area")

        if volume is not None and volume < 0:
            results.append(
                CheckResult(
                    passed=False,
                    element_id=elem_id,
                    category=cat_name,
                    message="Volume négatif détecté ({:.4f})".format(volume),
                )
            )
        elif area is not None and area < 0:
            results.append(
                CheckResult(
                    passed=False,
                    element_id=elem_id,
                    category=cat_name,
                    message="Surface négative détectée ({:.4f})".format(area),
                )
            )
        else:
            results.append(
                CheckResult(
                    passed=True,
                    element_id=elem_id,
                    category=cat_name,
                    message="Géométrie valide",
                )
            )

    return _build_report(results)


def _get_double_param(element, param_name):
    """Retourne la valeur double d'un paramètre, ou None si inexistant."""
    try:
        param = element.LookupParameter(param_name)
        if param is None:
            return None
        from Autodesk.Revit import DB  # noqa: PLC0415

        if param.StorageType == DB.StorageType.Double:
            return param.AsDouble()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Rapport de qualité
# ---------------------------------------------------------------------------

def build_quality_report(reports):
    """Consolide plusieurs rapports en un rapport global.

    Args:
        reports (list[:class:`QualityReport`]): Liste de rapports individuels.

    Returns:
        :class:`QualityReport` consolidé.
    """
    all_results = []
    for report in reports:
        all_results.extend(report.results)
    return _build_report(all_results)


def format_report_as_text(report, title="Rapport de qualité BIM"):
    """Formate un rapport de qualité en texte lisible.

    Args:
        report (:class:`QualityReport`): Rapport à formater.
        title (str): Titre du rapport.

    Returns:
        str – Texte formaté du rapport.
    """
    lines = [
        title,
        "=" * len(title),
        "Total   : {}".format(report.total),
        "Réussi  : {}".format(report.passed),
        "Échec   : {}".format(report.failed),
        "",
    ]
    failed = [r for r in report.results if not r.passed]
    if failed:
        lines.append("Problèmes détectés :")
        lines.append("-" * 20)
        for r in failed:
            lines.append(
                "  [ID {}] {} – {}".format(r.element_id, r.category, r.message)
            )
    else:
        lines.append("Aucun problème détecté.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _build_report(results):
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    return QualityReport(total=total, passed=passed, failed=failed, results=results)


def _safe_id(element):
    try:
        return element.Id.IntegerValue
    except Exception:
        return -1


def _safe_category(element):
    try:
        if element.Category:
            return element.Category.Name
    except Exception:
        pass
    return ""


def _safe_name(element):
    try:
        from Autodesk.Revit import DB  # noqa: PLC0415

        return DB.Element.Name.GetValue(element) or ""
    except Exception:
        pass
    try:
        return element.Name or ""
    except Exception:
        return ""
