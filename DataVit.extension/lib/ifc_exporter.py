# -*- coding: utf-8 -*-
"""
ifc_exporter.py – Utilitaires d'export IFC pour Revit.

Fournit des fonctions pour configurer et exécuter l'export IFC depuis Revit,
avec validation pré-export et gestion des options IFC2x3 / IFC4.
"""
import os

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

IFC_VERSION_2X3 = "IFC2x3"
IFC_VERSION_4 = "IFC4"

# IFC4x3 n'est pas supporté nativement par l'API Revit IFCExportOptions.
# Il nécessite le plugin Open Source IFC Exporter. Seuls IFC2x3 et IFC4
# sont disponibles via DB.IFCVersion.
SUPPORTED_IFC_VERSIONS = (IFC_VERSION_2X3, IFC_VERSION_4)

DEFAULT_EXPORT_CONFIG = {
    "ifc_version": IFC_VERSION_2X3,
    "export_linked_files": False,
    "export_base_quantities": True,
    "export_solid_model_rep": False,
    "use_family_and_type_name_for_reference": True,
    "use_active_view_geometry": False,
    "export_rooms_in_3d_view": False,
    "export_bounding_box": False,
    "wall_and_column_splitter": False,
    "split_walls_and_columns_by_level": False,
    "include_site_elevation": False,
    "use_coarse_tessellation": True,
    "store_ifc_guid": True,
}


# ---------------------------------------------------------------------------
# Validation pré-export
# ---------------------------------------------------------------------------

def validate_export_path(folder_path, filename):
    """Vérifie que le chemin de destination est valide.

    Args:
        folder_path (str): Dossier de destination.
        filename (str): Nom du fichier IFC (avec ou sans extension).

    Returns:
        tuple[bool, str]: (valide, message d'erreur ou chemin complet).
    """
    if not folder_path:
        return False, "Le dossier de destination est vide."
    if not os.path.isdir(folder_path):
        return False, "Dossier de destination inexistant : '{}'".format(folder_path)

    if not filename:
        return False, "Le nom de fichier est vide."

    clean_name = filename if filename.lower().endswith(".ifc") else filename + ".ifc"
    forbidden = set(['\\', '/', ':', '*', '?', '"', '<', '>', '|'])
    bad_chars = [c for c in os.path.basename(clean_name) if c in forbidden]
    if bad_chars:
        return False, "Nom de fichier contient des caractères invalides : {}".format(
            ", ".join(repr(c) for c in bad_chars)
        )

    full_path = os.path.join(folder_path, clean_name)
    return True, full_path


def validate_ifc_version(version):
    """Vérifie que la version IFC demandée est supportée.

    Args:
        version (str): Chaîne de version IFC (ex. ``"IFC2x3"``).

    Returns:
        tuple[bool, str]: (valide, message).
    """
    if version in SUPPORTED_IFC_VERSIONS:
        return True, "Version IFC '{}' supportée.".format(version)
    return False, "Version IFC '{}' non supportée. Versions acceptées : {}".format(
        version, ", ".join(SUPPORTED_IFC_VERSIONS)
    )


# ---------------------------------------------------------------------------
# Création des options IFC
# ---------------------------------------------------------------------------

def build_ifc_export_options(config=None):
    """Construit l'objet ``IFCExportOptions`` à partir d'une configuration.

    Args:
        config (dict, optional): Dictionnaire de configuration.
            Fusionne avec :data:`DEFAULT_EXPORT_CONFIG`.

    Returns:
        ``DB.IFCExportOptions`` configuré.

    Raises:
        ImportError: Si l'API Revit n'est pas disponible.
    """
    from Autodesk.Revit import DB  # noqa: PLC0415

    cfg = dict(DEFAULT_EXPORT_CONFIG)
    if config:
        cfg.update(config)

    opts = DB.IFCExportOptions()

    # Version IFC (seules IFC2x3 et IFC4 sont supportées via DB.IFCVersion)
    version_map = {
        IFC_VERSION_2X3: DB.IFCVersion.IFC2x3,
        IFC_VERSION_4: DB.IFCVersion.IFC4,
    }
    opts.FileVersion = version_map.get(cfg["ifc_version"], DB.IFCVersion.IFC2x3)

    opts.ExportLinkedFiles = cfg["export_linked_files"]
    opts.ExportBaseQuantities = cfg["export_base_quantities"]
    opts.WallAndColumnSplitting = cfg["split_walls_and_columns_by_level"]
    opts.SpaceBoundaryLevel = 0

    return opts


# ---------------------------------------------------------------------------
# Export IFC
# ---------------------------------------------------------------------------

def export_ifc(doc, folder_path, filename, config=None):
    """Exporte le document Revit courant en IFC.

    Args:
        doc: Document Revit actif (``revit.doc``).
        folder_path (str): Dossier de destination de l'export.
        filename (str): Nom du fichier IFC (sans extension).
        config (dict, optional): Options d'export (voir :data:`DEFAULT_EXPORT_CONFIG`).

    Returns:
        tuple[bool, str]: (succès, message ou chemin du fichier exporté).
    """
    valid, result = validate_export_path(folder_path, filename)
    if not valid:
        return False, result

    full_path = result
    export_filename = os.path.basename(full_path)

    cfg = dict(DEFAULT_EXPORT_CONFIG)
    if config:
        cfg.update(config)

    version_ok, version_msg = validate_ifc_version(cfg["ifc_version"])
    if not version_ok:
        return False, version_msg

    try:
        opts = build_ifc_export_options(cfg)
        doc.Export(folder_path, export_filename, opts)
        return True, full_path
    except Exception as exc:
        return False, "Erreur lors de l'export IFC : {}".format(exc)


def export_ifc_by_view(doc, view, folder_path, filename, config=None):
    """Exporte une vue spécifique en IFC.

    Args:
        doc: Document Revit actif.
        view: Vue Revit à exporter (``DB.View``).
        folder_path (str): Dossier de destination.
        filename (str): Nom du fichier IFC (sans extension).
        config (dict, optional): Options d'export.

    Returns:
        tuple[bool, str]: (succès, message ou chemin du fichier exporté).
    """
    valid, result = validate_export_path(folder_path, filename)
    if not valid:
        return False, result

    full_path = result
    export_filename = os.path.basename(full_path)

    cfg = dict(DEFAULT_EXPORT_CONFIG)
    if config:
        cfg.update(config)

    try:
        opts = build_ifc_export_options(cfg)
        opts.FilterViewId = view.Id
        doc.Export(folder_path, export_filename, opts)
        return True, full_path
    except Exception as exc:
        return False, "Erreur lors de l'export IFC par vue : {}".format(exc)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def get_default_export_folder(doc):
    """Retourne le dossier par défaut pour l'export IFC.

    Utilise le répertoire du modèle Revit, ou le bureau de l'utilisateur
    si le modèle n'a pas encore été sauvegardé.

    Args:
        doc: Document Revit actif.

    Returns:
        str – Chemin du dossier par défaut.
    """
    try:
        model_path = doc.PathName
        if model_path:
            return os.path.dirname(model_path)
    except Exception:
        pass

    return os.path.expanduser("~")


def get_default_export_filename(doc):
    """Retourne le nom de fichier par défaut pour l'export IFC.

    Basé sur le titre du projet Revit, nettoyé des caractères invalides.

    Args:
        doc: Document Revit actif.

    Returns:
        str – Nom de fichier sans extension.
    """
    try:
        title = doc.Title or "export"
    except Exception:
        title = "export"

    forbidden = set('\\/:*?"<>|')
    clean = "".join(c if c not in forbidden else "_" for c in title)
    return clean.strip() or "export"
