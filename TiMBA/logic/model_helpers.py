import pandas as pd
import numpy as np
from TiMBA.parameters.Defines import (Constants, Shifter, ConversionParameters, VarNames)

from TiMBA.helpers.utils import Domains
from TiMBA.data_management.DataContainer import InterfaceWorldData


def calc_slope_inverted(self, domain_name:str, elasticity: pd.Series, price: pd.Series, quantity: pd.Series):
    """
    Calculate slope for Demand, Supply and Transportation using equation …
    Slope are corrected in case of calculated prices and quantities if present period is not zero. Slopes of
    previous period are taken over if present slopes equal 0.
    :param domain_name: name of the current domain (Supply, Demand, Manufacturing, Transportation)
    :param elasticity: values defining relationships between quantity and prices
    :param price: values of specific prices or costs
   	:param quantity: values of specific quantities   			
    :return: slope
    """
    slope_col_name = VarNames.SLOPE_COLNAME.value
    calc_prod_price_var = VarNames.CALC_PROD_PRICE.value
    quantity = quantity.clip(lower=0)
    price = price.clip(lower=0)
    quantity.replace(0, Constants.NON_ZERO_PARAMETER.value, inplace=True)
    slope = ((1 / elasticity) * price) / quantity
    slope.fillna(0, inplace=True)
    slope.replace(np.inf, 0, inplace=True)
    slope.replace(-np.inf, 0, inplace=True)
    if self.present_period > 0 and self.UserOptions.calc_product_prices == calc_prod_price_var:
        slope_index = slope.loc[slope == 0].index
        data_prev = self.Data[domain_name].data_aligned
        slope.loc[slope == 0] = data_prev[slope_col_name].loc[slope_index]
    return slope


def calc_slope_regular(self, domain_name:str, elasticity: pd.Series, price: pd.Series, quantity: pd.Series):
    """
    Calculate slope for Manufacturing using equation …
    Slope are corrected in case of calculated prices and quantities if present period is not zero. Slopes of
    previous period are taken over if present slopes equal 0.
    :param domain_name: name of the current domain (Supply, Demand, Manufacturing, Transportation)
    :param elasticity: values defining relationships between quantity and prices
    :param price: values of specific prices or costs
    :param quantity: values of specific quantities
    :return: slope
    """
    slope_col_name = VarNames.SLOPE_COLNAME.value
    calc_prod_price_var = VarNames.CALC_PROD_PRICE.value
    quantity = quantity.clip(lower=0)
    slope = (elasticity * price) / quantity
    slope.fillna(0, inplace=True)
    slope.replace(np.inf, 0, inplace=True)
    slope.replace(-np.inf, 0, inplace=True)
    if self.present_period > 0 and self.UserOptions.calc_product_prices == calc_prod_price_var:
        slope_index = slope.loc[slope == 0].index
        data_prev = self.Data[domain_name].data_aligned
        slope.loc[slope == 0] = data_prev[slope_col_name].loc[slope_index]
    return slope


def calc_intercept(self, domain_name:str, price_name:str, price: pd.Series, slope: pd.Series, quantity: pd.Series):
    """
    Calculate intercept for all domains using equation …
    Slope are corrected in case of calculated prices and quantities if present period is not zero. Slopes of
    previous period are taken over if present slopes equal 0.
    :param domain_name: name of the current domain (Supply, Demand, Manufacturing, Transportation)
    :param price_name: name of price per domain (SPrice,DPrice,ManuCost)
    :param price: values of specific prices or costs
    :param slope: functional slopes of domains
    :param quantity: values of specific quantities
    :return: intercept
    """
    intercept_col_name = VarNames.INTERCEPT_COLNAME.value
    calc_prod_price_var = VarNames.CALC_PROD_PRICE.value
    quantity.replace(0, Constants.NON_ZERO_PARAMETER.value, inplace=True)  
    intercept = price - (slope * quantity)
    if domain_name == "Supply":
        print("intercept old: ",intercept)
        try:
            print(self.Data.Forest.data_aligned["removal_penalty"])
            intercept[:-16] = intercept[:-16] * self.Data.Forest.data_aligned["removal_penalty"]
        except KeyError:
            pass
        print("intercept new: ",intercept)

    intercept.fillna(0, inplace=True)
    intercept.replace(np.inf, 0, inplace=True)
    intercept.replace(-np.inf, 0, inplace=True)
    if self.present_period > 0 and self.UserOptions.calc_product_prices == calc_prod_price_var:
        data_prev = self.Data[domain_name].data_aligned
        price_index = data_prev[data_prev[price_name] == 0].index
        intercept.loc[price_index] = data_prev[intercept_col_name].loc[price_index]
    return intercept


def actual_period(period_data: pd.DataFrame, actual_year: int = 2017, max_period: int = 9):
    """
    Creating a dataframe which contains all neccessary data about the actual period
    :param actual_year: User Input: Year for which the simulation starts. Defaults to 2017.
    :param max_period: User Input: Number of periods the simulation should run. Defaults to 9.
    :return: contains data about the all possible periods, period block, period length and the actual year
    """
    row = 0
    period_df = [[0, 0, 0, actual_year]]
    for period in range(1, max_period + 1):
        try:
            prev_row = row
            if (period + 1) == period_data["Period"][row + 1]: # TODO Hard code (future work)
                row += 1
        except IndexError:
            pass
        period_length = period_data["ForecastYears"][prev_row] # TODO Hard code (future work)
        actual_year += period_data["ForecastYears"][prev_row] # TODO Hard code (future work)
        period_df += [[period, prev_row, period_length, actual_year]]

    period_df = pd.DataFrame(period_df)
    period_df.columns = ["Period", "PeriodBlock", "PeriodLength", "ActualYear"] # TODO Hard code (future work)

    return period_df


def transport_cost_calculation(RegionsData: pd.DataFrame, WorldPrice: pd.DataFrame,
                               ImportData: pd.DataFrame, ExportData: pd.DataFrame):
    """
    Calculate Transportcost, Importtax, Exporttax and Import-, Exportprice
    :param RegionsData: all region codes from regions / Worlddatacontainer
    :param WorldPrice: Worldprices from Worlddatacontainer
    :param ImportData: Transportationimport from Worlddatacontainer
    :param ExportData: Transportationexport from Worlddatacontainer
    """

    transp_cost_col_name = VarNames.TRANSPORT_COSTS.value

    import_tax = ImportData[Domains.TransportationImport.import_ad_valorem_tax_rate] * (
            ImportData[Domains.TransportationImport.freight_cost] +
            ImportData[Domains.TransportationImport.price])

    export_tax = ExportData[Domains.TransportationExport.export_ad_valorem_tax_rate] * ExportData[
        Domains.TransportationExport.price]

    freight_cost = ImportData[Domains.TransportationImport.freight_cost]

    transport_cost = freight_cost + import_tax + export_tax

    # Worldprice calculation for importing and exporting regions
    importing_regions = pd.DataFrame(
        np.where(np.array(ImportData[Domains.TransportationImport.quantity]) > 0.0000000001, 1, 0))[0] # TODO Hard code (future work)
    exporting_regions = pd.DataFrame(
        np.where(np.array(ImportData[Domains.TransportationExport.quantity]) > 0.0000000001, 1, 0))[0] # TODO Hard code (future work)
    world_price = pd.concat([WorldPrice["WorldPrice"]] * RegionsData).reset_index(drop=True) # TODO Hard code (future work)
    import_price = world_price + transport_cost

    ImportData[transp_cost_col_name] = transport_cost
    ImportData[Domains.TransportationImport.price] = import_price * importing_regions
    ExportData[Domains.TransportationExport.price] = world_price  # world_price * exporting_regions (leads to unusable small worldprices)


