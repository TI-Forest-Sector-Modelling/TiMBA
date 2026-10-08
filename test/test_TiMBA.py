import unittest
import os
from pathlib import Path
import shutil
from TiMBA.main import run_timba
from TiMBA.data_management.DataManager import DataManager
from TiMBA.data_management.ParameterCollector import ParameterCollector
from TiMBA.data_validation.DataValidator import DataValidator
from TiMBA.user_io.default_parameters import user_input
from TiMBA.parameters.paths import (
    DATA_FOLDER, GIT_USER, GIT_REPO, GIT_BRANCH,
    GIT_FOLDER, DESTINATION_PATH, OUTPUT_DIR, INPUT_WORLD_PATH
)
from TiMBA.data_management.Load_Data import check_and_load_data
import importlib
import pkgutil
import TiMBA

from click.testing import CliRunner
from unittest.mock import patch
from TiMBA.cli.cli import cli

INPUT_UNIT_TEST_TIMBA_RESULT = Path(
    "test_data/DataContainer_Sc_scenario_input.pkl"
    )


class TestTiMBAClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.PACKAGEDIR = Path(__file__).parent.absolute()
        cls.INPUT_FOLDER = cls.PACKAGEDIR / DESTINATION_PATH

        # Prepare parameters
        user_input["max_period"] = 1
        cls.Parameters = ParameterCollector(user_input=user_input)

        # load input data
        check_and_load_data(
            user=GIT_USER,
            repo=GIT_REPO,
            branch=GIT_BRANCH,
            source_folder=GIT_FOLDER,
            dest_folder=cls.INPUT_FOLDER,
            check_flag=True,
            load_flag=True
        )

        # run TiMBA
        run_timba(Parameters=cls.Parameters, folderpath=cls.PACKAGEDIR)

        # Load reference data
        cls.data_timba_test = DataManager.restore_from_pickle(
            cls.PACKAGEDIR / INPUT_UNIT_TEST_TIMBA_RESULT
        )

        # reload TiMBA results
        results_folder = cls.PACKAGEDIR / DATA_FOLDER / OUTPUT_DIR
        results_file = list(results_folder.glob("*.pkl"))[0]
        cls.data_timba = DataManager.restore_from_pickle(results_file)

    # def test_timba_results(self):
    #     """test TiMBA results against standard output"""
    #     if user_input.get("test_timba_results", False):
    #         test_result = DataValidator.check_timba_results(
    #             Data=self.data_timba,
    #             DataTest=self.data_timba_test,
    #             rel_tolerance=5e-02
    #         )
    #         msg = "TiMBA results not match reference data."
    #         self.assertTrue(test_result, msg)

    def test_data_container(self):
        from TiMBA.parameters.Domains import Domains
        from TiMBA.data_management.DataManager import DataManager
        from TiMBA.data_management.DataContainer import (
            DataContainer, InterfaceWorldData, WorldDataCollector)
        cls = self.__class__

        INPUT_PATH = cls.PACKAGEDIR / DATA_FOLDER / INPUT_WORLD_PATH
        world_version_unit_test = os.listdir(cls.PACKAGEDIR)[0]

        DC = DataContainer("test")
        self.assertIsInstance(DC, DataContainer)
        self.assertTrue(hasattr(DC, "filepath"))
        self.assertTrue(hasattr(DC, "data"))
        self.assertTrue(hasattr(DC, "domain"))
        self.assertTrue(DC.data.empty)
        self.assertIsNone(DC.domain)

        def bad_interface():
            InterfaceWorldData("test")
        self.assertRaises(TypeError, bad_interface)

        self.assertTrue(hasattr(InterfaceWorldData, "set_attribute"))
        self.assertTrue(issubclass(InterfaceWorldData, DataContainer))

        self.assertTrue(issubclass(WorldDataCollector,
                                   (InterfaceWorldData, DataContainer)))
        self.assertTrue(hasattr(WorldDataCollector, "set_attribute"))

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

        domain_name = str(Domains.Specification)
        self.assertFalse(hasattr(WDC, domain_name))

        DataManager.set_attribute(WDC, domain_name,
                                  DataContainer(WDC.filepath))
        self.assertTrue(hasattr(WDC, domain_name))
        self.assertTrue(hasattr(WDC[domain_name], "data"))
        self.assertEqual(WDC.filepath, wdc_path)

        self.assertTrue(WDC[domain_name].data.empty)
        self.assertTrue(WDC.Specification.data.empty)

        TEST_NAME = "TEST_NAME"
        INPUT_WORLD_PATH_LOOPED = wdc_path
        iwpl_path = os.path.basename(INPUT_WORLD_PATH_LOOPED)
        expected_repr = f"Content from {iwpl_path}; Sheet: {TEST_NAME}"

        WDC[domain_name].update_domain_name(TEST_NAME)
        actual_repr = repr(WDC[domain_name]).replace("'", "")
        self.assertEqual(actual_repr, expected_repr)

    def test_import_all_timba_modules(self):
        """
        Automatically import all TiMBA submodules to
        satisfy coverage for imports.
        """
        package_path = Path(TiMBA.__file__).parent
        for _, module_name, _ in pkgutil.walk_packages(
            [str(package_path)], TiMBA.__name__ + "."
        ):
            importlib.import_module(module_name)

    def test_cli_all_commands_without_expensive_calls(self):
        """
        Tests CLI commands without running expensive functions.
        """

        runner = CliRunner()

        with patch("TiMBA.cli.cli.run_timba") as mock_timba, \
             patch("TiMBA.cli.cli.run_extensions") as mock_ext, \
             patch("TiMBA.cli.cli.load_data") as mock_load, \
             patch("TiMBA.cli.cli.timba_dashboard") as mock_dashboard, \
             patch("TiMBA.cli.cli.C_Module") as mock_c:

            # Setup mock for C_Module.run
            mock_instance = mock_c.return_value
            mock_instance.run.return_value = None

            # ---- timba command ----
            res = runner.invoke(cli, ["run"])
            self.assertEqual(res.exit_code, 0,
                             f"timba command failed: {res.output}")
            mock_timba.assert_called_once()
            mock_ext.assert_called_once()

            # ---- load_data command ----
            res = runner.invoke(cli, [
                "load",
                "--user", "dummy_user",
                "--repo", "dummy_repo",
                "--branch", "main",
                "--folder", "dummy_folder",
                "--folderpath", str(self.PACKAGEDIR)
            ])
            self.assertEqual(res.exit_code, 0,
                             f"load_data command failed: {res.output}")
            mock_load.assert_called_once()

            # ---- dashboard command ----
            res = runner.invoke(cli, [
                "dashboard",
                "--num_files", "2",
                "--data_folderpath", str(self.PACKAGEDIR)
            ])
            self.assertEqual(res.exit_code, 0,
                             f"dashboard command failed: {res.output}")
            mock_dashboard.assert_called_once()
            mock_ext.assert_called_once()

            # ---- carbon command ----
            res = runner.invoke(cli, [
                "carbon",
                "--sc_num", "1",
                "--calc_c_forest_agb", "False",
                "--calc_c_forest_bgb", "False",
                "--calc_c_forest_soil", "False",
                "--calc_c_forest_dwl", "False",
                "--calc_c_hwp", "False",
                "--c_hwp_accounting_approach", "None",
                "--read_in_pkl", "False"
            ])
            self.assertEqual(res.exit_code, 0,
                             f"carbon command failed: {res.output}")
            mock_c.assert_called_once()
            mock_instance.run.assert_called_once()

    @classmethod
    def tearDownClass(cls):
        tiMBA_path = cls.PACKAGEDIR / "TiMBA"
        if tiMBA_path.exists():
            shutil.rmtree(tiMBA_path)


if __name__ == '__main__':
    unittest.main()
