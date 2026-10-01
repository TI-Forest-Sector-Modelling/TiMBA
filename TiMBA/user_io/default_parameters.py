from TiMBA.parameters.Defines import ParamNames

default_year = 2020

default_max_period = 10

# default_calc_product_price possible specifications:
# "shadow_PP", "calculated_PP"
default_calc_product_price = "shadow_PP"

# default_calc_world_price possible specifications:
# "shadow_WP", "constant_WP", "average_WP, exogen_WP"
default_calc_world_price = "shadow_WP"

# default_MB possible specifications:
# "RC_specific_MB" # <- region and commodity specific material balance
# "RCG_specific_MB" # <- region and commodity group specific material balance
# "C_specific_MB" # <- commodity specific material balance
default_MB = "C_specific_MB"
default_transportation_impexp_factor = 1

# serialization_flag: if true read data from stored pkl files
serialization_flag = False

# constants: [constant prices, constant slopes, constant intercep]
constants = [False, False, False]
dynamization_activated = True
capped_prices = False
cleaned_opt_quantity = False

global_material_balance = False
verbose_optimization_logger = True
verbose_calculation_logger = False
read_additional_information_file = True

# test_timba_results: if true activate unittest for TiMBA results
test_timba_results = True

# Carbon module related parameters
activate_add_on_cmodule = True
sc_num = None  # Activate if run with CLI
read_in_pkl = True  # Caution False option not implemented yet
calc_c_forest_agb = True
calc_c_forest_bgb = True
calc_c_forest_soil = True
calc_c_forest_dwl = True
calc_c_hwp = True

# c_hwp_accounting_approach possible specifications:
# "stock-change" or "production"
c_hwp_accounting_approach = "stock-change"

# historical_c_hwp possible specifications:
# "average" or "historical"
historical_c_hwp = "average"

# hist_hwp_start_year possible specifications:
# "country-specific" or "default"
hist_hwp_start_year = "default"
hist_hwp_start_year_default = default_year
show_carbon_dashboard = True
fao_data_update = False
# Constraints carbon to specific carbon targets and saves constraint-related shadow price
carbon_constraint = False

# Max stock density compared to the previous period
max_density_growth = 1.5

# Charts integration
chart_flag = False

user_input = {
    ParamNames.year.value: default_year,
    ParamNames.max_period.value: default_max_period,
    ParamNames.product_price.value: default_calc_product_price,
    ParamNames.world_price.value: default_calc_world_price,
    ParamNames.transportation_factor.value: default_transportation_impexp_factor,
    ParamNames.material_balance.value: default_MB,
    ParamNames.serialization.value: serialization_flag,
    ParamNames.constants.value: constants,
    ParamNames.dynamization_activated.value: dynamization_activated,
    ParamNames.capped_prices.value: capped_prices,
    ParamNames.cleaned_opt_quantity.value: cleaned_opt_quantity,
    ParamNames.global_material_balance.value: global_material_balance,
    ParamNames.verbose_optimization_logger.value: verbose_optimization_logger,
    ParamNames.verbose_calculation_logger.value: verbose_calculation_logger,
    ParamNames.addInfo.value: read_additional_information_file,
    ParamNames.test_timba_results.value: test_timba_results,
    ParamNames.activate_cmodule.value: activate_add_on_cmodule,
    ParamNames.sc_num.value: sc_num,
    ParamNames.read_in_pkl.value: read_in_pkl,
    ParamNames.calc_c_forest_agb.value: calc_c_forest_agb,
    ParamNames.calc_c_forest_bgb.value: calc_c_forest_bgb,
    ParamNames.calc_c_forest_soil.value: calc_c_forest_soil,
    ParamNames.calc_c_forest_dwl.value: calc_c_forest_dwl,
    ParamNames.calc_c_hwp.value: calc_c_hwp,
    ParamNames.c_hwp_accounting_approach.value: c_hwp_accounting_approach,
    ParamNames.historical_c_hwp.value: historical_c_hwp,
    ParamNames.hist_hwp_start_year.value: hist_hwp_start_year,
    ParamNames.hist_hwp_start_year_default.value: hist_hwp_start_year_default,
    ParamNames.show_carbon_dashboard.value: show_carbon_dashboard,
    ParamNames.carbon_constraint.value: carbon_constraint,
    ParamNames.fao_data_update.value: fao_data_update,
    ParamNames.chart_flag.value: chart_flag,
}