def production_price_calculation(self, AlignedData: pd.DataFrame, RegionsData: pd.DataFrame, SupplyData: pd.DataFrame,
                                 ImportData: pd.DataFrame, ioMatrix: pd.DataFrame,
                                 ManufactureCostData: pd.DataFrame, capped_prices: bool):
    """
    Compute production prices as the sum of raw material costs and manufacture costs. Raw material costs are calculated
    based on supply prices of raw material products multiplied by the IO-matrix. For countries without domestic
    production of raw material products (= no supply price), import prices are used instead and multiplied by the
    IO-matrix. Calculations are conducted in two steps to cover final and intermediate products.
    :param AlignedData: DataFrame with aligned data (containing aligned data for regions and commodities)
    :param RegionsData: DataFrame with region data (containing not aligned data for regions)
    :param SupplyData: aligned DataFrame for Supply (containing all data of supply DataFrame)
    :param ImportData: aligned DataFrame for TransportationImport (containing all data of Import DataFrame)
    :param ioMatrix: IO-coefficient-matrix of ManufactureCoefficient
    :param ManufactureCostData: aligned DataFrame for ManufactureCost (containing all data of manufacture DataFrame)
    :params capped_prices: flag for correction of production prices (demprices=prodprices) #TODO remove after validation?
    :return: Overwrite column "price" of ManufactureCost in World Data Container with computed production prices
    """
    total_prod_cost_col_name = VarNames.TOTAL_PRODUCTION_COST.value
    price_col_name = VarNames.PRICE_COLNAME.value
    raw_mat_cost_col_name = VarNames.RAW_MATERIAL_COST.value
    raw_mat_cost_int_prod_col_name = VarNames.RAW_MATERIAL_COST_INTERM_PROD.value

    supply_price_collector = pd.DataFrame()
    (raw_prod, interm_prod, fin_prod, fuelw, othindrnd) = extract_product_groups(world_data=self.Data,
                                                                                 commodity_data=self.Data.Commodities,
                                                                                 region_data=self.Data.Regions,
                                                                                 all_regions=False,
                                                                                 only_commodity_codes=True)
    # Calculation of raw material costs for final products based on supply and import prices
    for region in RegionsData[Domains.Regions.region_code]:
        help_matrix = SupplyData[SupplyData[Domains.Supply.region_code] == region]
        supply_price_region = pd.DataFrame()
        for commodity in help_matrix[Domains.Supply.commodity_code]:
            commodity_index = help_matrix[help_matrix[Domains.Supply.commodity_code] == commodity].index

            if (commodity in raw_prod) & (float(help_matrix[help_matrix[Domains.Supply.commodity_code] ==
                                                            commodity][Domains.Supply.price]) == 0):
                temporary_import_price_region = ImportData[Domains.TransportationImport.price].iloc[commodity_index]
                supply_price_region = pd.concat([supply_price_region,
                                                 temporary_import_price_region], axis=0).reset_index(drop=True)
            else:
                supply_price_region = pd.concat(
                    [supply_price_region, SupplyData[Domains.Supply.price].iloc[
                        commodity_index]], axis=0).reset_index(drop=True)

        supply_price_collector = pd.concat([supply_price_collector,
                                            supply_price_region], axis=0).reset_index(drop=True)

    supply_price_collector.rename(columns={0: Domains.Supply.price}, inplace=True)

    matrix_mult = ioMatrix.T @ supply_price_collector[Domains.Supply.price]
    matrix_mult = pd.concat([AlignedData, pd.DataFrame(matrix_mult).rename(
        columns={0: raw_mat_cost_int_prod_col_name})], axis=1)

    # Retrieving import prices for intermediate products for non-producing countries
    import_price_collector = pd.DataFrame()
    for region in RegionsData[Domains.Regions.region_code]:
        help_matrix = matrix_mult[matrix_mult[Domains.Regions.region_code] == region]
        import_price_region = pd.DataFrame()
        for commodity in help_matrix[Domains.Commodities.commodity_code]:
            if (commodity in interm_prod) & (float(help_matrix[help_matrix[Domains.Commodities.commodity_code] ==
                                                               commodity][raw_mat_cost_int_prod_col_name]) == 0):
                commodity_index = help_matrix[help_matrix[Domains.Commodities.commodity_code] == commodity].index
                temporary_import_price_region = ImportData[Domains.TransportationImport.price].iloc[commodity_index]
                import_price_region = pd.concat([import_price_region,
                                                 temporary_import_price_region], axis=0).reset_index(drop=True)
            else:
                import_price_region = pd.concat([import_price_region,
                                                 pd.DataFrame([0])], axis=0).reset_index(drop=True)
        import_price_collector = pd.concat([import_price_collector,
                                            import_price_region], axis=0).reset_index(drop=True)

    import_price_collector.rename(columns={0: raw_mat_cost_int_prod_col_name}, inplace=True)
    raw_material_cost = ioMatrix.T @ (matrix_mult[raw_mat_cost_int_prod_col_name] +
                                      import_price_collector[raw_mat_cost_int_prod_col_name] +
                                      ManufactureCostData[Domains.ManufactureCost.net_manufacturing_cost] +
                                      SupplyData[Domains.Supply.price])

    # TODO rename production costs to production prices (check compatibility with other model parts e.g. optimization) (future work)
    production_cost = raw_material_cost + ManufactureCostData[Domains.ManufactureCost.net_manufacturing_cost]
    if capped_prices:
        # TODO remove capped_prices in all functions
        delta_production_cost = ImportData[Domains.TransportationImport.price] - production_cost
        delta_production_cost[delta_production_cost > 0] = 0
        new_manufacture_cost = (ManufactureCostData[Domains.ManufactureCost.net_manufacturing_cost] +
                                delta_production_cost)
        new_manufacture_cost[new_manufacture_cost < 0] = 0
        ManufactureCostData[Domains.ManufactureCost.net_manufacturing_cost] = new_manufacture_cost

    ManufactureCostData[total_prod_cost_col_name] = production_cost  # TODO rename production costs to production prices
    ManufactureCostData[price_col_name] = ManufactureCostData[Domains.ManufactureCost.net_manufacturing_cost]
    ManufactureCostData[raw_mat_cost_col_name] = raw_material_cost

    return production_cost


def forest_param_alpha(ForestData: pd.DataFrame):
    """
    Calculate alpha from equation ... for the base peroiod (variable needed to calculate forest area growth
    in following periods)
    :param ForestData: contain all forest data
    :return: alpha
    """
    growth_rate_area = ForestData[Domains.Forest.forest_area_growth_rate]
    SqForAreaGDPGrowth = ForestData[Domains.Forest.exponential_gdp_forest_area_growth_rate]
    LinForAreaGDPGrowth = ForestData[Domains.Forest.linear_gdp_forest_area_growth_rate]
    gdp_per_capita = ForestData[Domains.Forest.gdp_per_capita_base_period]

    alpha = (growth_rate_area / np.exp(SqForAreaGDPGrowth.astype(float) * gdp_per_capita.astype(float)/1000) -
             (LinForAreaGDPGrowth * gdp_per_capita/1000)) # TODO Hard code
    return alpha


def forest_param_gamma(ForestData: pd.DataFrame):
    """
    Calculate gamma from equation ... for the base peroiod (variable needed to calculate forest stock growth
    in following periods)
    :param ForestData: contain all forest data
    :return: gamma
    """
    growth_rate_stock = ForestData[Domains.Forest.growth_rate_forest_stock]
    forest_stock_prev = ForestData[Domains.Forest.forest_stock] + Constants.NON_ZERO_PARAMETER.value
    forest_area_prev = ForestData[Domains.Forest.forest_area] + Constants.NON_ZERO_PARAMETER.value
    StockElastArea = ForestData[Domains.Forest.elasticity_growth_rate_forest_stock]
    gamma = growth_rate_stock / ((forest_stock_prev / forest_area_prev) ** StockElastArea)

    return gamma


