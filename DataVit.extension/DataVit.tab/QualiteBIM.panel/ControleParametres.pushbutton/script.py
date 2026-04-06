"""
ControleParametres – Contrôle qualité des paramètres BIM obligatoires.

Vérifie que tous les éléments du projet possèdent leurs paramètres
obligatoires correctement renseignés, et affiche un rapport détaillé.
"""
from pyrevit import revit, script

from bim_quality import (
    REQUIRED_PARAMS_BY_CATEGORY,
    check_required_parameters,
    format_report_as_text,
)
from revit_utils import collect_model_elements

# ---------------------------------------------------------------------------
# Script principal
# ---------------------------------------------------------------------------

logger = script.get_logger()
output = script.get_output()

doc = revit.doc

output.print_md("## Contrôle des paramètres BIM obligatoires")
output.print_md(
    "Catégories contrôlées : **{}**".format(
        ", ".join(REQUIRED_PARAMS_BY_CATEGORY.keys())
    )
)

elements = collect_model_elements(doc)
output.print_md("Éléments analysés : **{}**".format(len(elements)))

report = check_required_parameters(elements)

if report.total == 0:
    output.print_md("⚠️ Aucun élément avec paramètres obligatoires trouvé.")
    script.exit()

score = (report.passed / report.total * 100) if report.total > 0 else 0
output.print_md(
    "**Score : {}/{} ({:.1f}%)**".format(report.passed, report.total, score)
)

if report.failed == 0:
    output.print_md("✅ Tous les paramètres obligatoires sont renseignés.")
else:
    output.print_md("❌ **{} problème(s) détecté(s)**".format(report.failed))
    output.print_md("")

    # Tableau des problèmes
    output.print_table(
        table_data=[
            [str(r.element_id), r.category, r.message]
            for r in report.results
            if not r.passed
        ],
        title="Paramètres manquants",
        columns=["ID Élément", "Catégorie", "Message"],
    )

    logger.warning(
        "Contrôle paramètres : %d problème(s) sur %d vérification(s)",
        report.failed,
        report.total,
    )
