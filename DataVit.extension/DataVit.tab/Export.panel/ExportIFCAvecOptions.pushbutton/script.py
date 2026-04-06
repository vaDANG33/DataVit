"""
ExportIFCAvecOptions – Export IFC avec sélection des options.

Permet de choisir le dossier de destination, le nom du fichier et
la version IFC (IFC2x3 ou IFC4) via des boîtes de dialogue pyRevit.
"""
from pyrevit import forms, revit, script

from ifc_exporter import (
    IFC_VERSION_2X3,
    IFC_VERSION_4,
    SUPPORTED_IFC_VERSIONS,
    export_ifc,
    get_default_export_filename,
    get_default_export_folder,
)

# ---------------------------------------------------------------------------
# Script principal
# ---------------------------------------------------------------------------

logger = script.get_logger()
output = script.get_output()

doc = revit.doc

# --- Sélection du dossier ---------------------------------------------------
default_folder = get_default_export_folder(doc)
folder = forms.pick_folder(title="Sélectionner le dossier de destination IFC")
if not folder:
    script.exit()

# --- Saisie du nom de fichier -----------------------------------------------
default_name = get_default_export_filename(doc)
filename = forms.ask_for_string(
    default=default_name,
    prompt="Nom du fichier IFC (sans extension) :",
    title="Export IFC",
)
if not filename:
    script.exit()

# --- Sélection de la version IFC --------------------------------------------
version = forms.ask_for_one_item(
    list(SUPPORTED_IFC_VERSIONS),
    default=IFC_VERSION_2X3,
    prompt="Sélectionner la version IFC :",
    title="Export IFC",
)
if not version:
    script.exit()

# --- Export -----------------------------------------------------------------
config = {"ifc_version": version}

output.print_md("## Export IFC avec Options")
output.print_md("**Dossier :** `{}`".format(folder))
output.print_md("**Fichier  :** `{}.ifc`".format(filename))
output.print_md("**Version  :** `{}`".format(version))

success, result = export_ifc(doc, folder, filename, config=config)

if success:
    output.print_md("✅ **Export réussi :** `{}`".format(result))
    logger.info("Export IFC réussi : %s", result)
else:
    output.print_md("❌ **Erreur d'export :** {}".format(result))
    logger.error("Erreur export IFC : %s", result)