def update_dynamization(DomainData: pd.DataFrame, ChangeData: pd.DataFrame, shifter_exception: int = 1,
                        period_block: int = 1):
    """
    Updates last period data. Written to update current data with data from exogenous change. Calculated 
    with the length of domain data.
    :param DomainData: Vector with current data which should be updated
    :param ChangeData: contains the updates from exogenous change
    :param shifter_exception: Variable to deal with exception from updates. Used if data is unchanged. Defaults to 1.
    :param period_block: Variable for the current period block in exogenous change. Defaults to 1.
    :return: returns vector with updated data
    """
    lengthDomainData = len(DomainData)
    index_domain = DomainData.index
    start_of_period = period_block * lengthDomainData
    end_of_period = (period_block + 1) * lengthDomainData
    ChangeDataPeriod = ChangeData[start_of_period:end_of_period].copy().reset_index(drop=True)

    if shifter_exception in [Shifter.except_shifter_minus_one.value, Shifter.except_shifter_zero.value]:
        subset_ChangeDataPeriod = ChangeDataPeriod[ChangeDataPeriod == shifter_exception]
        index_subset_ChangeDataPeriod = subset_ChangeDataPeriod.index
        ChangeDataPeriod[index_subset_ChangeDataPeriod] = DomainData[index_subset_ChangeDataPeriod]

    return ChangeDataPeriod.reset_index(drop=True)


def growth_dynamization(DomainData: pd.DataFrame, ChangeData: pd.DataFrame, shifter_exception: int = 1,
                        shifter_switch: bool = False,
                        ChangeData_Switch: int = 0, period_block: int = 1, period_length: int = 5):
    """
    Calculate the growth per period. Written to deal with data from exogenous change,
    where growth is given annually. Calculated with the length of domain data.
    :param DomainData: Vector where growth is applied for
    :param ChangeData: Vector of data with annual growth rate
    :param shifter_exception: Variable to deal with exception from growth rates in exogenous change. Defaults to 1.
    :param shifter_switch: Switch data where growth is applied for with another data vector. Defaults to 0.
    :param ChangeData_Switch: Switched data vector. Defaults to 0.
    :param period_block: Variable for the actual period block in exogenous change. Defaults to 1.
    :param period_length: Variable for the actual period length. Defaults to 5.
    :return: returns vector with periodic growth rate data
    """
    lengthDomainData = len(DomainData)
    index_domain = DomainData.index
    start_of_period = period_block * lengthDomainData
    end_of_period = (period_block + 1) * lengthDomainData
    ChangeDataPeriod = ChangeData[start_of_period:end_of_period].copy().reset_index(drop=True)

    if shifter_exception in [Shifter.except_shifter_minus_one.value, Shifter.except_shifter_zero.value]:
        subset_ChangeDataPeriod = ChangeDataPeriod[ChangeDataPeriod == shifter_exception]
        index_subset_ChangeDataPeriod = subset_ChangeDataPeriod.index
        if shifter_switch:
            ChangeDataPeriod_Switch = ChangeData_Switch[index_domain]
            ChangeDataPeriod[index_subset_ChangeDataPeriod] = ChangeDataPeriod_Switch[index_subset_ChangeDataPeriod]
        else:
            ChangeDataPeriod[index_subset_ChangeDataPeriod] = DomainData[index_subset_ChangeDataPeriod]

    ChangeDataPeriod = (1 + ChangeDataPeriod) ** period_length - 1

    return ChangeDataPeriod.reset_index(drop=True)


def change_dynamization(DomainData: pd.DataFrame, ChangeData: pd.DataFrame, period_block: int = 1,
                        period_length: int = 5):
    """
    Calculate the change in amount per period. Written to deal with data from exogenous change,
    where change is given annually. Calculated with the length of domain data.
    :param DomainData: Vector where change is applied for
    :param ChangeData: Vector of data with annual change in amount
    :param period_block: Variable for the actual period block in exogenous change. Defaults to 1.
    :param period_length: Variable for the actual period length. Defaults to 5.
    :return: returns vector with periodic change in amount
    """
    lengthDomainData = len(DomainData) 
    start_of_period = period_block * lengthDomainData
    end_of_period = (period_block + 1) * lengthDomainData
    ChangeDataPeriod = ChangeData[start_of_period:end_of_period].copy()
    ChangeDataPeriod = ChangeDataPeriod * period_length

    return ChangeDataPeriod.reset_index(drop=True)


def dynamize_demand(Data: pd.DataFrame, DataChange: pd.DataFrame, period_info: list):
    """
    Read exogenous change data for growth parameters and elasticities, Calculate new demand as demand from simulation 
    results of the previous period multiplied with growth shifters, update demand data from previous period.
    :param Data: WorldData.Demand.data_aligned
    :param DataChange: WorldData.ExogChangeDemand.data_aligned
    :param period_info: list containing information about the current period
    """
    periodic_trend = growth_dynamization(Data[Domains.Demand.quantity],
                                         DataChange[Domains.ExogChangeDemand.growth_rate_value],
                                         period_block=period_info["block"], # TODO Hard code (future work)
                                         period_length=period_info["length"]) # TODO Hard code (future work)

    elasticity_price = update_dynamization(Data[Domains.Demand.elasticity_price],
                                           DataChange[Domains.ExogChangeDemand.elasticity_price],
                                           Shifter.except_shifter_zero.value,
                                           period_block=period_info["block"])

    elasticity_gdp = update_dynamization(Data[Domains.Demand.elasticity_gdp],
                                         DataChange[Domains.ExogChangeDemand.elasticity_gdp],
                                         Shifter.except_shifter_zero.value,
                                         period_block=period_info["block"])

    growth_gdp = growth_dynamization(Data[Domains.Demand.elasticity_gdp],
                                     DataChange[Domains.ExogChangeDemand.growth_rate_gdp],
                                     period_block=period_info["block"],
                                     period_length=period_info["length"])

    growth_expected_demand = growth_dynamization(Data[Domains.Demand.elasticity_expectations],
                                                 DataChange[Domains.ExogChangeDemand.growth_demand_expected],
                                                 period_block=period_info["block"],
                                                 period_length=period_info["length"])

    dynamized_demand_quantity = (Data[Domains.Demand.quantity] * 
                                 (1 + periodic_trend + elasticity_gdp * growth_gdp + 
                                  Data[Domains.Demand.elasticity_expectations] * growth_expected_demand))

    DLB = Data[Domains.Demand.lower_bound]
    growth_rate_DLB = DataChange[Domains.ExogChangeDemand.growth_lower_bound]
    periodic_grDLB =  (1 + growth_rate_DLB) ** period_info["length"]
    DLB = DLB * periodic_grDLB

    Data[Domains.Demand.elasticity_price] = elasticity_price
    Data[Domains.Demand.elasticity_gdp] = elasticity_gdp  
    Data[Domains.Demand.quantity] = dynamized_demand_quantity
    Data[Domains.Demand.lower_bound] = DLB


