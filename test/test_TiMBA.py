import unittest
import os
from pathlib import Path
import shutil
from TiMBA.data_management.DataManager import DataManager
from TiMBA.data_management.ParameterCollector import ParameterCollector
from TiMBA.data_validation.DataValidator import DataValidator
from TiMBA.main import run_timba
from TiMBA.user_io.default_parameters import user_input
from TiMBA.parameters.paths import (
    DATA_FOLDER, GIT_USER, GIT_REPO, GIT_BRANCH,
    GIT_FOLDER, DESTINATION_PATH, OUTPUT_DIR,INPUT_WORLD_PATH
)
from TiMBA.data_management.Load_Data import load_data
import importlib
import pkgutil
import TiMBA

INPUT_UNIT_TEST_TIMBA_RESULT = Path("test_data/DataContainer_Sc_scenario_input.pkl")

class TestTiMBAClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.PACKAGEDIR = Path(__file__).parent.absolute()
        cls.INPUT_FOLDER = cls.PACKAGEDIR / DESTINATION_PATH

        # Prepare parameters
        user_input["max_period"] = 1
        cls.Parameters = ParameterCollector(user_input=user_input)

        # load input data from GitHub AddInfo repo
        load_data(
            user=GIT_USER,
            repo=GIT_REPO,
            branch=GIT_BRANCH,
            source_folder=GIT_FOLDER,
            dest_folder=cls.INPUT_FOLDER
        )

        # run TiMBA
        run_timba(Parameters=cls.Parameters, folderpath=cls.PACKAGEDIR)

        # Load reference data
        cls.data_timba_test = DataManager.restore_from_pickle(cls.PACKAGEDIR / INPUT_UNIT_TEST_TIMBA_RESULT)

        # reload TiMBA results
        results_folder = cls.PACKAGEDIR / DATA_FOLDER / OUTPUT_DIR
        results_file = list(results_folder.glob("*.pkl"))[0]
        cls.data_timba = DataManager.restore_from_pickle(results_file)

    # def test_timba_results(self):
    #     """
    #     test TiMBA results against standard output
    #     """
    #     if user_input.get("test_timba_results", False):
    #         test_result = DataValidator.check_timba_results(
    #             Data=self.data_timba,
    #             DataTest=self.data_timba_test,
    #             rel_tolerance=5e-02
    #         )
    #         self.assertTrue(test_result, "TiMBA results are not in line with reference data.")

    def test_data_container(self):
        from TiMBA.parameters.Domains import Domains
        from TiMBA.data_management.DataManager import DataManager
        from TiMBA.data_management.DataContainer import DataContainer, InterfaceWorldData, WorldDataCollector
        cls = self.__class__

        INPUT_PATH = cls.PACKAGEDIR / DATA_FOLDER / INPUT_WORLD_PATH        
        world_version_unit_test = os.listdir(cls.PACKAGEDIR)[0]

        # Test DataContainer
        DC = DataContainer("test")
        self.assertIsInstance(DC, DataContainer)
        self.assertTrue(hasattr(DC, "filepath"))
        self.assertTrue(hasattr(DC, "data"))
        self.assertTrue(hasattr(DC, "domain"))
        self.assertTrue(DC.data.empty)
        self.assertIsNone(DC.domain)

        # Test InterfaceWorldData
        def bad_interface():
            InterfaceWorldData("test")
        self.assertRaises(TypeError, bad_interface)

        self.assertTrue(hasattr(InterfaceWorldData, "set_attribute"))
        self.assertTrue(issubclass(InterfaceWorldData, DataContainer))

        # Test WorldDataCollector
        self.assertTrue(issubclass(WorldDataCollector, (InterfaceWorldData, DataContainer)))
        self.assertTrue(hasattr(WorldDataCollector, "set_attribute"))

        # Test WorldDataCollector
        wdc_path = str(INPUT_PATH / world_version_unit_test)
        WDC = WorldDataCollector(wdc_path)

        self.assertFalse(hasattr(WDC, "attr_test_1"))
        DataManager.set_attribute(WDC, "attr_test_1", [1, 2, 3])
        self.assertTrue(hasattr(WDC, "attr_test_1"))
        self.assertEqual(WDC.attr_test_1, [1, 2, 3])
        self.assertEqual(WDC["attr_test_1"], [1, 2, 3])

        self.assertFalse(hasattr(WDC, "attr_test_2"))
        WDC["attr_test_2"] = [4, 5, 6]
        self.assertTrue(hasattr(WDC, "attr_test_2"))
        self.assertEqual(WDC.attr_test_2, [4, 5, 6])
        self.assertEqual(WDC["attr_test_2"], [4, 5, 6])

        # Test Domains
        domain_name = str(Domains.Specification)
        self.assertFalse(hasattr(WDC, domain_name))

        DataManager.set_attribute(WDC, domain_name, DataContainer(WDC.filepath))
        self.assertTrue(hasattr(WDC, domain_name))
        self.assertTrue(hasattr(WDC[domain_name], "data"))
        self.assertEqual(WDC.filepath, wdc_path)

        self.assertTrue(WDC[domain_name].data.empty)
        self.assertTrue(WDC.Specification.data.empty)

        # # Test import
        # WDC[domain_name].data = DataManager.read_excel(WDC.filepath, str(Domains.Specification))
        # comparison = DataManager.read_excel(WDC.filepath, str(Domains.Specification))
        # self.assertTrue(WDC[domain_name].data.compare(comparison).empty)

        # Test __repr__
        TEST_NAME = "TEST_NAME"
        INPUT_WORLD_PATH_LOOPED = wdc_path
        expected_repr = f"Content from {os.path.basename(INPUT_WORLD_PATH_LOOPED)}; Sheet: {TEST_NAME}"

        WDC[domain_name].update_domain_name(TEST_NAME)
        actual_repr = repr(WDC[domain_name]).replace("'", "")
        self.assertEqual(actual_repr, expected_repr)

    def test_import_all_timba_modules(self):
        """Automatically import all TiMBA submodules to satisfy coverage for imports."""
        package_path = Path(TiMBA.__file__).parent
        for _, module_name, _ in pkgutil.walk_packages([str(package_path)], TiMBA.__name__ + "."):
            importlib.import_module(module_name)


    @classmethod
    def tearDownClass(cls):
        tiMBA_path = cls.PACKAGEDIR / "TiMBA"
        if tiMBA_path.exists():
            shutil.rmtree(tiMBA_path)


if __name__ == '__main__':
    unittest.main()
