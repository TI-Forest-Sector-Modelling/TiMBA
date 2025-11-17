from enum import Enum


class VarNames(Enum):
    """
    Class to hold names of variables
    """
    CONTINENT_COLNAME = "ContinentNew"
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


class Constants(Enum):
    """
    Class to hold computational and floating point constants
    """
    NON_ZERO_PARAMETER = 0.0000000001
    TRADE_INERTIA_DEVIATION = 0.005  # most accurate world prices with 0.05 with lose trade boundaries / with 0.005 with hard boundaries
    TRADE_INERTIA_DEVIATION_ZY = 0.001  # most accurate world prices with 0.01 with lose trade boundaries / with 0.001 with hard boundaries
    TRADE_BOUND_DEVIATION_PENALTY = 99999999  # Penalty term for deviation from trade bounds (retrieved from GFPM source code)
    TRADE_PREV_DEVIATION_PENALTY = 0  # Penalty term for deviation from trade in previous period, set 0 to deactivate
    BOUND_OMITTED_VALUE = 99999999
    PRICE_DEVIATION_THRESHOLD = 0.5 # Threshold for correction of shadow price in current period compared to previous period
    fao_agg_country_code = 5000


class ConversionParameters(Enum):
    MIO_FACTOR = 1000


class SolverParameters(Enum):
    """
    REL_ACCURACY: default 0.0025; best settings for optimal world prices: 0.00025 (with tighted trade boundaries 0.005, 0.001)
    ABS_ACCURACY: default 0.0001; best settings for optimal world prices: 0.00001 (with tighted trade boundaries 0.005, 0.001)
    """
    MAX_ITERATION = 500000
    REL_ACCURACY = 0.00025
    ABS_ACCURACY = 0.00001
    MAX_ITERATION_UNIT_TEST = 500000
    REL_ACCURACY_UNIT_TEST = 0.00025
    ABS_ACCURACY_UNIT_TEST = 0.00001


class Shifter(Enum):
    except_shifter_zero = 0
    except_shifter_minus_one = -1