def dynamize_forest(Data: pd.DataFrame, DataChange: pd.DataFrame, DataSupply: pd.DataFrame, 
                    Logger: classmethod, period_info: list):
    """
    Read exogenous change, Calculate and update endogenous growth of forest area and stock (for detailed information
    check: Documentation), update forest data from previous period. Logger is used produce error messages. Calculation
    of growth_rate_stock, growth_rate_area, fraction_fuelwood, max_ratio_inventory_drain and carbon price not activated.
    Exogenous change for these parameters will not be accounted in the dynamisation.
    :param Data: WorldData.Forest.data
    :param DataChange: WorldData.ExogChangeForest.data
    :param DataSupply: WorldData.Supply.data_aligned
    :param period_info: list containing information about the current period
    :return: contains data about the endogenous forest stock growth per region code.
    This data is than used in dynamize_supply().
    """


    growth_rate_stock = growth_dynamization(Data[Domains.Forest.growth_rate_forest_stock],
                                            DataChange[Domains.ExogChangeForest.growth_rate_stock],
                                            Shifter.except_shifter_minus_one.value,
                                            period_block=period_info["block"]) # TODO Hard code (future work)

    growth_rate_area = growth_dynamization(Data[Domains.Forest.forest_area_growth_rate],
                                           DataChange[Domains.ExogChangeForest.growth_rate_area],
                                           Shifter.except_shifter_minus_one.value,
                                           period_block=period_info["block"])
    
    growth_rate_gdp = growth_dynamization(Data[Domains.Forest.gdp_per_capita_base_period],
                                          DataChange[Domains.ExogChangeForest.growth_rate_gdp],
                                          period_block=period_info["block"],
                                          period_length=period_info["length"]) # TODO Hard code (future work)
    growth_rate_gdp = growth_rate_gdp.reset_index(drop=True)

    adjustment_endogenous_growth_rate_stock = DataChange[Domains.ExogChangeForest.adjustment_endogenous_growth_rate_stock]
    adjustment_endogenous_growth_rate_stock = growth_dynamization(Data[Domains.Forest.gdp_per_capita_base_period],
                                                                  adjustment_endogenous_growth_rate_stock,
                                                                  period_block=period_info["block"],
                                                                  period_length=period_info["length"])

    StockElastArea = update_dynamization(Data[Domains.Forest.elasticity_growth_rate_forest_stock],
                                         DataChange[Domains.ExogChangeForest.elasticity_growth_rate_stock_on_area],
                                         Shifter.except_shifter_zero.value,
                                         period_block=period_info["block"])
    
    LinForAreaGDPGrowth = update_dynamization(Data[Domains.Forest.linear_gdp_forest_area_growth_rate],
                                              DataChange[Domains.ExogChangeForest.growth_rate_linear_GDP_forest_area_growth_rate],
                                              Shifter.except_shifter_zero.value,
                                              period_block=period_info["block"])
    
    SqForAreaGDPGrowth = update_dynamization(Data[Domains.Forest.exponential_gdp_forest_area_growth_rate],
                                             DataChange[Domains.ExogChangeForest.growth_rate_squared_GDP_forest_area_growth_rate],
                                             Shifter.except_shifter_zero.value,
                                             period_block=period_info["block"])

    fraction_fuelwood = update_dynamization(Data[Domains.Forest.fraction_fuelwood],
                                            DataChange[Domains.ExogChangeForest.fraction_fuelwood],
                                            Shifter.except_shifter_minus_one.value,
                                            period_block=period_info["block"])
    
    ratio_inventory_drain = update_dynamization(Data[Domains.Forest.ratio_inventory_drain],
                                                DataChange[Domains.ExogChangeForest.ratio_inventory_drain],
                                                Shifter.except_shifter_minus_one.value,
                                                period_block=period_info["block"])

    max_ratio_inventory_drain = update_dynamization(Data[Domains.Forest.max_ratio_inventory_drain],
                                                    DataChange[Domains.ExogChangeForest.max_ratio_inventory_drain],
                                                    Shifter.except_shifter_zero.value,
                                                    period_block=period_info["block"])
    
    if not Data[Data[Domains.Forest.forest_stock] < 0].index.any():
        pass
    else:
        Logger.info(f"Problem negativ forest stock for:")
        Logger.info(f"\n{Data.loc[min(Data[Data[Domains.Forest.forest_stock] <= 0].index)]}")
        Logger.info(f"Negativ forest stock set to zero")
        Data[Domains.Forest.forest_stock] = Data[Domains.Forest.forest_stock].clip(lower=0)

    if not Data[Data[Domains.Forest.forest_area] < 0].index.any():
        pass
    else:
        Logger.info(f"Problem negativ forest area for:")
        Logger.info(f"\n{Data.loc[min(Data[Data[Domains.Forest.forest_area] <= 0].index)]}")
        Logger.info(f"Negativ forest area set to zero")
        Data[Domains.Forest.forest_area] = Data[Domains.Forest.forest_area].clip(lower=0)

    forest_stock_prev = Data[Domains.Forest.forest_stock]
    forest_area_prev = Data[Domains.Forest.forest_area]
    Data[Domains.Forest.forest_stock].replace(0, 0.001, inplace=True) # TODO small non zero parameter
    forest_stock_prev = Data[Domains.Forest.forest_stock]

    gdp_per_capita = Data[Domains.Forest.gdp_per_capita_base_period] / ConversionParameters.MIO_FACTOR.value
    gdp_per_capita = gdp_per_capita * (1 + growth_rate_gdp.reset_index(drop=True))

    roundwood_supply = pd.concat(
        [DataSupply[Domains.Supply.region_code],
         pd.DataFrame(DataSupply[Domains.Supply.quantity] * Data[Domains.Forest.fraction_fuelwood]).fillna(0)
         ], axis=1).rename(columns={0: Domains.Supply.quantity})

    sum_roundwood_supply = roundwood_supply.groupby(Domains.Supply.region_code).sum().reset_index().rename(
        columns={Domains.Supply.quantity: "summed_roundwood_supply"})

    roundwood_supply = roundwood_supply.merge(sum_roundwood_supply, left_on="RegionCode", right_on="RegionCode",
                                              how="left")

    roundwood_supply = (roundwood_supply["summed_roundwood_supply"] * period_info["length"] /
                        ConversionParameters.MIO_FACTOR.value)

    alpha = Data["alpha"] # TODO Hard code (future work)
    gamma = Data["gamma"] # TODO Hard code (future work)

    area_growth = (alpha + LinForAreaGDPGrowth * gdp_per_capita) * np.exp(SqForAreaGDPGrowth.astype(float) *
                                                                          gdp_per_capita.astype(float))

    periodic_area_growth = growth_dynamization(area_growth, 
                                               DataChange[Domains.ExogChangeForest.growth_rate_area],
                                               Shifter.except_shifter_minus_one.value,
                                               period_block=period_info["block"],
                                               period_length=period_info["length"])
    
    forest_area_new = forest_area_prev * (1 + periodic_area_growth)

    periodic_change_rate_area = (forest_area_new - forest_area_prev) / forest_area_prev

    stock_growth_without_harvest = gamma * ((forest_stock_prev / forest_area_prev) ** StockElastArea)

    periodic_stock_growth_without_harvest = growth_dynamization(stock_growth_without_harvest,
                                                                DataChange[Domains.ExogChangeForest.growth_rate_stock],
                                                                Shifter.except_shifter_minus_one.value,
                                                                period_block=period_info["block"],
                                                                period_length=period_info["length"])
    
    stock_growth = ((periodic_area_growth + periodic_stock_growth_without_harvest +
                     adjustment_endogenous_growth_rate_stock) * forest_stock_prev)
    forest_stock_new = forest_stock_prev + stock_growth - (ratio_inventory_drain * roundwood_supply[:len(Data)])

    try:
        forest_stock_max_index = Data[
            Data[Domains.Forest.max_forest_density] != Shifter.except_shifter_minus_one.value].index
        forest_stock_oth_index = Data[
            Data[Domains.Forest.max_forest_density] == Shifter.except_shifter_minus_one.value].index

        forest_stock_max = (Data.loc[forest_stock_max_index, Domains.Forest.max_forest_density] *
                            forest_area_new[forest_stock_max_index]) / ConversionParameters.MIO_FACTOR.value
        forest_stock_max = pd.DataFrame(np.where(
            forest_stock_new[forest_stock_max_index] > forest_stock_max[forest_stock_max_index],
            forest_stock_max[forest_stock_max_index],
            forest_stock_new[forest_stock_max_index])).set_index(forest_stock_max_index)
        forest_stock_oth = forest_stock_new[forest_stock_oth_index]
        forest_stock_new = pd.concat([forest_stock_max, forest_stock_oth], axis=0).sort_index()
        forest_stock_new = forest_stock_new.reset_index(drop=True)
        forest_stock_new = pd.Series(forest_stock_new[0])

    except KeyError:
        pass

    periodic_change_rate_stock = (forest_stock_new - forest_stock_prev) / forest_stock_prev
    growth_df = pd.concat([Data[Domains.Forest.region_code], periodic_change_rate_stock,
                           periodic_change_rate_area], axis=1)

    forest_stock_new = forest_stock_new.clip(lower=0.001) # TODO small non zero parameter
    forest_area_new = forest_area_new.clip(lower=0.001) # TODO small non zero parameter

    # TODO check if exogenous change is empty or all zero than do solution 1
    # Solution1 for optimization failure with blanko exogChange-Sheet --> works
    # (extra stock for all regions which stock falls under 1 Mio. m³)
    # todo delete if better solution is found
    # forest_stock_new = forest_stock_new.clip(lower=0)
    # mask = forest_stock_new[forest_stock_new < 1].index
    # forest_stock_new.loc[mask] = forest_stock_new.loc[mask] + 1  # add 1 Mio. m³
    # forest_area_new = forest_area_new.clip(lower=0)
    # todo delete until here

    Data[Domains.Forest.forest_area] = forest_area_new
    Data[Domains.Forest.forest_stock] = forest_stock_new
    Data[Domains.Forest.gdp_per_capita_base_period] = gdp_per_capita * ConversionParameters.MIO_FACTOR.value
    Data[Domains.Forest.growth_rate_forest_stock] = (1 + stock_growth / forest_stock_prev) ** (1 / period_info["length"]) -1
    Data["ga"] = periodic_area_growth # TODO Hard code
    Data["gu"] = periodic_stock_growth_without_harvest # TODO Hard code
    Data["supply_from_forest"] = roundwood_supply.iloc[:len(Data)] # TODO Hard code
    Data["removal_penalty"] = penalty_factor(
        value=Data["supply_from_forest"] / Data[Domains.Forest.forest_stock]
    )

    return growth_df


