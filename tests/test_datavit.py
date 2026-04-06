"""
Tests unitaires pour DataVit.extension/lib/

Ces tests utilisent des mocks pour simuler l'API Revit (non disponible
en dehors de Revit). Ils couvrent la logique pure des modules :
  - ifc_exporter
  - bim_quality
  - revit_utils
"""
import sys
import types
import unittest

# ---------------------------------------------------------------------------
# Mock de l'API Revit (Autodesk.Revit.DB) et de pyRevit
# Doit être fait avant tout import des modules testés
# ---------------------------------------------------------------------------

def _make_revit_stubs():
    """Crée des stubs minimaux pour Autodesk.Revit.DB."""

    # Stub StorageType
    StorageType = types.SimpleNamespace(
        String=0,
        Integer=1,
        Double=2,
        ElementId=3,
    )

    # Stub IFCVersion
    IFCVersion = types.SimpleNamespace(
        IFC2x3="IFC2x3",
        IFC4="IFC4",
    )

    class _ElementId:
        def __init__(self, val=-1):
            self.IntegerValue = val

    class _IFCExportOptions:
        def __init__(self):
            self.FileVersion = IFCVersion.IFC2x3
            self.ExportLinkedFiles = False
            self.ExportBaseQuantities = True
            self.WallAndColumnSplitting = False
            self.SpaceBoundaryLevel = 0
            self.FilterViewId = None

    DB = types.ModuleType("Autodesk.Revit.DB")
    DB.StorageType = StorageType
    DB.IFCVersion = IFCVersion
    DB.IFCExportOptions = _IFCExportOptions
    DB.ElementId = _ElementId

    # Stub FilteredElementCollector
    class _FEC:
        def __init__(self, doc):
            self._elements = list(getattr(doc, "_elements", []))

        def OfCategory(self, cat):
            return self

        def WhereElementIsNotElementType(self):
            return self

        def __iter__(self):
            return iter(self._elements)

    DB.FilteredElementCollector = _FEC

    # Element.Name helper
    class _ElementMeta:
        @staticmethod
        def Name():
            pass

    class _Element:
        Name = types.SimpleNamespace(GetValue=lambda e: getattr(e, "Name", ""))

    DB.Element = _Element

    # Register modules
    autodesk = types.ModuleType("Autodesk")
    autodesk_revit = types.ModuleType("Autodesk.Revit")
    autodesk.Revit = autodesk_revit
    autodesk_revit.DB = DB

    sys.modules.setdefault("Autodesk", autodesk)
    sys.modules.setdefault("Autodesk.Revit", autodesk_revit)
    sys.modules.setdefault("Autodesk.Revit.DB", DB)
    return DB


DB = _make_revit_stubs()

# Make lib/ importable
import os
LIB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "DataVit.extension", "lib"
)
sys.path.insert(0, os.path.abspath(LIB_PATH))

import bim_quality
import ifc_exporter
import revit_utils


# ===========================================================================
# Helpers – objets Revit factices
# ===========================================================================

class _FakeParam:
    """Paramètre Revit factice."""

    def __init__(self, storage_type, value):
        self.StorageType = storage_type
        self._value = value

    def AsString(self):
        return self._value if self.StorageType == DB.StorageType.String else None

    def AsInteger(self):
        return self._value if self.StorageType == DB.StorageType.Integer else 0

    def AsDouble(self):
        return self._value if self.StorageType == DB.StorageType.Double else 0.0

    def AsElementId(self):
        if self.StorageType == DB.StorageType.ElementId:
            return DB.ElementId(self._value)
        return DB.ElementId(-1)


class _FakeCategory:
    def __init__(self, name):
        self.Name = name


class _FakeElementId:
    def __init__(self, val):
        self.IntegerValue = val


class _FakeElement:
    """Élément Revit factice."""

    def __init__(self, elem_id, category_name="", name="", params=None):
        self.Id = _FakeElementId(elem_id)
        self.Category = _FakeCategory(category_name) if category_name else None
        self.Name = name
        self._params = params or {}

    def LookupParameter(self, param_name):
        return self._params.get(param_name)


# ===========================================================================
# Tests – ifc_exporter
# ===========================================================================

