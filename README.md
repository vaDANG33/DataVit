# DataVit

Extension pyRevit orientée Data + BIM pour Autodesk Revit.

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| **Export IFC** | Export rapide IFC2x3 ou IFC4 depuis le ruban Revit |
| **Contrôles qualité BIM** | Vérification des paramètres obligatoires, de la géométrie et des conventions de nommage |
| **Utilitaires Python partagés** | Bibliothèque `lib/` réutilisable dans tous les scripts pyRevit |

---

## Structure du projet

```
DataVit.extension/
├── extension.json                          # Métadonnées de l'extension
├── lib/                                    # Utilitaires Python partagés
│   ├── __init__.py
│   ├── ifc_exporter.py                     # Logique d'export IFC
│   ├── bim_quality.py                      # Contrôles qualité BIM
│   └── revit_utils.py                      # Wrappers API Revit
└── DataVit.tab/                            # Onglet du ruban Revit
    ├── Export.panel/
    │   ├── ExportIFC.pushbutton/           # Export IFC rapide
    │   └── ExportIFCAvecOptions.pushbutton/# Export IFC avec options
    └── QualiteBIM.panel/
        ├── ControleParametres.pushbutton/  # Contrôle des paramètres obligatoires
        ├── ControleGeometrie.pushbutton/   # Contrôle géométrie & nommage
        └── RapportQualite.pushbutton/      # Rapport de qualité complet

tests/
└── test_datavit.py                         # Tests unitaires (36 tests)
```

---

## Installation

1. Cloner ce dépôt dans le dossier `Extensions` de pyRevit :
   ```
   %APPDATA%\pyRevit\Extensions\DataVit.extension
   ```
   ou déclarer le chemin dans les paramètres pyRevit → *Manage Extensions*.

2. Recharger pyRevit depuis l'onglet **pyRevit** → **Reload**.

3. L'onglet **DataVit** apparaît dans le ruban Revit.

---

## Utilisation

### Export IFC

- **Exporter IFC** – exporte le modèle courant en IFC2x3 dans le même dossier que le fichier Revit.
- **Export IFC / Options** – sélectionner le dossier, le nom de fichier et la version IFC (IFC2x3 / IFC4 / IFC4x3).

### Qualité BIM

- **Contrôle Paramètres** – vérifie que les paramètres obligatoires (définis par catégorie) sont renseignés.
- **Contrôle Géométrie** – vérifie la validité des volumes/surfaces et les conventions de nommage.
- **Rapport Qualité** – rapport consolidé exportable en `.txt`.

---

## Développement & Tests

Les tests unitaires couvrent la logique pure des modules `lib/` sans nécessiter Revit.

```bash
python -m pytest tests/test_datavit.py -v
```

---

## Licence

MIT