def penalty_factor(value: pd.DataFrame, steepness: float = 10.0, threshold: float = 0.025, max_factor: int = 1000) -> float:
    value = pd.to_numeric(value, errors="coerce")
    exponent = np.clip(
        (value - threshold) * steepness,
        0.0,
        np.log(max_factor)
    )
    return np.exp(exponent)


def dynamize_supply(self, Data: pd.DataFrame, DataChange: pd.DataFrame, DataForest: pd.DataFrame,
                    DataForestChange: pd.DataFrame, Logger: classmethod, period_info: list):
    """
    Read exogenous change data for growth parameters and elasticities, calculate new supply as supply from simulation 
    results of the previous period multiplied with growth shifters, update supply data from previous period.
    :param Data: WorldData.Supply.data_aligned
    :param DataChange: WorldData.ExogChangeSupply.data_aligned
    :param DataForest: WorldData.Forest.data
    :param DataForestChange: WorldData.ExogChangeForest.data
    """
    zy_region_var = VarNames.ZY_REGION.value

    elasticity_price = update_dynamization(Data[Domains.Supply.elasticity_price],
                                           DataChange[Domains.ExogChangeSupply.elasticity_price],
                                           Shifter.except_shifter_zero.value,
                                           period_block=period_info["block"])
    
    periodic_trend = growth_dynamization(Data[Domains.Supply.quantity],
                                         DataChange[Domains.ExogChangeSupply.growth_rate_value],
                                         period_block=period_info["block"],
                                         period_length=period_info["length"])
    
    growth_gdp_or_stock = growth_dynamization(Data[Domains.Supply.quantity], 
                                              DataChange[Domains.ExogChangeSupply.growth_rate_gdp],
                                              period_block=period_info["block"],
                                              period_length=period_info["length"])
    
    gdp_periodic_growth = growth_dynamization(Data[Domains.Supply.quantity],
                                              DataChange[Domains.ExogChangeSupply.growth_rate_gdp],
                                              period_block=period_info["block"],
                                              period_length=period_info["length"])

    growth_fourth = growth_dynamization(Data[Domains.Supply.quantity],
                                        Data[Domains.Supply.elasticity_fourth] *
                                        DataChange[Domains.ExogChangeSupply.growth_rate_fourth_shift],
                                        period_block=period_info["block"],
                                        period_length=period_info["length"]
                                        )

    growth_fifth = growth_dynamization(Data[Domains.Supply.quantity],
                                       Data[Domains.Supply.elasticity_fifth] * 
                                       DataChange[Domains.ExogChangeSupply.growth_rate_fifth_shift],
                                       period_block=period_info["block"],
                                       period_length=period_info["length"])
    
    growth_sixth = growth_dynamization(Data[Domains.Supply.quantity],
                                       Data[Domains.Supply.elasticity_sixth] * 
                                       DataChange[Domains.ExogChangeSupply.growth_rate_sixth_shift],
                                       period_block=period_info["block"],
                                       period_length=period_info["length"])
    growth_df = dynamize_forest(DataForest, 
                                DataForestChange, 
                                Data, 
                                Logger, 
                                period_info=period_info)
    
    stock_periodic_growth = pd.concat([Data[Domains.Supply.region_code], growth_df], axis=1).fillna(0)[0]
    area_periodic_growth = pd.concat([Data[Domains.Supply.region_code], growth_df], axis=1).fillna(0)[1]

    paper_raw_commodities = sorted(list(set(self.Data.Supply.data[
                                                (self.Data.Supply.data[Domains.Supply.region_code] != zy_region_var) &
                                                (self.Data.Supply.data[Domains.Supply.commodity_code] >= 89)] # TODO hard code; maybe with list and not >=
                                            [Domains.Supply.commodity_code])))

    paper_supply_index = Data[[x not in paper_raw_commodities for x in Data[Domains.Supply.commodity_code]]].index

    paper_supply_shift = (1 + Data[Domains.Supply.elasticity_gdp] * gdp_periodic_growth)
    paper_supply_shift.loc[paper_supply_index] = 0
    dynamized_supply_paper = Data[Domains.Supply.quantity] * paper_supply_shift

    forest_raw_commodities = sorted(list(set(self.Data.Supply.data[
                                      (self.Data.Supply.data[Domains.Supply.region_code] != zy_region_var) &
                                      (self.Data.Supply.data[Domains.Supply.commodity_code] < 89)] # TODO hard code; maybe with list and not <
                                  [Domains.Supply.commodity_code])))

    fuelwood_roundwood_supply_index = Data[[x not in forest_raw_commodities for x in Data[Domains.Supply.commodity_code]
                                            ]].index

    fuelwood_roundwood_supply_shift = (1 + Data[Domains.Supply.elasticity_stock] * stock_periodic_growth
                                       + Data[Domains.Supply.elasticity_area] * area_periodic_growth)
    fuelwood_roundwood_supply_shift.loc[fuelwood_roundwood_supply_index] = 0

    supply_shifter = (paper_supply_shift + fuelwood_roundwood_supply_shift) * (1 + periodic_trend) - 1

    growth_rate_upper_bound = growth_dynamization(DomainData=Data[Domains.Supply.upper_bound],
                                                  ChangeData=DataChange[Domains.ExogChangeSupply.growth_rate_upper_bound],
                                                  shifter_exception=Shifter.except_shifter_minus_one.value,
                                                  shifter_switch=True,
                                                  ChangeData_Switch=supply_shifter,
                                                  period_block=period_info["block"],
                                                  period_length=period_info["length"])

    dynamized_supply_fuelwood_roundwood = Data[Domains.Supply.quantity] * fuelwood_roundwood_supply_shift
    dynamized_supply_fuelwood_roundwood.loc[fuelwood_roundwood_supply_index] = 0

    dynamized_supply_quantity = (dynamized_supply_fuelwood_roundwood + dynamized_supply_paper) * (1 + periodic_trend)

    dynamized_supply_quantity = dynamized_supply_quantity.clip(lower=0)

    Data[Domains.Supply.elasticity_price] = elasticity_price

    Data[Domains.Supply.quantity] = dynamized_supply_quantity
    Data["growth_rate_upper_bound"] = growth_rate_upper_bound # TODO hard code
    Data[Domains.Supply.elasticity_fourth] = growth_fourth
    Data[Domains.Supply.elasticity_fifth] = growth_fifth
    Data[Domains.Supply.elasticity_sixth] = growth_sixth