class TestValidateExportPath(unittest.TestCase):

    def test_valid_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            ok, result = ifc_exporter.validate_export_path(tmpdir, "myfile")
            self.assertTrue(ok)
            self.assertTrue(result.endswith(".ifc"))

    def test_empty_folder(self):
        ok, msg = ifc_exporter.validate_export_path("", "myfile")
        self.assertFalse(ok)
        self.assertIn("vide", msg)

    def test_nonexistent_folder(self):
        ok, msg = ifc_exporter.validate_export_path("/nonexistent/path/xyz", "myfile")
        self.assertFalse(ok)
        self.assertIn("inexistant", msg)

    def test_empty_filename(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            ok, msg = ifc_exporter.validate_export_path(tmpdir, "")
            self.assertFalse(ok)
            self.assertIn("vide", msg)

    def test_filename_with_forbidden_chars(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            ok, msg = ifc_exporter.validate_export_path(tmpdir, "bad:name")
            self.assertFalse(ok)

    def test_ifc_extension_appended(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            ok, result = ifc_exporter.validate_export_path(tmpdir, "model.ifc")
            self.assertTrue(ok)
            self.assertEqual(result.count(".ifc"), 1)


class TestValidateIfcVersion(unittest.TestCase):

    def test_supported_versions(self):
        for v in ifc_exporter.SUPPORTED_IFC_VERSIONS:
            ok, _ = ifc_exporter.validate_ifc_version(v)
            self.assertTrue(ok, msg="Version {} devrait être supportée".format(v))

    def test_unsupported_version(self):
        ok, msg = ifc_exporter.validate_ifc_version("IFC1.0")
        self.assertFalse(ok)
        self.assertIn("non supportée", msg)


class TestGetDefaultExportFilename(unittest.TestCase):

    def _make_doc(self, title):
        doc = types.SimpleNamespace(Title=title)
        return doc

    def test_normal_title(self):
        doc = self._make_doc("Mon Projet Revit")
        name = ifc_exporter.get_default_export_filename(doc)
        self.assertEqual(name, "Mon Projet Revit")

    def test_title_with_forbidden_chars(self):
        doc = self._make_doc("Projet:Test/Export")
        name = ifc_exporter.get_default_export_filename(doc)
        self.assertNotIn(":", name)
        self.assertNotIn("/", name)

    def test_empty_title_fallback(self):
        doc = self._make_doc("")
        name = ifc_exporter.get_default_export_filename(doc)
        self.assertEqual(name, "export")


class TestGetDefaultExportFolder(unittest.TestCase):

    def test_model_with_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = types.SimpleNamespace(PathName=os.path.join(tmpdir, "model.rvt"))
            folder = ifc_exporter.get_default_export_folder(doc)
            self.assertEqual(folder, tmpdir)

    def test_model_without_path(self):
        doc = types.SimpleNamespace(PathName="")
        folder = ifc_exporter.get_default_export_folder(doc)
        self.assertTrue(os.path.isdir(folder))


# ===========================================================================
# Tests – bim_quality
# ===========================================================================

class TestBimQualityHelpers(unittest.TestCase):

    def test_build_report_all_pass(self):
        results = [
            bim_quality.CheckResult(True, 1, "Murs", "ok"),
            bim_quality.CheckResult(True, 2, "Portes", "ok"),
        ]
        report = bim_quality._build_report(results)
        self.assertEqual(report.total, 2)
        self.assertEqual(report.passed, 2)
        self.assertEqual(report.failed, 0)

    def test_build_report_some_fail(self):
        results = [
            bim_quality.CheckResult(True, 1, "Murs", "ok"),
            bim_quality.CheckResult(False, 2, "Portes", "erreur"),
        ]
        report = bim_quality._build_report(results)
        self.assertEqual(report.total, 2)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)


class TestCheckNamingConventions(unittest.TestCase):

    def _elem(self, name, elem_id=1, category="Murs"):
        return _FakeElement(elem_id=elem_id, category_name=category, name=name)

    def test_valid_name(self):
        elem = self._elem("Mur extérieur")
        report = bim_quality.check_naming_conventions([elem])
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 0)

    def test_empty_name(self):
        elem = self._elem("")
        report = bim_quality.check_naming_conventions([elem])
        self.assertEqual(report.failed, 1)
        self.assertIn("vide", report.results[0].message.lower())

    def test_name_with_forbidden_char(self):
        elem = self._elem("Mur:invalide")
        report = bim_quality.check_naming_conventions([elem])
        self.assertEqual(report.failed, 1)

    def test_name_too_long(self):
        elem = self._elem("A" * 200)
        report = bim_quality.check_naming_conventions([elem])
        self.assertEqual(report.failed, 1)
        self.assertIn("long", report.results[0].message.lower())

    def test_multiple_elements(self):
        elems = [
            self._elem("Mur OK", 1),
            self._elem("Porte/Invalide", 2, "Portes"),
            self._elem("Fenêtre OK", 3, "Fenêtres"),
        ]
        report = bim_quality.check_naming_conventions(elems)
        self.assertEqual(report.total, 3)
        self.assertEqual(report.passed, 2)
        self.assertEqual(report.failed, 1)


class TestCheckRequiredParameters(unittest.TestCase):

    def test_all_params_present(self):
        param = _FakeParam(DB.StorageType.String, "Type A")
        elem = _FakeElement(
            elem_id=10,
            category_name="Murs",
            params={"Type Comments": param, "Description": param},
        )
        report = bim_quality.check_required_parameters(
            [elem],
            required_params={"Murs": ["Type Comments", "Description"]},
        )
        self.assertEqual(report.failed, 0)

    def test_missing_param(self):
        elem = _FakeElement(elem_id=11, category_name="Murs", params={})
        report = bim_quality.check_required_parameters(
            [elem],
            required_params={"Murs": ["Type Comments"]},
        )
        self.assertEqual(report.failed, 1)
        self.assertIn("manquant", report.results[0].message.lower())

    def test_empty_string_param_fails(self):
        param = _FakeParam(DB.StorageType.String, "")
        elem = _FakeElement(
            elem_id=12,
            category_name="Murs",
            params={"Type Comments": param},
        )
        report = bim_quality.check_required_parameters(
            [elem],
            required_params={"Murs": ["Type Comments"]},
        )
        self.assertEqual(report.failed, 1)

    def test_unknown_category_skipped(self):
        elem = _FakeElement(elem_id=13, category_name="UnknownCat", params={})
        report = bim_quality.check_required_parameters(
            [elem],
            required_params={"Murs": ["Type Comments"]},
        )
        self.assertEqual(report.total, 0)


class TestCheckGeometryValidity(unittest.TestCase):

    def test_positive_volume(self):
        param = _FakeParam(DB.StorageType.Double, 10.0)
        elem = _FakeElement(10, "Murs", params={"Volume": param})
        report = bim_quality.check_geometry_validity([elem])
        self.assertEqual(report.passed, 1)

    def test_negative_volume_fails(self):
        param = _FakeParam(DB.StorageType.Double, -1.0)
        elem = _FakeElement(11, "Murs", params={"Volume": param})
        report = bim_quality.check_geometry_validity([elem])
        self.assertEqual(report.failed, 1)
        self.assertIn("négatif", report.results[0].message.lower())

    def test_no_geometry_param_passes(self):
        elem = _FakeElement(12, "Murs", params={})
        report = bim_quality.check_geometry_validity([elem])
        self.assertEqual(report.passed, 1)


class TestBuildQualityReport(unittest.TestCase):

    def test_consolidation(self):
        r1 = bim_quality._build_report([
            bim_quality.CheckResult(True, 1, "Murs", "ok"),
            bim_quality.CheckResult(False, 2, "Portes", "ko"),
        ])
        r2 = bim_quality._build_report([
            bim_quality.CheckResult(True, 3, "Fenêtres", "ok"),
        ])
        combined = bim_quality.build_quality_report([r1, r2])
        self.assertEqual(combined.total, 3)
        self.assertEqual(combined.passed, 2)
        self.assertEqual(combined.failed, 1)


class TestFormatReportAsText(unittest.TestCase):

    def test_no_failures(self):
        results = [bim_quality.CheckResult(True, 1, "Murs", "ok")]
        report = bim_quality._build_report(results)
        text = bim_quality.format_report_as_text(report)
        self.assertIn("Aucun problème", text)

    def test_with_failure(self):
        results = [bim_quality.CheckResult(False, 2, "Portes", "Problème X")]
        report = bim_quality._build_report(results)
        text = bim_quality.format_report_as_text(report)
        self.assertIn("Problème X", text)
        self.assertIn("Portes", text)


# ===========================================================================
# Tests – revit_utils
# ===========================================================================

class TestRevitUtils(unittest.TestCase):

    def test_safe_id(self):
        elem = _FakeElement(42)
        self.assertEqual(bim_quality._safe_id(elem), 42)

    def test_safe_category(self):
        elem = _FakeElement(1, category_name="Murs")
        # revit_utils._safe_category uses element.Category.Name
        cat = elem.Category.Name if elem.Category else ""
        self.assertEqual(cat, "Murs")

    def test_get_parameter_value_string(self):
        param = _FakeParam(DB.StorageType.String, "Béton")
        elem = _FakeElement(1, params={"Matériau": param})
        info = revit_utils.get_parameter_value(elem, "Matériau")
        self.assertTrue(info.has_value)
        self.assertEqual(info.value, "Béton")

    def test_get_parameter_value_missing(self):
        elem = _FakeElement(1, params={})
        info = revit_utils.get_parameter_value(elem, "Matériau")
        self.assertFalse(info.has_value)
        self.assertIsNone(info.value)

    def test_get_parameter_value_empty_string(self):
        param = _FakeParam(DB.StorageType.String, "")
        elem = _FakeElement(1, params={"Matériau": param})
        info = revit_utils.get_parameter_value(elem, "Matériau")
        self.assertFalse(info.has_value)

    def test_element_to_info(self):
        param = _FakeParam(DB.StorageType.String, "Valeur")
        elem = _FakeElement(99, "Murs", "Mur Nord", {"Mark": param})
        info = revit_utils.element_to_info(elem, param_names=["Mark"])
        self.assertEqual(info.id, 99)
        self.assertEqual(info.category, "Murs")
        self.assertIn("Mark", info.parameters)
        self.assertTrue(info.parameters["Mark"].has_value)


if __name__ == "__main__":
    unittest.main()
