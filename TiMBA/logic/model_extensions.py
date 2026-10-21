from TiMBA.parameters.Defines import ParamNames
from TiMBA.parameters.paths import timba_trade_paths
from c_module.logic.main import C_Module
import timba_trade.main as tm

import pandas as pd
from pathlib import Path

# Add-on carbon module
class TiMBAExtensions(object):
    def __init__(self,
                 UserOptions):
        self.UserOptions = UserOptions
        self.c_module = None

    def run_carbon_module(self):
        if self.UserOptions.activate_add_on_cmodule:
            c_module = C_Module(UserInput={
                ParamNames.activate_cmodule.value: self.UserOptions.activate_add_on_cmodule,
                ParamNames.sc_num.value: self.UserOptions.sc_num,
                ParamNames.read_in_pkl.value: self.UserOptions.read_in_pkl,
                ParamNames.calc_c_forest_agb.value: self.UserOptions.calc_c_forest_agb,
                ParamNames.calc_c_forest_bgb.value: self.UserOptions.calc_c_forest_bgb,
                ParamNames.calc_c_forest_soil.value: self.UserOptions.calc_c_forest_soil,
                ParamNames.calc_c_forest_dwl.value: self.UserOptions.calc_c_forest_dwl,
                ParamNames.calc_c_hwp.value: self.UserOptions.calc_c_hwp,
                ParamNames.c_hwp_accounting_approach.value: self.UserOptions.c_hwp_accounting_approach,
                ParamNames.historical_c_hwp.value: self.UserOptions.historical_c_hwp,
                ParamNames.hist_hwp_start_year.value: self.UserOptions.hist_hwp_start_year,
                ParamNames.hist_hwp_start_year_default.value: self.UserOptions.hist_hwp_start_year_default,
                ParamNames.show_carbon_dashboard.value: self.UserOptions.show_carbon_dashboard,
                ParamNames.fao_data_update.value: self.UserOptions.fao_data_update
            })
            c_module.run()
            self.c_module = c_module


def run_extensions(UserIO):
    extensions = TiMBAExtensions(UserOptions=UserIO)
    extensions.run_carbon_module()

def run_trade_module(
        data:pd.DataFrame,
        data_path:Path, 
        ttp:dict=timba_trade_paths
)->pd.DataFrame:
    ttp["BACI_DIR"] = data_path / Path(ttp["BACI_DIR"])
    ttp["LOG_DIR"] = data_path / Path(ttp["LOG_DIR"])

    return tm.main(
        timba_data=data, 
        save_file=False,
        path_dict=ttp,
    )