def dynamize_manufacturing_cost(Data: pd.DataFrame, DataChange: pd.DataFrame, period_info: dict):
    """
    Dynamization of manufacturing costs in three steps:
    first step: Read in exogenous change data
    second step: Calculate new manufacturing costs as manufacturing costs from previous period multiplied with exogenous
    periodic growth rate (formula 10 and 22 in Buongiorno (2015))
    third step: Overwrite data from previous period with new manufacturing costs
    :param Data: Aligned data of manufacturing costs (WorldData.ManufactureCost.data_aligned)
    :param DataChange: Aligned data of exogenous change in manufacturing costs
    (WorldData.ExogChangeManufactureCost.data_aligned)
    :param period_info: dict storing information on current period (period number, period length, year)
    """
    periodic_growth_manucost = growth_dynamization(
        Data[Domains.ManufactureCost.net_manufacturing_cost],
        DataChange[Domains.ExogChangeManufactureCost.growth_rate_net_manufacture_cost],
        period_block=period_info["block"], 
        period_length=period_info["length"]) 

    dynamized_manucosts = Data[Domains.ManufactureCost.net_manufacturing_cost] * (1 + periodic_growth_manucost)
    Data[Domains.ManufactureCost.net_manufacturing_cost] = dynamized_manucosts


def dynamize_manufacturing_coeff(Data: pd.DataFrame, DataChange: pd.DataFrame, period_info: dict):
    """
     Read in exogenous change data, calculate new manufacturing coefficients from previous period plus exogenous change
     in manufacturing coefficients, overwrite data from previous period with new data
    :param Data: Aligned data of manufacturing coefficients (ManufactureCoefficients.data_aligned)
    :param DataChange: Aligned data of exogenous change in manufacturing coefficients
    (ExogChangeManufactureCoefficients.data_aligned)
    :param period_info: dict storing information on current period (period number, period length, year)
    """

    change_manu_coeff = change_dynamization(
        Data[Domains.ManufactureCoefficients.quantity],
        DataChange[Domains.ExogChangeManufactureCoefficients.change_input_output],
        period_block=period_info["block"], # TODO Hard code (future work)
        period_length=period_info["length"]) # TODO Hard code (future work)

    dynamized_manu_coeff = Data[Domains.ManufactureCoefficients.quantity] + change_manu_coeff
    dynamized_manu_coeff[dynamized_manu_coeff < 0] = 0
    Data[Domains.ManufactureCoefficients.quantity] = dynamized_manu_coeff


def dynamize_transportation(DataExport: pd.DataFrame, DataImport: pd.DataFrame, DataExportChange: pd.DataFrame,
                            DataImportChange: pd.DataFrame, period_info: dict):
    """
    Read in exogenous change data and previous data, calculate new transport costs with shifted freight costs,
    import costs and export costs from exogenous change, overwrite data from previous period with new data. Calculation
    of expected_export_growth, expected_import_growth, export_elasticity and import_elasticity not activated.
    Exogenous change for these parameters will not be accounted in the dynamisation.
    :param DataExport: Aligned data of TransportationExport (WorldData.TransportationExport.data_aligned)
    :param DataImport: Aligned data of TransportationImport (WorldData.TransportationImport.data_aligned)
    :param DataExportChange: Aligned data of ExogChangeTradeExport (WorldData.ExogChangeTradeExport.data_aligned)
    :param DataImportChange: Aligned data of ExogChangeTradeEImport (WorldData.ExogChangeTradeEImport.data_aligned)
    """
    transp_cost_col_name = VarNames.TRANSPORT_COSTS.value

    export_ad_valorem_tax_rate = DataExport[Domains.TransportationExport.export_ad_valorem_tax_rate]
    import_ad_valorem_tax_rate = DataImport[Domains.TransportationImport.import_ad_valorem_tax_rate]
    export_price = DataExport[Domains.TransportationExport.price]
    import_price = DataImport[Domains.TransportationImport.price]
    freight_cost = DataImport[Domains.TransportationImport.freight_cost]

    export_trade_inertia_bounds = update_dynamization(
        DataExport[Domains.TransportationExport.trade_inertia_bounds],
        DataExportChange[Domains.ExogChangeTradeExport.trade_inertia_bounds],
        shifter_exception = Shifter.except_shifter_zero.value,
        period_block=period_info["block"])  # TODO Hard code (future work)
    
    import_trade_inertia_bounds = update_dynamization(
        DataImport[Domains.TransportationImport.trade_inertia_bounds],
        DataImportChange[Domains.ExogChangeTradeImport.trade_inertia_bounds],
        shifter_exception = Shifter.except_shifter_zero.value,
        period_block=period_info["block"])

    expected_export_growth = growth_dynamization(
        DataExport[Domains.TransportationExport.quantity],
        DataExportChange[Domains.ExogChangeTradeExport.exogenous_growth_rate_export_trade_shift],
        period_block=period_info["block"],
        period_length=period_info["length"])  # TODO Hard code (future work)
    
    expected_import_growth = growth_dynamization(
        DataImport[Domains.TransportationImport.quantity],
        DataImportChange[Domains.ExogChangeTradeImport.exogenous_growth_rate_import_trade_shift],
        period_block=period_info["block"],
        period_length=period_info["length"])
    
    export_elasticity = update_dynamization(
        DataExport[Domains.TransportationExport.elasticity_trade_exporter],
        DataExportChange[Domains.ExogChangeTradeExport.elasticity_trade_exporter_shift],
        period_block=period_info["block"])
    
    import_elasticity = update_dynamization(
        DataImport[Domains.TransportationImport.elasticity_trade_importer],
        DataImportChange[Domains.ExogChangeTradeImport.elasticity_trade_importer_shift],
        period_block=period_info["block"])
    
    delta_export_ad_valorem_tax_rate = change_dynamization(
        export_ad_valorem_tax_rate,
        DataExportChange[Domains.ExogChangeTradeExport.change_export_tax_rate],
        period_block=period_info["block"],
        period_length=period_info["length"])
    
    delta_import_ad_valorem_tax_rate = change_dynamization(
        import_ad_valorem_tax_rate,
        DataImportChange[Domains.ExogChangeTradeImport.change_import_tax_rate],
        period_block=period_info["block"],
        period_length=period_info["length"])

    delta_freight_cost = change_dynamization(
        freight_cost,
        DataImportChange[Domains.ExogChangeTradeImport.change_freight_cost],
        period_block=period_info["block"],
        period_length=period_info["length"])

    # TODO define variable names for import costs in delimination to freight costs and ad valorem tax rates (future work)
    freight_cost = freight_cost + delta_freight_cost
    import_tax = (import_ad_valorem_tax_rate * delta_import_ad_valorem_tax_rate) * (freight_cost + import_price)
    export_tax = (export_ad_valorem_tax_rate * delta_export_ad_valorem_tax_rate) * export_price
    transport_cost = freight_cost + import_tax + export_tax

    DataImport[Domains.TransportationImport.trade_inertia_bounds] = import_trade_inertia_bounds
    DataExport[Domains.TransportationExport.trade_inertia_bounds] = export_trade_inertia_bounds
    DataImport[transp_cost_col_name] = transport_cost


def constraint_get_position(constraints_position: dict, constraint_name: str, constraint_list: list,
                            constraint_counter: list):
    """
    Retrieves the indexes of a specific constraints in the list of constraints for the optimization and saves it into
    a dictionary used for extraction of shadowprices
    :param constraints_position: dict where information (constraint name and position) are saved for the result
    extraction
    :param constraint_name: name of the specific constraint
    :param constraint_list: list of constraints in which specific constraint is saved
    :param constraint_counter: counter tracking of the number of constraints in constraints_position
    """
    if not bool(constraints_position):
        constraints_position[f"{constraint_name}"] = [constraint_counter[0], len(constraint_list)]

    else:
        constraints_position[f"{constraint_name}"] = [list(constraints_position.values())[constraint_counter[0]][1],
                                                      len(constraint_list)]
        constraint_counter[0] += 1


