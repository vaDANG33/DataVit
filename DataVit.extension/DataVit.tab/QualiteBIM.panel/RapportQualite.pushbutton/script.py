"""
RapportQualite – Rapport de qualité BIM complet.

Exécute l'ensemble des contrôles qualité (paramètres, géométrie, nommage)
et génère un rapport consolidé exportable en fichier texte.
"""
import os

from pyrevit import forms, revit, script

from bim_quality import (
    build_quality_report,
    check_geometry_validity,
    check_naming_conventions,
    check_required_parameters,
    format_report_as_text,
)
from ifc_exporter import get_default_export_folder
from revit_utils import collect_model_elements, get_project_info

# ---------------------------------------------------------------------------
# Script principal
# ---------------------------------------------------------------------------

logger = script.get_logger()
output = script.get_output()

doc = revit.doc

output.print_md("## Rapport de qualité BIM")

# Informations du projet
try:
    proj = get_project_info(doc)
    output.print_md(
        "**Projet :** {} | **Numéro :** {} | **Client :** {}".format(
            proj.get("title", "–"),
            proj.get("number", "–"),
            proj.get("client", "–"),
        )
    )
except Exception:
    pass

# Collecte des éléments
elements = collect_model_elements(doc)
output.print_md("Éléments analysés : **{}**\n".format(len(elements)))

# Contrôles
output.print_md("### 1. Paramètres obligatoires")
report_params = check_required_parameters(elements)
_total_p = report_params.total or 1
output.print_md(
    "Score : **{}/{} ({:.1f}%)**".format(
        report_params.passed, report_params.total,
        report_params.passed / _total_p * 100,
    )
)

output.print_md("### 2. Géométrie")
report_geo = check_geometry_validity(elements)
_total_g = report_geo.total or 1
output.print_md(
    "Score : **{}/{} ({:.1f}%)**".format(
        report_geo.passed, report_geo.total,
        report_geo.passed / _total_g * 100,
    )
)

output.print_md("### 3. Nommage")
report_naming = check_naming_conventions(elements)
_total_n = report_naming.total or 1
output.print_md(
    "Score : **{}/{} ({:.1f}%)**".format(
        report_naming.passed, report_naming.total,
        report_naming.passed / _total_n * 100,
    )
)

# Rapport global
global_report = build_quality_report([report_params, report_geo, report_naming])
_total_all = global_report.total or 1
score_pct = global_report.passed / _total_all * 100

output.print_md("---")
output.print_md(
    "### Score global : **{}/{} ({:.1f}%)**".format(
        global_report.passed, global_report.total, score_pct
    )
)

all_problems = [r for r in global_report.results if not r.passed]
if all_problems:
    output.print_table(
        table_data=[
            [str(r.element_id), r.category, r.message]
            for r in all_problems
        ],
        title="Tous les problèmes détectés",
        columns=["ID Élément", "Catégorie", "Message"],
    )

# Proposition d'export du rapport
save = forms.ask_for_string(
    default="",
    prompt="Saisir un chemin pour sauvegarder le rapport (laisser vide pour ignorer) :",
    title="Exporter le rapport",
)

if save and save.strip():
    try:
        report_text = format_report_as_text(global_report, title="Rapport de qualité BIM")
        save_path = save.strip()
        if not save_path.lower().endswith(".txt"):
            save_path += ".txt"
        with open(save_path, "w", encoding="utf-8") as fh:
            fh.write(report_text)
        output.print_md("✅ Rapport sauvegardé : `{}`".format(save_path))
        logger.info("Rapport qualité BIM sauvegardé : %s", save_path)
    except Exception as exc:
        output.print_md("❌ Impossible de sauvegarder le rapport : {}".format(exc))
        logger.error("Erreur sauvegarde rapport : %s", exc)
