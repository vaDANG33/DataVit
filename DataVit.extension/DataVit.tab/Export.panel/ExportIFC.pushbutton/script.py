"""
ExportIFC – Export rapide du projet courant en IFC.

Exporte le document Revit actif au format IFC2x3 dans le même dossier
que le modèle (ou sur le bureau si le modèle n'est pas encore sauvegardé).
"""
from pyrevit import revit, script

from ifc_exporter import (
    DEFAULT_EXPORT_CONFIG,
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

folder = get_default_export_folder(doc)
filename = get_default_export_filename(doc)

output.print_md("## Export IFC")
output.print_md("**Dossier :** `{}`".format(folder))
output.print_md("**Fichier  :** `{}.ifc`".format(filename))
output.print_md("**Version  :** `{}`".format(DEFAULT_EXPORT_CONFIG["ifc_version"]))

success, result = export_ifc(doc, folder, filename)

if success:
    output.print_md("✅ **Export réussi :** `{}`".format(result))
    logger.info("Export IFC réussi : %s", result)
else:
    output.print_md("❌ **Erreur d'export :** {}".format(result))
    logger.error("Erreur export IFC : %s", result)
