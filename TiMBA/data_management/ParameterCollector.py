from pathlib import Path

from typing import Union
from TiMBA.parameters.Defines import ParamNames


class ParameterCollector:
    """
    Class to collect user IO and propagate through application.
    """
    def __init__(self, user_input: dict,
                 folderpath: Union[str, Path, None] = None):
        """
        :param year: ...
        :param max_period: ...
        :param country: ...
        :param product: ...
        :param calc_product_prices: Switch to enable/disable shadow-price calc
        :param transportation_imp_exp_bound_factor: Factor to be used in
        model.set_bounds() for import/export
        :param param_x: EXEMPLARY ADDITIONAL PARAM  TODO: Drop
        :param param_y: EXEMPLARY ADDITIONAL PARAM  TODO: Drop
        """
        self._year = user_input[ParamNames.year.value]
        self._max_period = user_input[ParamNames.max_period.value]
        self._calc_product_prices = user_input[ParamNames.product_price.value]
        self._calc_world_prices = user_input[ParamNames.world_price.value]
        self._transportation_imp_exp_bound_factor = user_input[ParamNames.transportation_factor.value]
        self._material_balance = user_input[ParamNames.material_balance.value]
        self._global_material_balance = user_input[ParamNames.global_material_balance.value]
        self._serialization = user_input[ParamNames.serialization.value]
        self._constants = user_input[ParamNames.constants.value]
        self._dynamization_activated = user_input[ParamNames.dynamization_activated.value]
        self._capped_prices = user_input[ParamNames.capped_prices.value]
        self._cleaned_opt_quantity = user_input[ParamNames.cleaned_opt_quantity.value]
        self._verbose_optimization_logger = user_input[ParamNames.verbose_optimization_logger.value]
        self._verbose_calculation_logger = user_input[ParamNames.verbose_calculation_logger.value]
        self._addInfo = user_input[ParamNames.addInfo.value]
        self._folderpath = folderpath
        self._activate_add_on_cmodule = user_input[ParamNames.activate_cmodule.value]
        self._sc_num = user_input[ParamNames.sc_num.value]
        self._read_in_pkl = user_input[ParamNames.read_in_pkl.value]
        self._calc_c_forest_agb = user_input[ParamNames.calc_c_forest_agb.value]
        self._calc_c_forest_bgb = user_input[ParamNames.calc_c_forest_bgb.value]
        self._calc_c_forest_soil = user_input[ParamNames.calc_c_forest_soil.value]
        self._calc_c_forest_dwl = user_input[ParamNames.calc_c_forest_dwl.value]
        self._calc_c_hwp = user_input[ParamNames.calc_c_hwp.value]
        self._c_hwp_accounting_approach = user_input[ParamNames.c_hwp_accounting_approach.value]
        self._historical_c_hwp = user_input[ParamNames.historical_c_hwp.value]
        self._hist_hwp_start_year = user_input[ParamNames.hist_hwp_start_year.value]
        self._hist_hwp_start_year_default = user_input[ParamNames.hist_hwp_start_year_default.value]
        self._show_carbon_dashboard = user_input[ParamNames.show_carbon_dashboard.value]
        self._fao_data_update = user_input[ParamNames.fao_data_update.value]
        self._carbon_constraint = user_input[ParamNames.carbon_constraint.value]
        self._chart_flag = user_input[ParamNames.chart_flag.value]

        # Run directly after __init__ to ensure correct user IO
        self.input_data_check()

    @property
    def year(self) -> int:
        return self._year

    @year.setter
    def year(self, value: int):
        self._year = value

    @property
    def max_period(self) -> int:
        return self._max_period

    @max_period.setter
    def max_period(self, value: int):
        self._max_period = value

    @property
    def calc_product_prices(self) -> str:
        return self._calc_product_prices

    @calc_product_prices.setter
    def calc_product_prices(self, value: str):
        self._calc_product_prices = value

    @property
    def calc_world_prices(self) -> str:
        return self._calc_world_prices

    @calc_world_prices.setter
    def calc_world_prices(self, value: str):
        self._calc_world_prices = value

    @property
    def transportation_imp_exp_bound_factor(self) -> float:
        return self._transportation_imp_exp_bound_factor

    @transportation_imp_exp_bound_factor.setter
    def transportation_imp_exp_bound_factor(self, value: float):
        self._transportation_imp_exp_bound_factor = value

    @property
    def material_balance(self) -> str:
        return self._material_balance

    @material_balance.setter
    def material_balance(self, value: str):
        self._material_balance = value

    @property
    def global_material_balance(self) -> str:
        return self._global_material_balance

    @global_material_balance.setter
    def global_material_balance(self, value: str):
        self._global_material_balance = value

    @property
    def serialization(self) -> bool:
        return self._serialization

    @serialization.setter
    def serialization(self, value: bool):
        self._serialization = value

    @property
    def constants(self) -> list:
        return self._constants

    @constants.setter
    def constants(self, value: str):
        self._constants = value

    @property
    def dynamization_activated(self) -> bool:
        return self._dynamization_activated

    @dynamization_activated.setter
    def dynamization_activated(self, value: bool):
        self._dynamization_activated = value

    @property
    def capped_prices(self) -> bool:
        return self._capped_prices

    @capped_prices.setter
    def capped_prices(self, value: bool):
        self._capped_prices = value

    @property
    def verbose_optimization_logger(self) -> bool:
        return self._verbose_optimization_logger

    @verbose_optimization_logger.setter
    def verbose_optimization_logger(self, value: bool):
        self._verbose_optimization_logger = value

    @property
    def verbose_calculation_logger(self) -> bool:
        return self._verbose_calculation_logger

    @verbose_calculation_logger.setter
    def verbose_calculation_logger(self, value: bool):
        self._verbose_calculation_logger = value

    @property
    def addInfo(self) -> bool:
        return self._addInfo

    @addInfo.setter
    def addInfo(self, value: bool):
        self._addInfo = value

    @property
    def folderpath(self) -> Union[str, Path, None]:
        return self._folderpath

    @folderpath.setter
    def folderpath(self, value: Union[str, Path, None]):
        self._folderpath = value

    @property
    def cleaned_opt_quantity(self) -> bool:
        return self._cleaned_opt_quantity

    @cleaned_opt_quantity.setter
    def cleaned_opt_quantity(self, value: bool):
        self._cleaned_opt_quantity = value

    @property
    def activate_add_on_cmodule(self) -> bool:
        return self._activate_add_on_cmodule

    @activate_add_on_cmodule.setter
    def activate_add_on_cmodule(self, value: bool):
        self._activate_add_on_cmodule = value

    @property
    def sc_num(self) -> int:
        return self._sc_num

    @sc_num.setter
    def sc_num(self, value: int):
        self._sc_num = value

    @property
    def read_in_pkl(self) -> bool:
        return self._read_in_pkl

    @read_in_pkl.setter
    def read_in_pkl(self, value: bool):
        self._read_in_pkl = value

    @property
    def calc_c_forest_agb(self) -> bool:
        return self._calc_c_forest_agb

    @calc_c_forest_agb.setter
    def calc_c_forest_agb(self, value: bool):
        self._calc_c_forest_agb = value

    @property
    def calc_c_forest_bgb(self) -> bool:
        return self._calc_c_forest_bgb

    @calc_c_forest_bgb.setter
    def calc_c_forest_bgb(self, value: bool):
        self._calc_c_forest_bgb = value

    @property
    def calc_c_forest_soil(self) -> bool:
        return self._calc_c_forest_soil

    @calc_c_forest_soil.setter
    def calc_c_forest_soil(self, value: bool):
        self._calc_c_forest_soil = value

    @property
    def calc_c_forest_dwl(self) -> bool:
        return self._calc_c_forest_dwl

    @calc_c_forest_dwl.setter
    def calc_c_forest_dwl(self, value: bool):
        self._calc_c_forest_dwl = value

    @property
    def calc_c_forest_dwl(self) -> bool:
        return self._calc_c_forest_dwl

    @calc_c_forest_dwl.setter
    def calc_c_forest_dwl(self, value: bool):
        self._calc_c_forest_dwl = value

    @property
    def calc_c_hwp(self) -> bool:
        return self._calc_c_hwp

    @calc_c_hwp.setter
    def calc_c_hwp(self, value: bool):
        self._calc_c_hwp = value

    @property
    def c_hwp_accounting_approach(self) -> str:
        return self._c_hwp_accounting_approach

    @c_hwp_accounting_approach.setter
    def c_hwp_accounting_approach(self, value: str):
        self._c_hwp_accounting_approach = value

    @property
    def historical_c_hwp(self) -> str:
        return self._historical_c_hwp

    @historical_c_hwp.setter
    def historical_c_hwp(self, value: str):
        self._historical_c_hwp = value

    @property
    def hist_hwp_start_year(self) -> str:
        return self._hist_hwp_start_year

    @hist_hwp_start_year.setter
    def hist_hwp_start_year(self, value: str):
        self._hist_hwp_start_year = value

    @property
    def hist_hwp_start_year_default(self) -> int:
        return self._hist_hwp_start_year_default

    @hist_hwp_start_year_default.setter
    def hist_hwp_start_year_default(self, value: int):
        self._hist_hwp_start_year_default = value

    @property
    def show_carbon_dashboard(self) -> bool:
        return self._show_carbon_dashboard

    @show_carbon_dashboard.setter
    def show_carbon_dashboard(self, value: bool):
        self._show_carbon_dashboard = value

    @property
    def fao_data_update(self) -> bool:
        return self._fao_data_update

    @fao_data_update.setter
    def fao_data_update(self, value: bool):
        self._fao_data_update = value

    @property
    def carbon_constraint(self) -> bool:
        return self._carbon_constraint

    @carbon_constraint.setter
    def carbon_constraint(self, value: float):
        self._carbon_constraint = value

    @property
    def chart_flag(self) -> bool:
        return self._chart_flag

    @chart_flag.setter
    def chart_flag(self, value: bool):
        self._chart_flag = value

    def __repr__(self):
        return repr(f"year={self.year}, "
                    f"max_period={self.max_period}, "
                    f"calc_product_prices={self.calc_product_prices}, "
                    f"calc_world_prices={self.calc_world_prices}, "
                    f"""transportation_imp_exp_bound_factor=
                    {self.transportation_imp_exp_bound_factor}"""
                    f"material_balance={self.material_balance}, "
                    f"carbon_constraint={self.carbon_constraint}, "
                    )

    def input_data_check(self):
        assert isinstance(self.year, int)
        assert isinstance(self.max_period, int)
        assert isinstance(self.calc_product_prices, str)
        assert isinstance(self.calc_world_prices, str)
        assert isinstance(self.material_balance, str)
        assert isinstance(self.global_material_balance, bool)
        assert isinstance(self.serialization, bool)
        assert isinstance(self.constants, list)
        assert isinstance(self.dynamization_activated, bool)
        assert isinstance(self.capped_prices, bool)
        assert isinstance(self.cleaned_opt_quantity, bool)
        assert isinstance(self.verbose_optimization_logger, bool)
        assert isinstance(self.verbose_calculation_logger, bool)
        assert isinstance(self.addInfo, bool)
        assert type(self.transportation_imp_exp_bound_factor) in [float, int]
        assert isinstance(self.activate_add_on_cmodule, bool)
        assert isinstance(self.sc_num, (int, type(None)))
        assert isinstance(self.read_in_pkl, bool)
        assert isinstance(self.calc_c_forest_agb, bool)
        assert isinstance(self.calc_c_forest_bgb, bool)
        assert isinstance(self.calc_c_forest_soil, bool)
        assert isinstance(self.calc_c_forest_dwl, bool)
        assert isinstance(self.calc_c_hwp, bool)
        assert isinstance(self.historical_c_hwp, str)
        assert isinstance(self.hist_hwp_start_year, str)
        assert isinstance(self.hist_hwp_start_year_default, int)
        assert isinstance(self.show_carbon_dashboard, bool)
        assert isinstance(self.fao_data_update, bool)
        assert isinstance(self.carbon_constraint, bool)
        assert isinstance(self.chart_flag, bool)

        # TODO: Adapt tests for new params: Following are just exemplary.
        # assert self.param_x[0] > 0
        # assert isinstance(self.param_x[0], int)
        # assert -1 < self.param_x[1] < 1
        # assert len(self.param_y) == 3
        # assert isinstance(self.param_y[0], str)
        # assert isinstance(self.param_y[1], int)
        # assert isinstance(self.param_y[2], float)
        # assert self.param_y[2] > 2