def extract_product_groups(world_data, commodity_data: pd.DataFrame, region_data: pd.DataFrame, all_regions: bool,
                           only_commodity_codes: bool):
    """
    Creates helper vector for product group for material balance based on information provided by the world. Commodity
    structure from the world is automatically retrieved based on Supply.data for raw materials, on Demand.data for final
    products and on ManufactureCost.data and Demand.data for intermediate products (defined as products that have
    manufacture costs but are not demanded).
    :param world_data: Complete data of World Data container
    :param commodity_data: DataFrame with commodity codes and commodity names
    :param region_data: DataFrame with region codes and region names
    :param all_regions: Flag, allowing to create a help vector with different lengths:
     If set True: creates a help vector for all countries and commodities (len(countries) * len(products)) (data aligned)
     If set False: creates a help vector for all commodities (len(products))
    :param only_commodity_codes: Flag, allowing to select if only commodity codes for the different product categories
    are returned. If set True: only commodity codes are return; If set False: all generated data are returned.
    :return: product group vectors for raw products, intermediate products, final products, fuelwood and
    other industrial roundwood
    """
    zy_region_var = VarNames.ZY_REGION.value

    if all_regions:
        vector_len = commodity_data.df_length * (region_data.df_length - 1)
        commodity_data = world_data.data_aligned[:vector_len][Domains.Commodities.commodity_code]
    else:
        vector_len = commodity_data.df_length
        commodity_data = commodity_data.data[Domains.Commodities.commodity_code]

    commodity_list = list(world_data.Commodities.data[Domains.Commodities.commodity_code])
    produced_commodity_list = list(set(world_data.ManufactureCost.data[Domains.Commodities.commodity_code]))
    processed_commodity_list = list(set(
        world_data.ManufactureCoefficients.data[Domains.ManufactureCoefficients.commodity_code]))
    traded_commodity_list = list(set(world_data.TransportationExport.data[Domains.Commodities.commodity_code]))

    raw_materials_select = [x not in processed_commodity_list for x in commodity_list]
    produced_commodity_select = [x not in produced_commodity_list for x in commodity_list]
    traded_commodity_select = [x in traded_commodity_list for x in commodity_list]

    fuelw = [x for x, y, z, w in zip(commodity_list,
                                     raw_materials_select,
                                     traded_commodity_select,
                                     produced_commodity_select) if y and z and w is True][0]

    othindrnd = [x for x, y, z in zip(commodity_list,
                                      raw_materials_select,
                                      traded_commodity_select) if (y is True) and (z is False)][0]

    raw_prod = sorted(list(set(
        world_data.Supply.data[
            (world_data.Supply.data[Domains.Supply.region_code] != zy_region_var) &
            (world_data.Supply.data[Domains.Supply.commodity_code] != fuelw) &
            (world_data.Supply.data[Domains.Supply.commodity_code] != othindrnd)][Domains.Supply.commodity_code])))

    raw_prod_vector = np.where([x in raw_prod for x in commodity_data], 1, 0).reshape(vector_len, 1)

    fin_prod = sorted(list(set(
        world_data.Demand.data[
            (world_data.Demand.data[Domains.Demand.region_code] != zy_region_var) &
            (world_data.Demand.data[Domains.Demand.commodity_code] != fuelw) &
            (world_data.Demand.data[Domains.Demand.commodity_code] != othindrnd)][Domains.Demand.commodity_code])))

    fin_prod_vector = np.where([x in fin_prod for x in commodity_data], 1, 0).reshape(vector_len, 1)

    interm_prod = sorted(list(set(world_data.ManufactureCost.data[Domains.ManufactureCost.commodity_code])))

    interm_prod = list(np.array(interm_prod)[np.array([x not in fin_prod for x in interm_prod])])
    interm_prod_vector = np.where([x in interm_prod for x in commodity_data], 1, 0).reshape(vector_len, 1)

    fuelw_vector = np.array(np.where((commodity_data == fuelw), 1, 0).reshape(vector_len, 1))

    othindrnd_vector = np.array(np.where((commodity_data == othindrnd), 1, 0).reshape(vector_len, 1))

    if only_commodity_codes:
        return raw_prod, interm_prod, fin_prod, fuelw, othindrnd
    else:
        return (raw_prod_vector, interm_prod_vector, fin_prod_vector, fuelw_vector, othindrnd_vector,
                raw_prod, interm_prod, fin_prod, fuelw, othindrnd)


def calc_product_shadow_price(self, world_data: InterfaceWorldData, domain: str, price_column: str, constraints: list,
                              constraints_position: dict):
    """
    Extract shadow prices (dual values) from optimization. Depending on chosen material balance type in user input.
    RCG_specific MB region and commodity groups specific material balance
    RC_specific MB region and commodity specific material balance
    C_specific MB commodity specific material balance
    :param world_data: Complete data of World Data container
    :param domain: name of specific domain
    :param price_column: column with price data of specific domain
    :param constraints: list of all constraints used in optimization
    :param constraints_position: dictionary of all constraints specifying indexes
    :return: shadow_price
    """
    material_balance_col_name = VarNames.MATERIAL_BALANCE.value
    c_specific_mb_var = VarNames.C_SPECIFIC_MB.value
    rc_specific_mb_var = VarNames.RC_SPECIFIC_MB.value
    rcg_specific_mb_var = VarNames.RCG_SPECIFIC_MB.value

    shadow_product_price = pd.DataFrame()

    if self.UserOptions.material_balance == rcg_specific_mb_var:
        # Extraction of shadow prices for country and commodity specific material balance
        for region_num in range(0, len(world_data.data_aligned) - world_data.Commodities.df_length):

            shadow_product_price = pd.concat([
                shadow_product_price,
                pd.DataFrame(abs(
                    constraints[constraints_position[material_balance_col_name][0] + region_num].dual_value))
            ], axis=0).reset_index(drop=True)

    if self.UserOptions.material_balance == rcg_specific_mb_var:
        # Extraction of shadow prices for country and commodity group specific material balance
        for region_num in range(0, world_data.Regions.df_length - 1):
            tmp_shadow_product_price = pd.DataFrame(np.zeros([world_data.Commodities.df_length, 1]))
            for prod_category in range(0, 5):
                tmp_shadow_product_price = tmp_shadow_product_price + pd.DataFrame(
                    constraints[
                        constraints_position[material_balance_col_name][0] + region_num + prod_category].dual_value)

            shadow_product_price = pd.concat([shadow_product_price,
                                              abs(tmp_shadow_product_price)], axis=0).reset_index(drop=True)

    if self.UserOptions.material_balance == c_specific_mb_var:
        # Extraction of shadow prices for commodity specific material balance
        commodity_vector = world_data.data_aligned[Domains.Commodities.commodity_code].iloc[:(
                len(self.Data.data_aligned) - len(self.Data.Commodities.data))]
        for commodity, commodity_num in zip(world_data.Commodities.data[Domains.Commodities.commodity_code],
                                            range(0, world_data.Commodities.df_length)):
            commodity_index = commodity_vector[commodity_vector == commodity].index
            tmp_shadow_product_price = pd.DataFrame(constraints[constraints_position[material_balance_col_name][0] +
                                                                commodity_num].dual_value).set_index(commodity_index)
            shadow_product_price = pd.concat([shadow_product_price, abs(tmp_shadow_product_price)], axis=0)
        shadow_product_price = shadow_product_price.sort_index()

    zy_price_placeholder = pd.DataFrame(np.zeros(world_data.Commodities.df_length))
    shadow_price = pd.concat([shadow_product_price, zy_price_placeholder]).reset_index(drop=True)

    # Select shadow prices corresponding to the actual domain

    help_vector = pd.DataFrame(np.where(world_data[domain].data_aligned[price_column] > 0, 1, 0))
    shadow_price = shadow_price * help_vector

    shadow_price.fillna(0, inplace=True)
    shadow_price.replace(np.inf, 0, inplace=True)
    shadow_price.replace(-np.inf, 0, inplace=True)

    return shadow_price


