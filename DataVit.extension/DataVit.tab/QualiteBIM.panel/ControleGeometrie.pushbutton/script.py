# -*- coding: utf-8 -*-
"""
ControleGeometrie – Contrôle qualité de la géométrie et du nommage BIM.

Vérifie la validité des volumes/surfaces et les conventions de nommage
des éléments du modèle Revit courant.
"""
from pyrevit import revit, script

from bim_quality import (
    build_quality_report,
    check_geometry_validity,
    check_naming_conventions,
    format_report_as_text,
)
from revit_utils import collect_model_elements

# ---------------------------------------------------------------------------
# Script principal
# ---------------------------------------------------------------------------

logger = script.get_logger()
output = script.get_output()

doc = revit.doc

output.print_md("## Contrôle géométrie et nommage BIM")

elements = collect_model_elements(doc)
output.print_md("Éléments analysés : **{}**".format(len(elements)))

report_geo = check_geometry_validity(elements)
report_naming = check_naming_conventions(elements)
global_report = build_quality_report([report_geo, report_naming])

output.print_md(
    "**Géométrie  – Score : {}/{} ({:.1f}%)**".format(
        report_geo.passed,
        report_geo.total,
        (report_geo.passed / report_geo.total * 100) if report_geo.total else 0,
    )
)
output.print_md(
    "**Nommage    – Score : {}/{} ({:.1f}%)**".format(
        report_naming.passed,
        report_naming.total,
        (report_naming.passed / report_naming.total * 100) if report_naming.total else 0,
    )
)

problems = [r for r in global_report.results if not r.passed]
if not problems:
    output.print_md("✅ Aucun problème géométrique ou de nommage détecté.")
else:
    output.print_md("❌ **{} problème(s) détecté(s)**".format(len(problems)))
    output.print_table(
        table_data=[
            [str(r.element_id), r.category, r.message]
            for r in problems
        ],
        title="Problèmes détectés",
        columns=["ID Élément", "Catégorie", "Message"],
    )
    logger.warning(
        "Contrôle géométrie/nommage : %d problème(s) détecté(s)", len(problems)
    )
