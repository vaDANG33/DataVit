"""
revit_utils.py – Utilitaires partagés pour l'API Revit.

Fournit des fonctions d'aide pour accéder aux éléments, paramètres
et informations du projet Revit via pyRevit.
"""
from collections import namedtuple

# ---------------------------------------------------------------------------
# Types de résultat
# ---------------------------------------------------------------------------
ParameterInfo = namedtuple("ParameterInfo", ["name", "value", "has_value"])
ElementInfo = namedtuple("ElementInfo", ["id", "category", "name", "parameters"])


# ---------------------------------------------------------------------------
# Informations sur le projet
# ---------------------------------------------------------------------------

def get_project_info(doc):
    """Retourne un dictionnaire avec les informations de base du projet.

    Args:
        doc: Document Revit actif (``revit.doc``).

    Returns:
        dict avec les clés ``title``, ``number``, ``client``, ``address``,
        ``author`` et ``organisation``.
    """
    info = doc.ProjectInformation
    return {
        "title": info.Name or "",
        "number": info.Number or "",
        "client": info.ClientName or "",
        "address": info.Address or "",
        "author": info.Author or "",
        "organisation": info.OrganizationName or "",
    }


# ---------------------------------------------------------------------------
# Collecte d'éléments
# ---------------------------------------------------------------------------

def collect_elements_by_category(doc, category):
    """Retourne tous les éléments d'une catégorie Revit donnée.

    Args:
        doc: Document Revit actif.
        category: ``DB.BuiltInCategory`` ou ``DB.Category``.

    Returns:
        ``list`` d'éléments Revit filtrés par catégorie.
    """
    from Autodesk.Revit import DB  # noqa: PLC0415  (import local intentionnel)

    collector = DB.FilteredElementCollector(doc)
    collector = collector.OfCategory(category)
    collector = collector.WhereElementIsNotElementType()
    return list(collector)


def collect_model_elements(doc):
    """Retourne tous les éléments du modèle (hors types).

    Args:
        doc: Document Revit actif.

    Returns:
        ``list`` d'éléments Revit du modèle.
    """
    from Autodesk.Revit import DB  # noqa: PLC0415

    collector = DB.FilteredElementCollector(doc)
    collector = collector.WhereElementIsNotElementType()
    return list(collector)


# ---------------------------------------------------------------------------
# Paramètres
# ---------------------------------------------------------------------------

def get_parameter_value(element, param_name):
    """Récupère la valeur d'un paramètre d'un élément Revit.

    Args:
        element: Élément Revit.
        param_name (str): Nom du paramètre.

    Returns:
        :class:`ParameterInfo` avec la valeur du paramètre ou ``None``.
    """
    param = element.LookupParameter(param_name)
    if param is None:
        return ParameterInfo(name=param_name, value=None, has_value=False)

    storage = param.StorageType
    try:
        from Autodesk.Revit import DB  # noqa: PLC0415

        if storage == DB.StorageType.String:
            val = param.AsString()
        elif storage == DB.StorageType.Integer:
            val = param.AsInteger()
        elif storage == DB.StorageType.Double:
            val = param.AsDouble()
        elif storage == DB.StorageType.ElementId:
            val = param.AsElementId()
        else:
            val = None
    except Exception:
        val = None

    has_value = val is not None and val != ""
    return ParameterInfo(name=param_name, value=val, has_value=has_value)


def get_element_name(element):
    """Retourne le nom d'un élément Revit.

    Args:
        element: Élément Revit.

    Returns:
        str – Nom de l'élément ou chaîne vide si indéfini.
    """
    try:
        from Autodesk.Revit import DB  # noqa: PLC0415

        return DB.Element.Name.GetValue(element) or ""
    except Exception:
        return ""


def element_to_info(element, param_names=None):
    """Convertit un élément Revit en :class:`ElementInfo`.

    Args:
        element: Élément Revit.
        param_names (list[str], optional): Liste de noms de paramètres à
            récupérer. Si ``None``, aucun paramètre n'est récupéré.

    Returns:
        :class:`ElementInfo`.
    """
    category = ""
    try:
        if element.Category:
            category = element.Category.Name
    except Exception:
        pass

    params = {}
    for name in (param_names or []):
        info = get_parameter_value(element, name)
        params[name] = info

    return ElementInfo(
        id=element.Id.IntegerValue,
        category=category,
        name=get_element_name(element),
        parameters=params,
    )