def calc_world_shadow_price(world_data: InterfaceWorldData, constraints: list, constraints_position: dict):
    """
    Extract shadow prices (dual values) from optimization for world market.
    :param world_data: Complete data of World Data container
    :param constraints: list of all constraints used in optimization
    :param constraints_position: dictionary of all constraints specifying indexes
    :returns: shadow_world_price
    """
    zy_export_col_name = VarNames.ZY_EXPORT.value
    zy_import_col_name = VarNames.ZY_IMPORT.value
    zy_region_var = VarNames.ZY_REGION.value

    zy_region = world_data.data_aligned[world_data.data_aligned[Domains.Regions.region_code] == zy_region_var]
    zy_import = world_data.TransportationImport.data_aligned[
        Domains.TransportationImport.region_code].loc[zy_region.index]
    zy_export = world_data.TransportationExport.data_aligned[
        Domains.TransportationExport.region_code].loc[zy_region.index]

    zy_import = pd.DataFrame(np.where(np.array(zy_import) != 0, 1, 0))
    zy_export = pd.DataFrame(np.where(np.array(zy_export) != 0, 1, 0))

    shadow_world_price_import = pd.DataFrame()
    shadow_world_price_export = pd.DataFrame()

    for commodity_num in range(0, world_data.Commodities.df_length):
        shadow_world_price_import_temp = pd.DataFrame(
            abs(constraints[constraints_position[zy_import_col_name][0] + commodity_num].dual_value))
        shadow_world_price_export_temp = pd.DataFrame(
            abs(constraints[constraints_position[zy_export_col_name][0] + commodity_num].dual_value))
        shadow_world_price_import = pd.concat([
            shadow_world_price_import, shadow_world_price_import_temp]).reset_index(drop=True)
        shadow_world_price_export = pd.concat([
            shadow_world_price_export, shadow_world_price_export_temp]).reset_index(drop=True)

    shadow_world_price_import = shadow_world_price_import[0] * zy_import[0]
    shadow_world_price_export = shadow_world_price_export[0] * zy_export[0]
    shadow_world_price = shadow_world_price_export + shadow_world_price_import

    shadow_world_price = pd.concat(
        [shadow_world_price] * len(world_data.Regions.data), axis=0).reset_index(drop=True)

    shadow_world_price.fillna(0, inplace=True)
    shadow_world_price.replace(np.inf, 0, inplace=True)
    shadow_world_price.replace(-np.inf, 0, inplace=True)

    return shadow_world_price


def calc_product_price(world_data: InterfaceWorldData, domain: str, price_column: str, quantity_column: str,
                       elasticity_column: str, opt_quantity_clean: pd.DataFrame):
    """
    Calculate prices for all domains and products. Alternative approach to shadow prices for product price calculation.
    Selectable via user input. Calculations based on equations xxx.
    :param world_data: Complete data of World Data container
    :param domain: name of specific domain
    :param price_column: name of column with price data of specific domain
    :param quantity_column: name of column with quantity data of specific domain
    :param elasticity_column: name of column with elasticity data of specific domain
    :param opt_quantity_clean: optimized quantity data cleaned with lower and upper bounds in extract_optimization_results
    :returns: calculated product prices for each domain
    """
    calculated_price = world_data[domain].data_aligned[price_column] * (
            (opt_quantity_clean / world_data[domain].data_aligned[quantity_column]) **
            world_data[domain].data_aligned[elasticity_column]
    )

    calculated_price.fillna(0, inplace=True)
    calculated_price.replace(np.inf, 0, inplace=True)
    calculated_price.replace(-np.inf, 0, inplace=True)

    return calculated_price


def shadow_price_correction(deviation_threshold: int, domain_name: str, shadow_price_prev: pd.Series,
                            shadow_price_new: pd.Series, calc_price_new: pd.Series, logger):
    """
    Corrects shadow prices if deviation from the shadow prices in previous period is higher than the determined
    threshold. These shadow prices are corrected by their replacement with calculated prices
    :param deviation_threshold: defined threshold for deviation from shadow prices in the previous period
    :param domain_name: name of the selected domain
    :param shadow_price_prev: shadow prices from the previous period
    :param shadow_price_new: shadow prices from the actual period
    :param calc_price_new: calculated prices from the actual period
    :param logger: Logger method

    :return: corrected shadow prices

    """
    price_deviation = shadow_price_prev / shadow_price_new
    price_deviation.fillna(0, inplace=True)
    index_corrected_value = price_deviation[((price_deviation <= 1 - deviation_threshold) &
                                             (price_deviation != 0)) |
                                            (price_deviation >= 1 + deviation_threshold)].index
    logger.info(f"Number of corrected shadow prices in {domain_name}: {len(index_corrected_value)}")

    shadow_price_new.loc[index_corrected_value] = calc_price_new.loc[index_corrected_value]
    return shadow_price_new


def save_price_data(world_data: InterfaceWorldData, calc_price: pd.Series, shadow_price: pd.Series,
                    domain_name: str, index_domain: np.array, domain_price_name: str, price_col_name: str,
                    shadow_price_col_name: str, calc_product_prices_flag: str, world_price: pd.Series):
    """
    Saves prices in the domain dataframe (world_data[domain_name].data_aligned), in the optimization helpers dataframe
    (world_data.OptimizationHelpers.data) in columns price and shadow price. Depending on user input either calculated
    or shadow prices are saved in the domain and the optimization helpers dataframe.
    :param world_data: interface world data
    :param calc_price: vector of calculated prices
    :param shadow_price: vector of shadow prices
    :param domain_name: name of the selected domain
    :param index_domain: index of the selected doamin in optimization helpers dataframe
    :param domain_price_name: column name of price vector in each domain
    :param price_col_name: column name of price vector in optimization helpers dataframe
    :param shadow_price_col_name: column name of shadow price vector in optimization helpers dataframe
    :param calc_product_prices_flag: flag for the used prices based on user input (shadow or calculcated prices)
    """

    shadow_prod_price_var = VarNames.SHADOW_PROD_PRICE.value
    calc_prod_price_var = VarNames.CALC_PROD_PRICE.value

    total_production_cost_col_name = VarNames.TOTAL_PRODUCTION_COST.value
    if str(Domains.TransportationImport) not in domain_name or str(Domains.TransportationImport) not in domain_name:
        # For supply, demand and manucost
        if (calc_product_prices_flag == calc_prod_price_var) or str(Domains.ManufactureCost) in domain_name:
            world_data[domain_name].data_aligned[domain_price_name] = abs(calc_price)
            if str(Domains.ManufactureCost) in domain_name:
                world_data.OptimizationHelpers.data.loc[index_domain, price_col_name] = pd.DataFrame(
                    world_data[domain_name].data_aligned[total_production_cost_col_name]).set_index(
                    index_domain)[total_production_cost_col_name]
            else:
                world_data.OptimizationHelpers.data.loc[index_domain, price_col_name] = pd.DataFrame(
                    abs(calc_price)).set_index(index_domain)[0]
        if calc_product_prices_flag == shadow_prod_price_var and str(Domains.ManufactureCost) not in domain_name:
            world_data[domain_name].data_aligned[domain_price_name] = abs(shadow_price)
            world_data.OptimizationHelpers.data.loc[index_domain, price_col_name] = pd.DataFrame(
                abs(shadow_price)).set_index(index_domain)[0]

    else:
        # For TransportationImport and TransportationExport
        world_data[domain_name].data_aligned[price_col_name] = abs(world_price)

        world_data.OptimizationHelpers.data.loc[index_domain, price_col_name] = pd.DataFrame(
            abs(world_price)).set_index(index_domain)[0]

    world_data.OptimizationHelpers.data.loc[index_domain, shadow_price_col_name] = pd.DataFrame(
        abs(shadow_price)).set_index(index_domain)[0]
