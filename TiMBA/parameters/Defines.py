from enum import Enum


class VarNames(Enum):
    """
    Class to hold names of variables
    """
    DOMAIN_COLNAME = "domain"
    PRICE_COLNAME = "price"
    QUANTITY_COLNAME = "quantity"
    ELASTICITY_COLNAME = "elasticity_price"
    SLOPE_COLNAME = "slope"
    INTERCEPT_COLNAME = "intercept"
    PERIOD_COLNAME = "Period"
    YEAR_COLNAME = "year"
    SHADOW_PRICE_COLNAME = "shadow_price"

    TRADE_LOWER_BOUND = "trade_lower_bound"
    TRADE_UPPER_BOUND = "trade_upper_bound"
    SUPPLY_UPPER_BOUND = "supply_upper_bound"
    DEMAND_LOWER_BOUND = "demand_lower_bound"
    MANU_UPPER_BOUND = "manu_upper_bound"
    MAX_HARVEST = "max_harvest"
    MATERIAL_BALANCE = "material_balance"
    MATERIAL_BALANCE_ZY = "material_balance_zy"
    ZY_EXPORT = "zy_export"
    ZY_IMPORT = "zy_import"
    ZY_REGION = "zy"
    MANUFACTURE_COSTS = "manufacture_costs"
    TRANSPORT_COSTS = "transport_costs"
    TOTAL_PRODUCTION_COST = "total_production_costs"
    RAW_MATERIAL_COST = "raw_material_costs"
    RAW_MATERIAL_COST_INTERM_PROD = "RawMaterialCostIntermProd"

    SHADOW_PROD_PRICE = "shadow_PP"
    CALC_PROD_PRICE = "calculated_PP"
    SHADOW_WORLD_PRICE = "shadow_WP"
    CONSTANT_WORLD_PRICE = "constant_WP"
    AVG_WORLD_PRICE = "average_WP"
    EXG_WORLD_PRICE = "exogen_WP"
    C_SPECIFIC_MB = "C_specific_MB"
    RC_SPECIFIC_MB = "RC_specific_MB"
    RCG_SPECIFIC_MB = "RCG_specific_MB"
    OPT_MB = "optional_MB"


class ParamNames(Enum):
    """
    Closs to hold names of parameters
    """
    year = "year"
    max_period = "max_period"
    product_price = "product_price"
    world_price = "world_price"
    transportation_factor = "transportation_factor"
    material_balance = "material_balance"
    serialization = "serialization"
    constants = "constants"
    dynamization_activated = "dynamization_activated"
    capped_prices = "capped_prices"
    cleaned_opt_quantity = "cleaned_opt_quantity"
    global_material_balance = "global_material_balance"
    verbose_optimization_logger = "verbose_optimization_logger"
    verbose_calculation_logger = "verbose_calculation_logger"
    addInfo = "addInfo"
    test_timba_results = "test_timba_results"
    activate_cmodule = "activate_add_on_cmodule"
    sc_num = "sc_num"
    read_in_pkl = "read_in_pkl"
    calc_c_forest_agb = "calc_c_forest_agb"
    calc_c_forest_bgb = "calc_c_forest_bgb"
    calc_c_forest_soil = "calc_c_forest_soil"
    calc_c_forest_dwl = "calc_c_forest_dwl"
    calc_c_hwp = "calc_c_hwp"
    c_hwp_accounting_approach = "c_hwp_accounting_approach"
    historical_c_hwp = "historical_c_hwp"
    hist_hwp_start_year = "hist_hwp_start_year"
    hist_hwp_start_year_default = "hist_hwp_start_year_default"
    show_carbon_dashboard = "show_carbon_dashboard"
    fao_data_update = "fao_data_update"
    chart_flag = "chart_flag"


class Constants(Enum):
    """
    Class to hold computational and floating point constants
    """
    NON_ZERO_PARAMETER = 0.0000000001
    # Trade inertias lose trade boundaries (0.05)/hard boundaries (0.005)
    TRADE_INERTIA_DEVIATION = 0.005
    # Rest of world trade inertias lose trade bounds (0.01)/hard bounds (0.001)
    TRADE_INERTIA_DEVIATION_ZY = 0.001
    # Penalty term for deviation from trade bounds (retrieved from GFPM)
    TRADE_BOUND_DEVIATION_PENALTY = 99999999
    # Penalty term for deviation from trade in previous period, 0 to deactivate
    TRADE_PREV_DEVIATION_PENALTY = 0
    BOUND_OMITTED_VALUE = 99999999
    # Threshold for correction of shadow price in current to previous period
    PRICE_DEVIATION_THRESHOLD = 0.5
    fao_agg_country_code = 5000


class ConversionParameters(Enum):
    MIO_FACTOR = 1000


class SolverParameters(Enum):
    """
    REL_ACCURACY: default 0.0025; best settings for optimal world prices:
        0.00025 (with tighted trade boundaries 0.005, 0.001)
    ABS_ACCURACY: default 0.0001; best settings for optimal world prices:
        0.00001 (with tighted trade boundaries 0.005, 0.001)
    """
    MAX_ITERATION = 500000
    REL_ACCURACY = 0.00001
    ABS_ACCURACY = 0.00025


class Shifter(Enum):
    except_shifter_zero = 0
    except_shifter_minus_one = -1
