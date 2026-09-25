import cvxpy.error
import pandas as pd
import numpy as np
import cvxpy as cp
from logging import Logger

from TiMBA.results_logging.ResultsWriter import ResultsWriter
from TiMBA.data_management.DataManager import DataManager
from TiMBA.data_management.DataContainer import (
    DataContainer, InterfaceWorldData, AdditionalInformation, WorldPriceData)
from TiMBA.data_validation.DataValidator import DataValidator
from TiMBA.parameters.Defines import (VarNames, Constants, SolverParameters, ConversionParameters)
from TiMBA.helpers.utils import DomainIterator
from TiMBA.data_management.ParameterCollector import ParameterCollector
from TiMBA.parameters.Domains import Domains
from TiMBA.logic.model_helpers import (
    calc_slope_inverted, calc_slope_regular, calc_intercept, dynamize_demand, dynamize_manufacturing_coeff,
    dynamize_manufacturing_cost, dynamize_supply, dynamize_transportation, actual_period, production_price_calculation,
    transport_cost_calculation, forest_param_alpha, forest_param_gamma, constraint_get_position,
    extract_product_groups, calc_product_shadow_price, calc_world_shadow_price, calc_product_price,
    shadow_price_correction, save_price_data)
from TiMBA.logic.tests import (verify_trade_balance, verify_material_balance, verify_global_material_balance,
                        verify_supply_upper_bound, verify_trade_bounds)


class TiMBA(object):

    def __init__(self,
                 Data: InterfaceWorldData,
                 UserOptions: ParameterCollector,
                 AdditionalInfo: AdditionalInformation,
                 WorldPriceData: WorldPriceData,
                 LogHandler: Logger,
                 #ResultHandler: ResultsWriter,
                 ):
        self.Data = Data
        self.UserOptions = UserOptions
        self.AdditionalInfo = AdditionalInfo
        self.WorldPriceData = WorldPriceData
        self.Logger = LogHandler
        #self.ResultHandler = ResultHandler
        self.period_df = actual_period(self.Data.periods_forecast, self.UserOptions.year, self.UserOptions.max_period)

        # Runner Variables
        self.present_period = None
        self.period_length = None

    def compute(self, max_iteration: int, rel_accuracy: int, abs_accuracy: int, dynamization_activated: bool,
                constants: list, capped_prices: bool):
        """Loop model calculation over existing periods (execute methods and store results of the model)
        :param max_iteration: Maximal number of periods
        :param rel_accuracy: relative accuracy of the solver
        :param abs_accuracy: absolute accuracy of the solver
        :param dynamization_activated: dynamization of the model on or off #TODO remove after validation?
        :param constants: list where the user can choose to run model with constant prices, slopes or intercepts #TODO remove after validation?
        :param capped_prices: flag for correction of production prices (demprices=prodprices) #TODO remove after validation?
        """
        for self.present_period, period_block, self.period_length, self.actual_year in zip(
                self.period_df["Period"], #TODO Hard code (future work)
                self.period_df["PeriodBlock"],
                self.period_df["PeriodLength"],
                self.period_df["ActualYear"]):
            print()
            self.Logger.info(f"Computing model for Period: {self.present_period}, Period length: {self.period_length},"
                             f" ActualYear: {self.actual_year}")
            if self.present_period == 0:
                # Execute base period
                if self.UserOptions.verbose_calculation_logger:
                    print(self.period_df)
                self.base_period_compute(capped_prices=capped_prices)

            else:
                # Execute following periods
                self.Logger.info(f"Start computation for Period: {self.present_period}")
                if dynamization_activated:
                    self.Logger.info(f"Dynamization activated")
                    self.dynamize(present_period=self.present_period,
                                  period_length=self.period_length,
                                  period_block=period_block,
                                  actual_year=self.actual_year)
                self.follow_periods_compute(capped_prices=capped_prices)

            self.loop_slope_intercept_calculation(constant_prices=constants[0],
                                                  constant_slopes=constants[1],
                                                  constant_intercepts=constants[2])
            
            self.vectorize_domains()
            try:
                self.optimization(solver_max_iteration=max_iteration,
                                  solver_rel_accuracy=rel_accuracy,
                                  solver_abs_accuracy=abs_accuracy,
                                  dynamization_activated=dynamization_activated)

                self.extract_optimization_results(
                    opt_quantity=self.Data.OptimizationResults.optimized_quantity,
                    constraints=self.Data.OptimizationResults.optimization_constraints,
                    constraints_position=self.Data.OptimizationResults.optimization_constraints_position,
                    opt_ubs=self.Data.OptimizationResults.optimization_upper_bound,
                    opt_lbs=self.Data.OptimizationResults.optimization_lower_bound,
                    capped_prices=capped_prices,
                    cleaned_opt_quantity=self.UserOptions.cleaned_opt_quantity)
            except BaseException as b_err:
                self.Logger.error(f"Optimization failed for period {self.present_period}.", exc_info=True)
                break
            DataManager.update_periods(self.Data, period=self.present_period)

        DataManager.get_additional_output(self.Data, self.Data.OptimizationHelpers.data_periods, self.Data.Regions.data)

    def follow_periods_compute(self, capped_prices: bool):
        """
        Computation and overwrite attributes of following periods. Update IO-matrix, production prices, fuelwood from forest,
        transport cost, import cost, export cost (... ). Updates are stored in domain dataframes. #TODO Buongiorno 2015 Formula 21, 22, 23)
        :param capped_prices: flag for correction of production prices (demprices=prodprices) #TODO remove after validation?
        """
        # Update IO-Coefficients
        DataManager.create_io_matrix(self.Data, update=True, default_io=False)

        # Update fuelwood from forest parameter
        DataManager.update_fuelwood_forest_param(self.Data)

        # TODO export to seperate function (begin here, future work)
        # Import and export calculation
        transp_cost_col_name = VarNames.TRANSPORT_COSTS.value

        ImportData = self.Data.TransportationImport.data_aligned
        ExportData = self.Data.TransportationExport.data_aligned
        WorldPrice = self.Data.WorldPrices.data_periods
        RegionsData = self.Data.Regions.df_length

        #TODO keep next comment for possible calculation alternatives with exegenous world price
        #exogen_world_price = pd.concat([WorldPrice["WorldPrice"]] * RegionsData).reset_index(drop=True)

        importing_regions = pd.DataFrame(np.where(np.array(ImportData[Domains.TransportationImport.quantity]) > 
                                                  Constants.NON_ZERO_PARAMETER.value, 1, 0))[0]
        world_price = pd.concat([WorldPrice[WorldPrice["Period"] == self.present_period - 1]["WorldPrice"] #TODO Hard coded (future work)
                                 ] * RegionsData).reset_index(drop=True)
        import_price = world_price + ImportData[transp_cost_col_name]

        ImportData[Domains.TransportationImport.price] = import_price * importing_regions
        ExportData[Domains.TransportationExport.price] = world_price
        # TODO export to seperate function (end here, future work)

        # Production price calculation
        production_price_calculation(self,
                                     AlignedData=self.Data.data_aligned,
                                     RegionsData=self.Data.Regions.data,
                                     SupplyData=self.Data.Supply.data_aligned,
                                     ImportData=self.Data.TransportationImport.data_aligned,
                                     ioMatrix=self.Data.ManufactureCoefficients.ioMatrix,
                                     ManufactureCostData=self.Data.ManufactureCost.data_aligned,
                                     capped_prices=capped_prices)

    def base_period_compute(self, capped_prices: bool):
        """
        Computation and overwrite attributes of base period. Calculate production prices,
        transport cost, import cost, export cost. Results are stored in domain dataframes.
        :params capped_prices: flag for correction of production prices (demprices=prodprices) #TODO remove after validation?
        """
        self.Logger.info(f"Start computation of Base-Period.")

        # transport cost calculation
        transport_cost_calculation(ImportData=self.Data.TransportationImport.data_aligned,
                                   ExportData=self.Data.TransportationExport.data_aligned,
                                   WorldPrice=self.Data.WorldPrices.data,
                                   RegionsData=self.Data.Regions.df_length)

        # production price calculation
        production_price_calculation(self,
                                     AlignedData=self.Data.data_aligned,
                                     RegionsData=self.Data.Regions.data,
                                     SupplyData=self.Data.Supply.data_aligned,
                                     ImportData=self.Data.TransportationImport.data_aligned,
                                     ioMatrix=self.Data.ManufactureCoefficients.ioMatrix,
                                     ManufactureCostData=self.Data.ManufactureCost.data_aligned,
                                     capped_prices=capped_prices)

        # forest parameters calculation (alpha and gamma)
        self.Data.Forest.data_aligned["alpha"] = forest_param_alpha(ForestData=self.Data.Forest.data_aligned) #TODO Hard coded (future work)
        self.Data.Forest.data_aligned["gamma"] = forest_param_gamma(ForestData=self.Data.Forest.data_aligned) #TODO Hard coded (future work)

    def loop_slope_intercept_calculation(self, constant_prices: bool = True, constant_slopes: bool = True,
                                         constant_intercepts: bool = True):
        """
        Slope and intercept calculation looped over optimization domains, specifying regular functions
         (ManufactureCost) and inverted functions (TransportImport, TransportExport, Demand and Supply)
         :param: InterfaceWorldData
         :param constant_prices: flag to set prices as constant based on the base period prices for slope and
          intercept calculation
         :param constant_slopes: flag to set slopes as constant based on the base period slopes
         :param constant_intercepts: flag to set intercepts as constant based on the base period intercepts
         :return: slopes and intercepts for optimization domains
         """
        if self.UserOptions.verbose_calculation_logger:
            self.Logger.info(f"Settings for slope_intercept_calculation:")
            self.Logger.info(f"constant_prices: {constant_prices}\n"
                             f"constant_slopes: {constant_slopes}\n"
                             f"constant_intercepts: {constant_intercepts}")

        for domain_name, price, quantity, elasticity_price in DomainIterator.get_info_slope_intercept_calculation(
                DomainIterator.OPTIMIZATION_DOMAINS):
            quantity_values = self.Data[domain_name].data_aligned[quantity].copy()
            elasticity_price = self.Data[domain_name].data_aligned[elasticity_price]
            present_period = self.present_period

            domain_col_name = VarNames.DOMAIN_COLNAME.value
            period_col_name = VarNames.PERIOD_COLNAME.value
            price_col_name = VarNames.PRICE_COLNAME.value
            slope_col_name = VarNames.SLOPE_COLNAME.value
            intercept_col_name = VarNames.INTERCEPT_COLNAME.value

            if constant_prices and (present_period > 0):
                self.Data[domain_name].data_aligned[price] = (
                    self.Data.OptimizationHelpers.data_periods[
                        (self.Data.OptimizationHelpers.data_periods[domain_col_name] == domain_name) &
                        (self.Data.OptimizationHelpers.data_periods[period_col_name] == 0)][price_col_name]
                ).reset_index(drop=True)

            if constant_slopes and (present_period > 0):
                self.Data[domain_name].data_aligned[slope_col_name] = (
                    self.Data.OptimizationHelpers.data_periods[
                        (self.Data.OptimizationHelpers.data_periods[domain_col_name] == domain_name) &
                        (self.Data.OptimizationHelpers.data_periods[period_col_name] == 0)][slope_col_name]
                ).reset_index(drop=True)
            else:
                if str(Domains.ManufactureCost) in domain_name:
                    price_data = self.Data[domain_name].data_aligned[Domains.ManufactureCost.net_manufacturing_cost]
                    self.Data[domain_name].data_aligned[slope_col_name] = (
                        calc_slope_regular(self,
                                           domain_name,
                                           elasticity_price,
                                           price_data,
                                           quantity_values))
                else:
                    # TODO check relevance of this passage on impact on results:
                    # clean slopes from outliers due to no quantity or no price
                    helper_index = self.Data[domain_name].data_aligned[
                        ((self.Data[domain_name].data_aligned[quantity] <= 1) &
                         (self.Data[domain_name].data_aligned[price] <= 0)) |
                        (self.Data[domain_name].data_aligned[quantity] <= 0.0001)].index # TODO hard code (future work)
                    elasticity_price_clean = elasticity_price.copy()
                    # elasticity_price_clean.loc[helper_index] = 0

                    self.Data[domain_name].data_aligned[slope_col_name] = (
                        calc_slope_inverted(self,
                                            domain_name,
                                            elasticity_price_clean,
                                            self.Data[domain_name].data_aligned[price],
                                            quantity_values))

            if constant_intercepts and (present_period > 0):
                self.Data[domain_name].data_aligned[intercept_col_name] = (
                    self.Data.OptimizationHelpers.data_periods[
                        (self.Data.OptimizationHelpers.data_periods[domain_col_name] == domain_name) &
                        (self.Data.OptimizationHelpers.data_periods[period_col_name] == 0)][intercept_col_name]
                ).reset_index(drop=True)
            else:
                if str(Domains.ManufactureCost) in domain_name:
                    # price_data = self.Data[domain_name].data_aligned["total_production_costs"]
                    price_data = self.Data[domain_name].data_aligned[Domains.ManufactureCost.net_manufacturing_cost]
                    self.Data[domain_name].data_aligned[intercept_col_name] = (
                        calc_intercept(self,
                                       domain_name,
                                       price,
                                       price_data,
                                       self.Data[domain_name].data_aligned[slope_col_name],
                                       quantity_values))

                else:
                    # todo clean slopes from outliers due to no quantity or no price
                    price_clean = self.Data[domain_name].data_aligned[price].copy()
                    # price_clean.loc[helper_index] = 0

                    self.Data[domain_name].data_aligned[intercept_col_name] = (
                        calc_intercept(self,
                                       domain_name,
                                       price,
                                       price_clean,
                                       self.Data[domain_name].data_aligned[slope_col_name],
                                       quantity_values))

            try:
                # TODO: Integrate DataValidator for Slope/Intercepts, set correct sign args for slope/intercept wrt domain
                check_result = DataValidator.check_slope_intercept(
                    self.Data[domain_name].data_aligned[slope_col_name],
                    self.Data[domain_name].data_aligned[intercept_col_name],
                    sign_slope=1,
                    sign_intercept=-1)
                if not all(check_result):
                    if self.UserOptions.verbose_calculation_logger:
                        self.Logger.info(f"Slope/Intercept check failed for {domain_name}. Results:"
                                         f"Slope: {' correct' if check_result[0] is True else ' incorrect'}"
                                         f"Intercept: {' correct' if check_result[1] is True else ' incorrect'}")
            except Exception:
                self.Logger.error(f"{DataValidator.check_slope_intercept.__qualname__} failed.", exc_info=True)

    def set_bounds(self, dynamization_activated: bool):
        """
        Set bounds for demand, supply, supply recycled, import, export and manufacture.
        :param dynamization_activated: dynamization of the model on or off  #TODO remove after validation?
        :return: two np.arrays about upper and lower bounds for all domains
        """
        self.Logger.info(f"Setting bounds.")
        zy_region_var = VarNames.ZY_REGION.value

        demand_upper_bound = self.Data.Demand.data_aligned[Domains.Demand.quantity] * 1.25 # TODO check relevance of this passage on impact on results:
        lower_bound = pd.DataFrame(self.Data.Demand.data_aligned[[Domains.Demand.region_code,
                                                                  Domains.Demand.lower_bound]])
        index_correction = lower_bound[(lower_bound[Domains.Demand.region_code] == zy_region_var)].index
        lower_bound.loc[index_correction, Domains.Demand.lower_bound] = 0
        demand_lower_bound = lower_bound[Domains.Demand.lower_bound]

        manu_lower_bound = self.Data.ManufactureCost.data_aligned[Domains.ManufactureCost.quantity] * 0 #ToDo Hard code future work
        non_producing_region = self.Data.ManufactureCost.data_aligned[
            self.Data.ManufactureCost.data_aligned[Domains.ManufactureCost.net_manufacturing_cost] == 0
            ].index
        producing_region = self.Data.ManufactureCost.data_aligned[
            self.Data.ManufactureCost.data_aligned[Domains.ManufactureCost.net_manufacturing_cost] > 0
            ].index
        manu_upper_bound = self.Data.ManufactureCost.data_aligned[Domains.ManufactureCost.quantity].copy()
        manu_upper_bound.loc[non_producing_region] = manu_upper_bound.loc[non_producing_region] * 0
        manu_upper_bound.loc[producing_region] = manu_upper_bound.loc[producing_region] * 10000 #ToDo Hard Code

        supply_lower_bound = self.Data.Supply.data_aligned[Domains.Supply.lower_bound]

        if self.present_period == 0:

            supply_upper_bound = pd.Series(
                np.where(np.array(self.Data.Supply.data_aligned[Domains.Supply.upper_bound]) == 0,
                         Constants.BOUND_OMITTED_VALUE.value,
                         np.array(self.Data.Supply.data_aligned[Domains.Supply.upper_bound])))

            zy_region = len(self.Data.data_aligned) - len(self.Data.Commodities.data)
            other_regions = len(self.Data.data_aligned) - len(self.Data.Commodities.data)

            trade_inertia_export = self.Data.TransportationExport.data_aligned[
                                       Domains.TransportationExport.trade_inertia_bounds][:other_regions]
            trade_inertia_import = self.Data.TransportationImport.data_aligned[
                                       Domains.TransportationImport.trade_inertia_bounds][:other_regions]
            trade_inertia_export_zy = self.Data.TransportationExport.data_aligned[
                                          Domains.TransportationExport.trade_inertia_bounds][zy_region:]
            trade_inertia_import_zy = self.Data.TransportationImport.data_aligned[
                                          Domains.TransportationImport.trade_inertia_bounds][zy_region:]

            export_prev = self.Data.TransportationExport.data_aligned[Domains.TransportationExport.quantity][
                          :other_regions]
            import_prev = self.Data.TransportationImport.data_aligned[Domains.TransportationImport.quantity][
                          :other_regions]
            export_prev_zy = self.Data.TransportationExport.data_aligned[Domains.TransportationExport.quantity][
                             zy_region:]
            import_prev_zy = self.Data.TransportationImport.data_aligned[Domains.TransportationImport.quantity][
                             zy_region:]

            trade_inertia_deviation = Constants.TRADE_INERTIA_DEVIATION.value
            trade_inertia_deviation_zy = Constants.TRADE_INERTIA_DEVIATION_ZY.value

            export_lower_bound = (export_prev * (1 - trade_inertia_export - trade_inertia_deviation))
            export_lower_bound_zy = (export_prev_zy * (1 - trade_inertia_export_zy - trade_inertia_deviation_zy))

            export_upper_bound = (export_prev * (1 + trade_inertia_export + trade_inertia_deviation))
            export_upper_bound_zy = (export_prev_zy * (1 + trade_inertia_export_zy + trade_inertia_deviation_zy))

            import_lower_bound = (import_prev * (1 - trade_inertia_import - trade_inertia_deviation))
            import_lower_bound_zy = (import_prev_zy * (1 - trade_inertia_import_zy - trade_inertia_deviation_zy))

            import_upper_bound = (import_prev * (1 + trade_inertia_import + trade_inertia_deviation))
            import_upper_bound_zy = (import_prev_zy * (1 + trade_inertia_import_zy + trade_inertia_deviation_zy))

            export_lower_bound = pd.concat([export_lower_bound, export_lower_bound_zy], axis=0).reset_index(drop=True)
            export_upper_bound = pd.concat([export_upper_bound, export_upper_bound_zy], axis=0).reset_index(drop=True)
            import_lower_bound = pd.concat([import_lower_bound, import_lower_bound_zy], axis=0).reset_index(drop=True)
            import_upper_bound = pd.concat([import_upper_bound, import_upper_bound_zy], axis=0).reset_index(drop=True)

        else:

            paper_demand_prev = pd.concat([
                pd.DataFrame(self.Data.Demand.data_aligned[Domains.Demand.region_code]),
                pd.DataFrame(self.Data.Demand.data_aligned[Domains.Demand.commodity_code]),
                pd.DataFrame(self.Data.Demand.data_aligned[Domains.Demand.quantity])], axis=1)

            paper_demand_prev = paper_demand_prev.loc[paper_demand_prev[Domains.Demand.commodity_code] > 90]  # ToDo: Hard Code change to list with all paperproducts in defines
            paper_demand_prev = paper_demand_prev.reset_index(drop=True)

            recycling_upper_bound = pd.DataFrame(self.Data.RecyclingS.data_aligned[Domains.RecyclingS.recov_ubs])
            recycled_quantity_supply = pd.concat([paper_demand_prev, recycling_upper_bound], axis=1)
            recycled_quantity_supply["recycled_quantity"] = (recycled_quantity_supply[Domains.Demand.quantity]
                                                             * recycled_quantity_supply[Domains.RecyclingS.recov_ubs])

            wastepaper_supply_upper_bound = (
                recycled_quantity_supply.groupby(Domains.Demand.region_code)["recycled_quantity"].sum() # TODO Hard code (future work)
                                             ).reset_index()
            wastepaper_supply_upper_bound[Domains.Supply.commodity_code] = 90

            supply_upper_bound = self.Data.Supply.data_aligned.merge(
                wastepaper_supply_upper_bound,
                left_on=[Domains.Supply.commodity_code, Domains.Supply.region_code],
                right_on=[Domains.Supply.commodity_code, Domains.Supply.region_code],
                how="left").fillna(0)

            supply_upper_bound[Domains.Supply.upper_bound] = (supply_upper_bound[Domains.Supply.upper_bound] +
                                                              supply_upper_bound["recycled_quantity"])  # TODO Hard code (future work)
            supply_upper_bound.loc[supply_upper_bound[
                    Domains.Supply.upper_bound] == 0, Domains.Supply.upper_bound] = Constants.BOUND_OMITTED_VALUE.value

            # if dynamization_activated:
            #     supply_upper_bound = (supply_upper_bound[Domains.Supply.upper_bound] *
            #                           (1 + supply_upper_bound["growth_rate_upper_bound"]))
            # else:
            supply_upper_bound = supply_upper_bound[Domains.Supply.upper_bound]

            zy_region = len(self.Data.data_aligned) - len(self.Data.Commodities.data)
            other_regions = len(self.Data.data_aligned) - len(self.Data.Commodities.data)

            trade_inertia_export = self.Data.TransportationExport.data_aligned[
                                       Domains.TransportationExport.trade_inertia_bounds][:other_regions]
            trade_inertia_import = self.Data.TransportationImport.data_aligned[
                                       Domains.TransportationImport.trade_inertia_bounds][:other_regions]
            trade_inertia_export_zy = self.Data.TransportationExport.data_aligned[
                                          Domains.TransportationExport.trade_inertia_bounds][zy_region:]
            trade_inertia_import_zy = self.Data.TransportationImport.data_aligned[
                                          Domains.TransportationImport.trade_inertia_bounds][zy_region:]

            export_prev = self.Data.TransportationExport.data_aligned[Domains.TransportationExport.quantity][
                          :other_regions]
            import_prev = self.Data.TransportationImport.data_aligned[Domains.TransportationImport.quantity][
                          :other_regions]
            export_prev_zy = self.Data.TransportationExport.data_aligned[Domains.TransportationExport.quantity][
                             zy_region:]
            import_prev_zy = self.Data.TransportationImport.data_aligned[Domains.TransportationImport.quantity][
                             zy_region:]

            trade_inertia_deviation = Constants.TRADE_INERTIA_DEVIATION.value
            trade_inertia_deviation_zy = Constants.TRADE_INERTIA_DEVIATION_ZY.value

            export_lower_bound = (
                    export_prev * (1 - trade_inertia_export - trade_inertia_deviation) ** self.period_length)
            export_lower_bound_zy = (
                    export_prev_zy * (1 - trade_inertia_export_zy - trade_inertia_deviation_zy) ** self.period_length)

            export_upper_bound = (
                    export_prev * (1 + trade_inertia_export + trade_inertia_deviation) ** self.period_length)
            export_upper_bound_zy = (
                    export_prev_zy * (1 + trade_inertia_export_zy + trade_inertia_deviation) ** self.period_length)

            import_lower_bound = (
                    import_prev * (1 - trade_inertia_import - trade_inertia_deviation) ** self.period_length)
            import_lower_bound_zy = (
                    import_prev_zy * (1 - trade_inertia_import_zy - trade_inertia_deviation_zy) ** self.period_length)

            import_upper_bound = (
                    import_prev * (1 + trade_inertia_import + trade_inertia_deviation) ** self.period_length)
            import_upper_bound_zy = (
                    import_prev_zy * (1 + trade_inertia_import_zy + trade_inertia_deviation_zy) ** self.period_length)

            export_lower_bound = pd.concat([export_lower_bound, export_lower_bound_zy], axis=0).reset_index(drop=True)
            export_upper_bound = pd.concat([export_upper_bound, export_upper_bound_zy], axis=0).reset_index(drop=True)
            import_lower_bound = pd.concat([import_lower_bound, import_lower_bound_zy], axis=0).reset_index(drop=True)
            import_upper_bound = pd.concat([import_upper_bound, import_upper_bound_zy], axis=0).reset_index(drop=True)

            regions_no_stock = self.Data.Forest.data_aligned[
                self.Data.Forest.data_aligned["ForStock"] <= 1]["RegionCode"].unique()

            mask_no_stock = self.Data.data_aligned[(
                [x in regions_no_stock for x in self.Data.data_aligned["RegionCode"]])].index

            export_lower_bound.loc[mask_no_stock] = 0

        complete_lower_bounds = np.array([
            pd.concat([demand_lower_bound, export_lower_bound, import_lower_bound, manu_lower_bound,
                       supply_lower_bound]).reset_index(drop=True).clip(lower=0)
        ])
        complete_upper_bounds = np.array([
            pd.concat([demand_upper_bound, export_upper_bound, import_upper_bound, manu_upper_bound,
                       supply_upper_bound]).reset_index(drop=True).clip(lower=0)
        ])
        self.Data.OptimizationHelpers.data["lower_bound"] = pd.DataFrame(complete_lower_bounds.T)
        self.Data.OptimizationHelpers.data["upper_bound"] = pd.DataFrame(complete_upper_bounds.T)
        self.Logger.info(f"Setting bounds finished.")
        return complete_lower_bounds, complete_upper_bounds

    def vectorize_domains(self):
        """
        Transform required data for the optimization into vectors and save them into a new domain optim_helpers in
        following order: Demand, TransportExport, TransportImport, ManufactureCost, Supply. The order is of importance
        for all following optimization steps
        """
        self.Logger.info(f"Domains vectorization.")
        region_vector = pd.DataFrame()
        commodity_vector = pd.DataFrame()
        domain_vector = pd.DataFrame()
        price_vector = pd.DataFrame()
        quantity_vector = pd.DataFrame()
        elasticity_price_vector = pd.DataFrame()
        slope_vector = pd.DataFrame()
        intercept_vector = pd.DataFrame()
        period_vector = pd.DataFrame()
        year_vector = pd.DataFrame()
        shadow_price_vector = pd.DataFrame()

        for (domain_name, price, quantity, elasticity_price, slope,
             intercept) in DomainIterator.get_info_vectorize(DomainIterator.OPTIMIZATION_DOMAINS):
            region_vector = pd.concat([region_vector,
                                       self.Data.data_aligned[Domains.Regions.region_code]]).reset_index(drop=True)
            commodity_vector = pd.concat([commodity_vector,
                                          self.Data.data_aligned[Domains.Commodities.commodity_code]]).reset_index(
                drop=True)
            domain_vector = pd.concat([domain_vector,
                                       pd.concat(
                                           [pd.DataFrame([domain_name])]
                                           * self.Data[domain_name].data_aligned.shape[0])]).reset_index(drop=True)
            price_vector = pd.concat([price_vector, self.Data[domain_name].data_aligned[price]]).reset_index(drop=True)
            quantity_vector = pd.concat([quantity_vector, self.Data[domain_name].data_aligned[
                quantity]]).reset_index(drop=True)
            elasticity_price_vector = pd.concat([elasticity_price_vector, self.Data[domain_name].data_aligned[
                elasticity_price]]).reset_index(drop=True)
            slope_vector = pd.concat([slope_vector, self.Data[domain_name].data_aligned[slope]]).reset_index(drop=True)
            intercept_vector = pd.concat([intercept_vector, self.Data[domain_name].data_aligned[
                intercept]]).reset_index(drop=True)
            period_vector = pd.concat([
                period_vector, pd.concat([pd.DataFrame([self.present_period])] * self.Data[
                    domain_name].data_aligned.shape[0])]).reset_index(drop=True)
            year_vector = pd.concat([
                year_vector, pd.concat([pd.DataFrame([self.actual_year])] * self.Data[
                    domain_name].data_aligned.shape[0])]).reset_index(drop=True)
            shadow_price_vector = pd.concat([
                shadow_price_vector, pd.concat([pd.DataFrame([0])] * self.Data[
                    domain_name].data_aligned.shape[0])]).reset_index(drop=True)

        optim_helpers = DataContainer("optim_helpers")
        optim_helpers.data = pd.concat([region_vector.rename(columns={0: Domains.Regions.region_code}),
                                        commodity_vector.rename(columns={0: Domains.Commodities.commodity_code}),
                                        domain_vector.rename(columns={0: VarNames.DOMAIN_COLNAME.value}),
                                        price_vector.rename(columns={0: VarNames.PRICE_COLNAME.value}),
                                        quantity_vector.rename(columns={0: VarNames.QUANTITY_COLNAME.value}),
                                        elasticity_price_vector.rename(columns={0: VarNames.ELASTICITY_COLNAME.value}),
                                        slope_vector.rename(columns={0: VarNames.SLOPE_COLNAME.value}),
                                        intercept_vector.rename(columns={0: VarNames.INTERCEPT_COLNAME.value}),
                                        period_vector.rename(columns={0: VarNames.PERIOD_COLNAME.value}),
                                        year_vector.rename(columns={0: VarNames.YEAR_COLNAME.value}),
                                        shadow_price_vector.rename(columns={0: VarNames.SHADOW_PRICE_COLNAME.value})],
                                       axis=1).reset_index(drop=True)

        if self.present_period == 0:
            self.Data.set_attribute("OptimizationHelpers", optim_helpers)
        else:
            self.Data["OptimizationHelpers"].data = optim_helpers.data

    def optimization_setup(self):
        """
        Defines welfare optimization.
        Define optimization parameters (optimized quantities and manufacture costs).
        :return: optimization parameters (opt_quantity), corrected slopes and intercepts
        and domain lengths (DOMAIN_LEN, ALL_DOMAIN_LEN)
        """
        slope_col_name = VarNames.SLOPE_COLNAME.value
        intercept_col_name = VarNames.INTERCEPT_COLNAME.value
        DOMAIN_LEN = len(self.Data.data_aligned)
        ALL_DOMAINS_LEN = len(self.Data.OptimizationHelpers.data)
        opt_quantity = cp.Variable((ALL_DOMAINS_LEN, 1), nonneg=True)

        curvature_correction = pd.DataFrame(np.concatenate([np.ones((DOMAIN_LEN, 1)),
                                                            np.ones((DOMAIN_LEN, 1)),
                                                            - np.ones((DOMAIN_LEN, 1)),
                                                            - np.ones((DOMAIN_LEN, 1)),
                                                            - np.ones((DOMAIN_LEN, 1))]))

        slope = np.array(self.Data.OptimizationHelpers.data[slope_col_name] * curvature_correction[0]
                         ).reshape(ALL_DOMAINS_LEN, 1)
        intercept = np.array(self.Data.OptimizationHelpers.data[intercept_col_name] * curvature_correction[0]
                             ).reshape(ALL_DOMAINS_LEN, 1)
        self.Logger.info(f"Optimization setup done.")
        return DOMAIN_LEN, ALL_DOMAINS_LEN, opt_quantity, slope, intercept

    def constraint_trade(self, constraints: list, constraints_position: dict, constraint_counter: list,
                         opt_quantity: cp.Variable, opt_lbs: np.array, opt_ubs: np.array, DOMAIN_LEN: int):
        """
        Defines optimization constraint for the minimal and maximal traded quantities (upper and lower bound) for each
        country in compliance with trade related exogenous parameters. Used for bounding trade in base periods.
        Needed because in base period trade is fixed to bounds.
        :param constraints: list where constraints are saved for the optimization
        :param constraints_position: dict where information (constraint name and position) are saved for the result
         extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: optimized quantity
        :param opt_lbs: optimization lower bounds
        :param opt_ubs: optimization upper bounds
        :param DOMAIN_LEN: aligned length of optimized domains
        """
        trade_lower_bnd_var = VarNames.TRADE_LOWER_BOUND.value
        trade_upper_bnd_var = VarNames.TRADE_UPPER_BOUND.value

        constraints += [opt_quantity[DOMAIN_LEN: 3 * DOMAIN_LEN] >= opt_lbs[DOMAIN_LEN: 3 * DOMAIN_LEN]]
        constraint_get_position(constraints_position, trade_lower_bnd_var, constraints, constraint_counter)
        constraints += [opt_quantity[DOMAIN_LEN: 3 * DOMAIN_LEN] <= opt_ubs[DOMAIN_LEN: 3 * DOMAIN_LEN]]
        constraint_get_position(constraints_position, trade_upper_bnd_var, constraints, constraint_counter)
        self.Logger.info(f"Constraint trade bounds done.")

    def constraint_trade_new(self, constraints: list, constraints_position: dict, constraint_counter: list,
                             opt_quantity: cp.Variable, opt_lbs: np.array, opt_ubs: np.array,
                             DOMAIN_LEN: int, ALL_DOMAINS_LEN: int):
        """
        Calculates delta_trade for the upper and lower bound for traded quantities. Delta_trade represents the
        difference between the optimized trade quantity and the upper and lower bound for traded quantities, which is
        minimized in the objective function, allowing therefore more flexibility to avoid infeasibility issues due to
        strict trade bounds. This approach is needed for stable world price calculations. Used for bounding trade in 
        following periods. Needed because in follwoing period trade is allowed to trespass the given bounds. Deviation
        from bounds are sanctioned by penalty.
        :param constraints: list of constraints in which specific constraint is saved
        :param constraints_position: dict where information (constraint name and position) are saved for the result
        extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: independent variable
        :param opt_lbs: lower bounds for trade optimization
        :param opt_ubs: upper bounds for trade optimization
        :param DOMAIN_LEN: lenght of one domain vector
        :returns np.array: deviation between optimized trade value and bounds; deviation between optimized trade value 
        and previous trade value
        """
        period_col_name = VarNames.PERIOD_COLNAME.value
        quantity_col_name = VarNames.QUANTITY_COLNAME.value
        domain_col_name = VarNames.DOMAIN_COLNAME.value
        trade_lower_bnd_var = VarNames.TRADE_LOWER_BOUND.value
        trade_upper_bnd_var = VarNames.TRADE_UPPER_BOUND.value
        zy_region_var = VarNames.ZY_REGION.value

        zero_vector = pd.DataFrame(np.zeros(DOMAIN_LEN))
        one_vector = pd.DataFrame(np.ones(DOMAIN_LEN))
        trade_vector = np.array(pd.concat([zero_vector, one_vector, one_vector, zero_vector, zero_vector],
                                          axis=0).reset_index(drop=True)).reshape(ALL_DOMAINS_LEN, 1)
        # Deviation from upper and lower bound
        delta_trade_upper_bound = cp.multiply((opt_quantity - opt_ubs), trade_vector)
        delta_trade_lower_bound = cp.multiply((opt_lbs - opt_quantity), trade_vector)

        # Deviation from trade in previous period (increases and decreases from prev trade)
        #TODO activate by user input
        prev_trade = self.Data.OptimizationHelpers.data_periods[
            self.Data.OptimizationHelpers.data_periods[period_col_name] == self.present_period - 1][quantity_col_name]
        prev_trade = np.array(prev_trade).reshape(ALL_DOMAINS_LEN, 1)
        delta_prev_trade_increase = cp.multiply((opt_quantity - prev_trade), trade_vector)
        delta_prev_trade_decrease = cp.multiply((prev_trade - opt_quantity), trade_vector)

        # No flexible trade bounds for regions without trade
        trade_mask = self.Data.OptimizationHelpers.data[
            ([x in [str(Domains.TransportationExport),
                    str(Domains.TransportationImport)] for x in self.Data.OptimizationHelpers.data[domain_col_name]]) &
            (self.Data.OptimizationHelpers.data[quantity_col_name] <= Constants.NON_ZERO_PARAMETER.value) &
            (self.Data.OptimizationHelpers.data[Domains.Supply.region_code] != zy_region_var)].index

        constraints += [opt_quantity[trade_mask] >= opt_lbs[trade_mask]]
        constraint_get_position(constraints_position, trade_lower_bnd_var, constraints, constraint_counter)
        constraints += [opt_quantity[trade_mask] <= opt_ubs[trade_mask]]
        constraint_get_position(constraints_position, trade_upper_bnd_var, constraints, constraint_counter)

        self.Logger.info(f"Constraint trade bounds done. Delta trade for lower and upper bounds computed.")
        return delta_trade_upper_bound, delta_trade_lower_bound, delta_prev_trade_increase, delta_prev_trade_decrease

    def constraint_supply(self, constraints: list, constraints_position: dict, constraint_counter: list,
                          opt_quantity: cp.Variable, opt_ubs: np.array, DOMAIN_LEN: int):
        """
        Defines optimization constraint for maximal supplied quantity (upper bound) for each country in case that it 
        is exogenously prescript in input da-ta with the supply related exogenous parameters.
        :param constraints: list of constraints in which specific constraint is saved
        :param constraints_position: dict where information (constraint name and position) are saved for the result
        extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: independent variable
        :param opt_ubs: upper bounds for supply optimization
        :param DOMAIN_LEN: lenght of one domain vector
        """
        supply_upper_bnd_var = VarNames.SUPPLY_UPPER_BOUND.value
        constraints += [opt_quantity[4 * DOMAIN_LEN: 5 * DOMAIN_LEN] <= opt_ubs[4 * DOMAIN_LEN: 5 * DOMAIN_LEN]]
        constraint_get_position(constraints_position, supply_upper_bnd_var, constraints, constraint_counter)
        self.Logger.info(f"Constraint upper bound for supply done.")

    def constraint_manufacture(self, constraints: list, constraints_position: dict, constraint_counter: list,
                               opt_quantity: cp.Variable, opt_ubs: np.array, DOMAIN_LEN: int):
        """
        Defines optimization constraint for maximal manufactured quantity (upper bound). Main purpose of the constraint 
        to prohibit production for non-producing regions in input file. Producing regions are allowed to produce  
        complying with the material balance constraint due to arbitrary high con-straints (quantity * 10000). Remove 
        constraint manufacture to allow origi-nally non-producing regions to build up a production!
        :param constraints: list of constraints in which specific constraint is saved
        :param constraints_position: dict where information (constraint name and position) are saved for the result
        extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: independent variable
        :param opt_ubs: upper bounds for supply optimization
        :param DOMAIN_LEN: lenght of one domain vector
        """
        manu_upper_bnd_var = VarNames.MANU_UPPER_BOUND.value
        constraints += [opt_quantity[3 * DOMAIN_LEN: 4 * DOMAIN_LEN] <= opt_ubs[3 * DOMAIN_LEN: 4 * DOMAIN_LEN]]
        constraint_get_position(constraints_position, manu_upper_bnd_var, constraints, constraint_counter)
        self.Logger.info(f"Constraint upper bound for manufacture done.")

    def constraint_demand(self, constraints: list, constraints_position: dict, constraint_counter: list,
                          opt_quantity: cp.Variable, opt_ubs: np.array, opt_lbs: np.array, DOMAIN_LEN: int):
        """
        Defines optimization constraint for demand for regions without stocks. Prohibit the demand for 
        countries without forest stock.
        :param constraints: list of constraints in which specific constraint is saved
        :param constraints_position: dict where information (constraint name and position) are saved for the result
        extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: independent variable
        :param opt_ubs: upper bounds for demand optimization
        :param opt_lbs: demand bounds for demand optimization
        :param DOMAIN_LEN: lenght of one domain vector
        """
        demand_lower_bnd_var = VarNames.DEMAND_LOWER_BOUND.value
        constraints += [opt_quantity[0: DOMAIN_LEN] >= opt_lbs[0: DOMAIN_LEN]]
        constraint_get_position(constraints_position, demand_lower_bnd_var, constraints, constraint_counter)
        self.Logger.info(f"Constraint lower bound for demand done.")

    def constraint_max_harvest(self, constraints: list, constraints_position: dict, constraint_counter: list,
                               opt_quantity: cp.Variable, DOMAIN_LEN: int):
        """
        Defines optimization constraint for the maximal harvestable wood quantity (upper bound) for each country
        in compliance with the available stock. The variable fraction_fuelwood is modified to capture fraction of all
        supplied wood from forest (1 for indround, 1 for othindround, fraction_fuelwood for fuelwood).
        :param constraints: list where constraints are saved for the optimization
        :param constraints_position: dict where information (constraint name and position) are saved for the result
        extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: independent variable
        :param DOMAIN_LEN: aligned length of optimized domains
        """
        max_harvest_var = VarNames.MAX_HARVEST.value
        for region in self.Data.Regions.data[Domains.Regions.region_code].iloc[:self.Data.Regions.df_length - 1]:
            #TODO could be implemented as a specific iterator (iterate over all regions with zy and all countries without zy)
            region_index = self.Data.data_aligned[self.Data.data_aligned[Domains.Regions.region_code] == region].index
            total_harvest = self.Data.Forest.data_aligned[Domains.Forest.ratio_inventory_drain].iloc[
                                region_index.min()] * cp.sum(
                cp.multiply(opt_quantity[4 * DOMAIN_LEN + region_index.min(): 4 * DOMAIN_LEN + region_index.max() + 1],
                            np.array(pd.DataFrame(self.Data.Forest.data_aligned[Domains.Forest.fraction_fuelwood].iloc[
                                                      region_index]))) / ConversionParameters.MIO_FACTOR.value)

            available_stock = self.Data.Forest.data_aligned[Domains.Forest.forest_stock].iloc[region_index.min()]

            constraints += [total_harvest <= available_stock]
        constraint_get_position(constraints_position, max_harvest_var, constraints, constraint_counter)
        self.Logger.info(f"Constraint maximum harvestable forest stock done.")

    def constraint_material_balance(self, constraints: list, constraints_position: dict, constraint_counter: list,
                                    opt_quantity: cp.Variable, DOMAIN_LEN: int):
        """
        Defines optimization constraint for the material balance for each country and each product group (raw_prod,
        interm_prod, fin_prod, fuelw and othindrnd). Choice for different types of material balances by user input:
        RC_specific_MB: region and commodity specific material balance (one constraint per product and country)
        RCG_specific_MB: region and commodity group specific material balance (raw, final and intermediate products 
        are grouped in one constraint for each country)
        optional_MB: #TODO check relevance
        C_specific_MB: Commodity group specific material balance (raw, final and intermediate products are grouped 
        in one constraint for all countries; default).
        From a mathematical point of view all MB are the same. Only for the optimization process these types are 
        relevant.
        :param constraints: list where constraints are saved for the optimization
        :param constraints_position: dict where information (constraint name and position) are saved for the result
         extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: unknown quantity value to optimize
        :param DOMAIN_LEN: aligned length of optimized domains
        """
        domain_col_name = VarNames.DOMAIN_COLNAME.value
        c_specific_mb_var = VarNames.C_SPECIFIC_MB.value
        rc_specific_mb_var = VarNames.RC_SPECIFIC_MB.value
        rcg_specific_mb_var = VarNames.RCG_SPECIFIC_MB.value
        optional_mb_var = VarNames.OPT_MB.value

        (raw_prod_vector, interm_prod_vector, fin_prod_vector, fuelw_vector, othindrnd_vector,
         raw_prod, interm_prod, fin_prod, fuelw, othindrnd
         ) = extract_product_groups(world_data=self.Data, commodity_data=self.Data.Commodities,
                                    region_data=self.Data.Regions, all_regions=False, only_commodity_codes=False)
        material_balance_var = VarNames.MATERIAL_BALANCE.value
        if (self.UserOptions.material_balance == rc_specific_mb_var or
                self.UserOptions.material_balance == rcg_specific_mb_var or
                self.UserOptions.material_balance == optional_mb_var):

            for region in self.Data.Regions.data[Domains.Regions.region_code].iloc[:self.Data.Regions.df_length - 1]:

                region_index_max = max(self.Data.data_aligned[self.Data.data_aligned[
                                                                  Domains.Regions.region_code] == region].index) + 1
                region_index_min = min(self.Data.data_aligned[self.Data.data_aligned[
                                                                  Domains.Regions.region_code] == region].index)
                io_matrix_region = np.array(pd.DataFrame(self.Data.ManufactureCoefficients.ioMatrix).iloc[
                                            region_index_min:region_index_max, region_index_min:region_index_max])

                demand_opt_region = opt_quantity[region_index_min:region_index_max]
                export_opt_region = opt_quantity[DOMAIN_LEN + region_index_min: DOMAIN_LEN + region_index_max]
                import_opt_region = opt_quantity[2 * DOMAIN_LEN + region_index_min: 2 * DOMAIN_LEN + region_index_max]
                manuD_opt_region = opt_quantity[3 * DOMAIN_LEN + region_index_min: 3 * DOMAIN_LEN + region_index_max]
                supply_opt_region = opt_quantity[4 * DOMAIN_LEN + region_index_min: 4 * DOMAIN_LEN + region_index_max]
                manuS_opt_quantity = self.Data.ManufactureCoefficients.ioMatrix @ opt_quantity[
                                                                                  3 * DOMAIN_LEN: 4 * DOMAIN_LEN]

                optimization_data = self.Data.OptimizationHelpers.data[
                    [Domains.Regions.region_code, domain_col_name, Domains.Commodities.commodity_code]]

                # raw materials
                raw_prod_supply_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.Supply.domain) &
                    ([x in raw_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                raw_prod_import_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.TransportationImport.domain) &
                    ([x in raw_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                raw_prod_export_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.TransportationExport.domain) &
                    ([x in raw_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                raw_prod_demand_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.Demand.domain) &
                    ([x in raw_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                # Intermediate products
                interm_prod_import_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.TransportationImport.domain) &
                    ([x in interm_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                interm_prod_export_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.TransportationExport.domain) &
                    ([x in interm_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                interm_prod_manu_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.ManufactureCost.domain) &
                    ([x in interm_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                interm_prod_demand_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.Demand.domain) &
                    ([x in interm_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                # final products
                fin_prod_import_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.TransportationImport.domain) &
                    ([x in fin_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                fin_prod_export_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.TransportationExport.domain) &
                    ([x in fin_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                fin_prod_manu_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.ManufactureCost.domain) &
                    ([x in fin_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                fin_prod_demand_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.Demand.domain) &
                    ([x in fin_prod for x in optimization_data[Domains.Commodities.commodity_code]])].index

                # fuelwood
                fuelw_supply_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.Supply.domain) &
                    (optimization_data[Domains.Commodities.commodity_code] == fuelw)].index

                fuelw_import_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.TransportationImport.domain) &
                    (optimization_data[Domains.Commodities.commodity_code] == fuelw)].index

                fuelw_export_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.TransportationExport.domain) &
                    (optimization_data[Domains.Commodities.commodity_code] == fuelw)].index

                fuelw_demand_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.Demand.domain) &
                    (optimization_data[Domains.Commodities.commodity_code] == fuelw)].index

                # other industrial roundwood
                othindrnd_supply_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.Supply.domain) &
                    (optimization_data[Domains.Commodities.commodity_code] == othindrnd)].index

                othindrnd_demand_index_region = optimization_data[
                    (optimization_data[Domains.Regions.region_code] == region) &
                    (optimization_data[domain_col_name] == self.Data.Demand.domain) &
                    (optimization_data[Domains.Commodities.commodity_code] == othindrnd)].index

                #TODO check if te following passages could be split in single functions for each type of MB.
                if self.UserOptions.material_balance == rc_specific_mb_var:
                    """
                    Region and commodity specific material balance: one constraint for each product in each region.
                    constraint number = len(commodities) * len(regions)
                    Not used for validation due to the long processing time of the large constraint number
                    """

                    for commodity in self.Data.Commodities.data[Domains.Commodities.commodity_code]:
                        help_vector = np.array(self.Data.Commodities.data[Domains.Commodities.commodity_code]
                                               ).reshape([len(self.Data.Commodities.data), 1])
                        help_vector = np.where(help_vector == commodity, 1, 0)
                        region_vector = self.Data.data_aligned[region_index_min: region_index_max]
                        commodity_index = region_vector[
                            region_vector[Domains.Commodities.commodity_code] == commodity].index

                        demand_opt_commodity = opt_quantity[commodity_index]
                        export_opt_commodity = opt_quantity[DOMAIN_LEN + commodity_index]
                        import_opt_commodity = opt_quantity[2 * DOMAIN_LEN + commodity_index]
                        manu_opt_commodity = opt_quantity[3 * DOMAIN_LEN + commodity_index]
                        supply_opt_commodity = opt_quantity[4 * DOMAIN_LEN + commodity_index]

                        # raw materials
                        if [x in raw_prod for x in list([commodity])][0]:
                            constraints += [import_opt_commodity + supply_opt_commodity ==
                                            cp.sum(cp.multiply(io_matrix_region @ manuD_opt_region, help_vector))
                                            + export_opt_commodity
                                            ]
                        # fuelwood
                        if commodity == fuelw:
                            constraints += [import_opt_commodity + supply_opt_commodity ==
                                            demand_opt_commodity + export_opt_commodity
                                            ]
                        # other_industrial_wood
                        if commodity == othindrnd:
                            constraints += [supply_opt_commodity == demand_opt_commodity
                                            ]
                        # intermediate_products
                        if [x in interm_prod for x in list([commodity])][0]:
                            constraints += [import_opt_commodity + manu_opt_commodity ==
                                            cp.sum(cp.multiply(io_matrix_region @ manuD_opt_region, help_vector))
                                            + export_opt_commodity
                                            ]
                        # final products
                        if [x in fin_prod for x in list([commodity])][0]:
                            constraints += [import_opt_commodity
                                            + manu_opt_commodity ==
                                            demand_opt_commodity
                                            + export_opt_commodity
                                            ]

                if self.UserOptions.material_balance == rcg_specific_mb_var:
                    """
                    Region and commodity specific material balance: one constraint for each commodity group in each. 
                    region with helper vectors
                    constraint number: 5 commodity groups * len(regions)
                    Used for validation with calculated prices
                    """
                    # raw materials
                    constraints += [cp.multiply(import_opt_region, raw_prod_vector)
                                    + cp.multiply(supply_opt_region, raw_prod_vector) ==
                                    cp.multiply(io_matrix_region @ manuD_opt_region, raw_prod_vector)
                                    + cp.multiply(export_opt_region, raw_prod_vector)
                                    ]

                    # intermediate products
                    constraints += [cp.multiply(import_opt_region, interm_prod_vector)
                                    + cp.multiply(manuD_opt_region, interm_prod_vector) ==
                                    cp.multiply(io_matrix_region @ manuD_opt_region, interm_prod_vector)
                                    + cp.multiply(export_opt_region, interm_prod_vector)
                                    ]

                    # final products
                    constraints += [cp.multiply(import_opt_region, fin_prod_vector)
                                    + cp.multiply(manuD_opt_region, fin_prod_vector) ==
                                    cp.multiply(demand_opt_region, fin_prod_vector)
                                    + cp.multiply(export_opt_region, fin_prod_vector)
                                    ]

                    # fuelwood
                    constraints += [cp.multiply(import_opt_region, fuelw_vector)
                                    + cp.multiply(supply_opt_region, fuelw_vector) ==
                                    cp.multiply(demand_opt_region, fuelw_vector)
                                    + cp.multiply(export_opt_region, fuelw_vector)
                                    ]

                    # other industrial roundwood
                    constraints += [cp.multiply(supply_opt_region, othindrnd_vector) ==
                                    cp.multiply(demand_opt_region, othindrnd_vector)
                                    ]

                if self.UserOptions.material_balance == optional_mb_var:
                    """
                    Optional material balance: commodity group and region specific material balance with indexes instead 
                    of help vectors as RCG_specific_MB.
                    constraint number: 5 commodity groups * len(regions)
                    Not used for validation as C_specific_MB yield comparable shadow prices with higher processing speed 
                    """
                    # raw materials new version
                    constraints += [opt_quantity[raw_prod_import_index_region]
                                    + opt_quantity[raw_prod_supply_index_region] ==
                                    manuS_opt_quantity[raw_prod_demand_index_region]
                                    + opt_quantity[raw_prod_export_index_region]
                                    ]

                    # intermediate products new version
                    constraints += [opt_quantity[interm_prod_import_index_region]
                                    + opt_quantity[interm_prod_manu_index_region] ==
                                    manuS_opt_quantity[interm_prod_demand_index_region]
                                    + opt_quantity[interm_prod_export_index_region]
                                    ]

                    # final products new version
                    constraints += [opt_quantity[fin_prod_import_index_region]
                                    + opt_quantity[fin_prod_manu_index_region] ==
                                    opt_quantity[fin_prod_demand_index_region]
                                    + opt_quantity[fin_prod_export_index_region]
                                    ]

                    # fuelwood new version
                    constraints += [opt_quantity[fuelw_import_index_region]
                                    + opt_quantity[fuelw_supply_index_region] ==
                                    opt_quantity[fuelw_demand_index_region]
                                    + opt_quantity[fuelw_export_index_region]
                                    ]

                    # other industrial roundwood new version
                    constraints += [opt_quantity[othindrnd_supply_index_region] ==
                                    opt_quantity[othindrnd_demand_index_region]
                                    ]

        if self.UserOptions.material_balance == c_specific_mb_var:
            """
            Commodity specific material balance: one constraint for each commodity over all regions.
            constraint number: len(commodities)
            Used for validation of shadow prices
            """
            # Define io_matrix and manu_opt

            io_matrix = self.Data.ManufactureCoefficients.ioMatrixshort
            manu_opt = opt_quantity[3 * DOMAIN_LEN: 4 * DOMAIN_LEN - len(self.Data.Commodities.data)]
            help_pd = self.Data.data_aligned[Domains.Commodities.commodity_code].iloc[
                      :(len(self.Data.data_aligned) - len(self.Data.Commodities.data))]

            for commodity in self.Data.Commodities.data[Domains.Commodities.commodity_code]:
                commodity_index = help_pd[help_pd == commodity].index

                demand_opt_commodity = opt_quantity[commodity_index]
                export_opt_commodity = opt_quantity[DOMAIN_LEN + commodity_index]
                import_opt_commodity = opt_quantity[2 * DOMAIN_LEN + commodity_index]
                manuD_opt_commodity = opt_quantity[3 * DOMAIN_LEN + commodity_index]
                supply_opt_commodity = opt_quantity[4 * DOMAIN_LEN + commodity_index]
                manuS_opt_commodity = (io_matrix @ manu_opt)[commodity_index]

                if [x in raw_prod for x in list([commodity])][0]:
                    constraints += [import_opt_commodity + supply_opt_commodity ==
                                    manuS_opt_commodity + export_opt_commodity
                                    ]
                # fuelwood
                if commodity == fuelw:
                    constraints += [import_opt_commodity + supply_opt_commodity ==
                                    demand_opt_commodity + export_opt_commodity
                                    ]
                # other_industrial_wood
                if commodity == othindrnd:
                    constraints += [supply_opt_commodity == demand_opt_commodity
                                    ]
                # intermediate_products
                if [x in interm_prod for x in list([commodity])][0]:
                    constraints += [import_opt_commodity + manuD_opt_commodity ==
                                    manuS_opt_commodity + export_opt_commodity
                                    ]
                # final products
                if [x in fin_prod for x in list([commodity])][0]:
                    constraints += [import_opt_commodity + manuD_opt_commodity ==
                                    demand_opt_commodity + export_opt_commodity
                                    ]

        constraint_get_position(constraints_position, material_balance_var, constraints, constraint_counter)
        self.Logger.info(f"Material balance constraint for all regions done.")

    def constraint_material_balance_zy(self, constraints: list, constraints_position: dict, constraint_counter: list,
                                       opt_quantity: cp.Variable, DOMAIN_LEN: int):
        """
        Defines the combined optimization constraint for material balance for zy-region for each product.
        1. constraint balances out surpluses of demand and supply of all countries with exports and imports from zy.
        (Combined constraints for imports and exports in zy region.)
        [zy-region-import + sum(demand of all countries) == zy-region-export + sum(supply of all countries)].
        2. constraint limits exports and imports of zy to trade volumes from the calibration for each product.
        [zy-region export from calibration == optimized zy-region export]
        [zy-region import from calibration == optimized zy-region import]
        Two seperate constraints for imports and exports in zy region used for extracting shadow prices for the
        world market.
        :param constraints: list where constraints are saved for the optimization
        :param constraints_position: dict where information (constraint name and position) are saved for the result
        extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: independent variable
        :param DOMAIN_LEN: aligned length of optimized domains
        """
        zy_material_balance_var = VarNames.MATERIAL_BALANCE_ZY.value
        zy_import_var = VarNames.ZY_IMPORT.value
        zy_export_var = VarNames.ZY_EXPORT.value
        zy_region_var = VarNames.ZY_REGION.value
        zy_region = self.Data.data_aligned[self.Data.data_aligned[Domains.Regions.region_code] == zy_region_var]
        other_regions = self.Data.data_aligned[self.Data.data_aligned[Domains.Regions.region_code] != zy_region_var]
        zy_import = self.Data.TransportationImport.data_aligned[Domains.TransportationImport.quantity].loc[
            zy_region.index]
        zy_export = self.Data.TransportationExport.data_aligned[Domains.TransportationExport.quantity].loc[
            zy_region.index]

        for commodity in self.Data.Commodities.data[Domains.Commodities.commodity_code]:
            commodity_regions_index = other_regions[other_regions[
                                                        Domains.Commodities.commodity_code] == commodity].index
            commodity_zy_index = zy_region[zy_region[Domains.Commodities.commodity_code] == commodity].index

            exports_test = sum(self.Data.TransportationExport.data_aligned[Domains.TransportationExport.quantity].loc[
                                   commodity_regions_index])
            imports_test = sum(self.Data.TransportationImport.data_aligned[Domains.TransportationImport.quantity].loc[
                                   commodity_regions_index])
            zy_material_balance = float(exports_test + zy_export[commodity_zy_index] -
                                        imports_test - zy_import[commodity_zy_index])
            if self.UserOptions.verbose_calculation_logger:
                self.Logger.info(f"ZY-material balance for {commodity}: {zy_material_balance}")

            constraints += [(cp.sum(opt_quantity[2 * DOMAIN_LEN + commodity_regions_index, 0]) +
                             opt_quantity[2 * DOMAIN_LEN + commodity_zy_index]) ==
                            (cp.sum(opt_quantity[DOMAIN_LEN + commodity_regions_index, 0]) +
                             opt_quantity[DOMAIN_LEN + commodity_zy_index])
                            ]

        constraint_get_position(constraints_position, zy_material_balance_var, constraints, constraint_counter)

        for commodity in self.Data.Commodities.data[Domains.Commodities.commodity_code]:
            commodity_zy_index = zy_region[zy_region[Domains.Commodities.commodity_code] == commodity].index

            constraints += [opt_quantity[DOMAIN_LEN + commodity_zy_index] == zy_export[commodity_zy_index]]

        constraint_get_position(constraints_position, zy_export_var, constraints, constraint_counter)

        for commodity in self.Data.Commodities.data[Domains.Commodities.commodity_code]:
            commodity_zy_index = zy_region[zy_region[Domains.Commodities.commodity_code] == commodity].index

            constraints += [opt_quantity[2 * DOMAIN_LEN + commodity_zy_index] == zy_import[commodity_zy_index]]

        constraint_get_position(constraints_position, zy_import_var, constraints, constraint_counter)

        self.Logger.info(f"Material balance constraints for zy-region done.")

    def constraint_global_material_balance(self, constraints: list, constraints_position: dict,
                                           constraint_counter: list, opt_quantity: cp.Variable, DOMAIN_LEN: int):
        """
        Defines optimization constraints for a global material balance over all regions. zy-region is used to balance
        deficits and surplus in exports and imports globally.
        :param constraints: list where constraints are saved for the optimization
        :param constraints_position: dict where information (constraint name and position) are saved for the result
        extraction
        :param constraint_counter: counter tracking of the number of constraints in constraints_position
        :param opt_quantity: unknown quantity value to optimize
        :param DOMAIN_LEN: aligned length of optimized domains
        """

        (raw_prod_vector, interm_prod_vector, fin_prod_vector, fuelw_vector, othindrnd_vector,
         raw_prod, interm_prod, fin_prod, fuelw, othindrnd
         ) = extract_product_groups(world_data=self.Data, commodity_data=self.Data.Commodities,
                                    region_data=self.Data.Regions, all_regions=True, only_commodity_codes=False)

        raw_prod_vector_short = raw_prod_vector[:self.Data.Commodities.df_length]
        interm_prod_vector_short = interm_prod_vector[:self.Data.Commodities.df_length]
        fin_prod_vector_short = fin_prod_vector[:self.Data.Commodities.df_length]
        fuelw_vector_short = fuelw_vector[:self.Data.Commodities.df_length]

        io_matrix = self.Data.ManufactureCoefficients.ioMatrixshort
        zy_import = opt_quantity[2 * DOMAIN_LEN - self.Data.Commodities.df_length: 2 * DOMAIN_LEN]
        zy_export = opt_quantity[DOMAIN_LEN - self.Data.Commodities.df_length: DOMAIN_LEN]
        opt_demand = opt_quantity[0: DOMAIN_LEN - self.Data.Commodities.df_length]
        opt_export = opt_quantity[DOMAIN_LEN: 2 * DOMAIN_LEN - self.Data.Commodities.df_length]
        opt_import = opt_quantity[2 * DOMAIN_LEN: 3 * DOMAIN_LEN - self.Data.Commodities.df_length]
        opt_manu = opt_quantity[3 * DOMAIN_LEN: 4 * DOMAIN_LEN - self.Data.Commodities.df_length]
        opt_supply = opt_quantity[4 * DOMAIN_LEN: 5 * DOMAIN_LEN - self.Data.Commodities.df_length]

        constraints += [cp.sum(cp.multiply(opt_import, raw_prod_vector))
                        + cp.sum(cp.multiply(zy_import, raw_prod_vector_short))
                        + cp.sum(cp.multiply(opt_supply, raw_prod_vector)) ==
                        cp.sum(cp.multiply(io_matrix @ opt_manu, raw_prod_vector))
                        + cp.sum(cp.multiply(opt_export, raw_prod_vector))
                        + cp.sum(cp.multiply(zy_export, raw_prod_vector_short))
                        ]

        constraints += [cp.sum(cp.multiply(opt_import, interm_prod_vector))
                        + cp.sum(cp.multiply(zy_import, interm_prod_vector_short))
                        + cp.sum(cp.multiply(opt_manu, interm_prod_vector)) ==
                        cp.sum(cp.multiply(io_matrix @ opt_manu, interm_prod_vector))
                        + cp.sum(cp.multiply(opt_export, interm_prod_vector))
                        + cp.sum(cp.multiply(zy_export, interm_prod_vector_short))
                        ]

        constraints += [cp.sum(cp.multiply(opt_import, fin_prod_vector))
                        + cp.sum(cp.multiply(zy_import, fin_prod_vector_short))
                        + cp.sum(cp.multiply(opt_manu, fin_prod_vector)) ==
                        cp.sum(cp.multiply(opt_demand, fin_prod_vector))
                        + cp.sum(cp.multiply(opt_export, fin_prod_vector))
                        + cp.sum(cp.multiply(zy_export, fin_prod_vector_short))
                        ]

        constraints += [cp.sum(cp.multiply(opt_import, fuelw_vector))
                        + cp.sum(cp.multiply(zy_import, fuelw_vector_short))
                        + cp.sum(cp.multiply(opt_supply, fuelw_vector)) ==
                        cp.sum(cp.multiply(opt_demand, fuelw_vector))
                        + cp.sum(cp.multiply(opt_export, fuelw_vector))
                        + cp.sum(cp.multiply(zy_export, fuelw_vector_short))
                        ]

        constraints += [cp.sum(cp.multiply(opt_supply, othindrnd_vector)) ==
                        cp.sum(cp.multiply(opt_demand, othindrnd_vector))
                        ]

        constraint_get_position(constraints_position, "Global_Material_Balance_test", constraints, constraint_counter)
        self.Logger.info(f"Global material balance constraints done.")

    def trade_deviation_penalties(self, ALL_DOMAINS_LEN, delta_trade_lower_bound, delta_trade_upper_bound,
                                  delta_prev_trade_decrease, delta_prev_trade_increase):
        """
        Defines penalties for deviations from trade bounds and from trade quantities in previous period.
        These penalties allow to flexiblize the optimization constraints for trade. Two penalty options are available:
         - Penalties for deviations from trade lower and upper bounds
         - Penalties for deviations from trade quantities in previous period
        :param ALL_DOMAINS_LEN: aligned length of all optimized domains
        :param delta_trade_lower_bound: deviations of optimized trade quantities from trade lower bound
        :param delta_trade_upper_bound: deviations of optimized trade quantities from trade upper bound
        :param delta_prev_trade_decrease: decreases of optimized trade quantities from trade quantities in previous
         period
        :param delta_prev_trade_increase: increases of optimized trade quantities from trade quantities in previous
         period
        :return trade_bound_deviation_penalty: aligned penalties for trade bound deviations
        :return sum_delta_trade_bound: sum of deviations from lower and upper trade bounds
        :return trade_prev_deviation_penalty: aligned penalties for deviations from trade quantities in previous period
        :return sum_delta_trade_prev: sum of deviations in trade quantities from trade quantities in previous period
        """
        domain_col_name = VarNames.DOMAIN_COLNAME.value
        zy_region_var = VarNames.ZY_REGION.value
        sum_delta_trade_bound = cp.abs(delta_trade_lower_bound) + cp.abs(delta_trade_upper_bound)
        sum_delta_trade_prev = cp.abs(delta_prev_trade_decrease) + cp.abs(delta_prev_trade_increase)

        trade_mask = self.Data.OptimizationHelpers.data[
            ([x in [
                str(Domains.TransportationExport),
                str(Domains.TransportationImport)] for x in self.Data.OptimizationHelpers.data[domain_col_name]]) &
            (self.Data.OptimizationHelpers.data[Domains.Supply.region_code] != zy_region_var)
            # & (self.Data.OptimizationHelpers.data[QUANTITY_COLNAME] > Constants.NON_ZERO_PARAMETER.value)
            # TODO check relevance: th_note including countries with lower or equal trade quantities than non-zero
            #  leads to small but non negligible changes (comprehensive analysis is would be needed)
            #  see results for trade_penalties_for_every_regions/ trade_penalties_only_for_trading_regions
            ]

        prev_wp = pd.DataFrame(
            trade_mask[Domains.TransportationImport.commodity_code]).merge(
            self.Data.WorldPrices.data_periods[
                self.Data.WorldPrices.data_periods["Period"] == self.present_period - 1],
            left_on=f"{Domains.TransportationImport.commodity_code}",
            right_on=f"{Domains.TransportationImport.commodity_code}",
            how="left")

        trade_mask = trade_mask.index
        prev_wp = prev_wp.set_index(trade_mask)["WorldPrice"]  # TODO Hard code (future work)

        # Penalty for deviations from trade bounds
        trade_bound_deviation_penalty = pd.DataFrame(np.zeros(ALL_DOMAINS_LEN))
        # trade deviation penalty with previous world prices
        trade_bound_deviation_penalty.loc[trade_mask, 0] = prev_wp.loc[trade_mask]
        trade_bound_deviation_penalty = np.array(trade_bound_deviation_penalty)
        # trade deviation penalty with abitrary weight
        # trade_deviation_penalty.loc[trade_mask, 0] = Constants.TRADE_BOUND_DEVIATION_PENALTY.value

        # Penalty for deviations from trade in previous period
        trade_prev_deviation_penalty = pd.DataFrame(np.zeros(ALL_DOMAINS_LEN))
        trade_prev_deviation_penalty.loc[trade_mask, 0] = Constants.TRADE_PREV_DEVIATION_PENALTY.value
        trade_prev_deviation_penalty = np.array(trade_prev_deviation_penalty)

        return trade_bound_deviation_penalty, sum_delta_trade_bound, trade_prev_deviation_penalty, sum_delta_trade_prev

    def setup_optimization_constraints(self, dynamization_activated: bool):
        """
        Set-up the optimization constraints and save them together with related information for the optimization
        :param dynamization_activated: dynamization of the model on or off #TODO remove after validation?
        :return: optimization parameters (opt_quantity), optimization constraints (constraints,
        constraints_position), slopes and intercepts and domain lengths (DOMAIN_LEN, ALL_DOMAIN_LEN)
        """
        DOMAIN_LEN, ALL_DOMAINS_LEN, opt_quantity, slope, intercept = self.optimization_setup()
        opt_lbs, opt_ubs = self.set_bounds(dynamization_activated=dynamization_activated)
        opt_lbs, opt_ubs = opt_lbs.reshape(ALL_DOMAINS_LEN, 1), opt_ubs.reshape(ALL_DOMAINS_LEN, 1)

        constraints = []
        constraints_position = {}
        constraint_counter = [0]

        # Infeasibilty-check of the optimization problem (check for negativ bounds)
        verify_ubs, verify_lbs = pd.DataFrame(opt_ubs), pd.DataFrame(opt_lbs)
        if not verify_ubs[verify_ubs[0] < 0].index.any():
            pass
        else:
            verify_index = verify_ubs[verify_ubs[0] < 0].index
            if self.UserOptions.verbose_calculation_logger:
                self.Logger.info(f"Upper bound problem with following regions and products")
                self.Logger.info(f"{self.Data.OptimizationHelpers.data.loc[verify_index]}")

        if not verify_lbs[verify_lbs[0] < 0].index.any():
            pass
        else:
            verify_index = verify_lbs[verify_lbs[0] < 0].index
            if self.UserOptions.verbose_calculation_logger:
                self.Logger.info(f"Lower bound problem with following regions and products")
                self.Logger.info(f"{self.Data.OptimizationHelpers.data.loc[verify_index]}")

        # DCP-rules-check of the optimization problem (curvature of the objective function - slope)
        verify_slope = pd.DataFrame(slope)
        if not verify_slope[verify_slope[0] >= 0.001].index.any(): #TODO Hard code (future work)
            pass
        else:
            verify_index = verify_slope[verify_slope[0] >= 0.0001].index #TODO Hard code (future work)
            if self.UserOptions.verbose_calculation_logger:
                self.Logger.info(f"DCP-Problem in slope with following regions and products")
                self.Logger.info(f"{self.Data.OptimizationHelpers.data.loc[verify_index]}")
            # Exogen slope correction
            pd.DataFrame(slope).loc[verify_index] = pd.DataFrame(slope).loc[verify_index] * -1

        # DCP-rules-check of the optimization problem (curvature of the objective function - intercept)
        verify_intercept = pd.DataFrame(intercept)
        if not verify_intercept[verify_intercept[0] >= 0.001].index.any():
            pass
        else:
            verify_index = verify_intercept[verify_intercept[0] >= 0.0001].index #TODO Hard code (future work)
            if self.UserOptions.verbose_calculation_logger:
                self.Logger.info(f"DCP-Problem in intercept with following regions and products")
                self.Logger.info(f"{self.Data.OptimizationHelpers.data.loc[verify_index]}")
            # Exogen intercept correction
            # pd.DataFrame(intercept).loc[verify_index] = pd.DataFrame(intercept).loc[verify_index] * -1 #TODO check relevance

        if self.present_period == 0:
            self.constraint_trade(constraints, constraints_position, constraint_counter, opt_quantity, opt_lbs, opt_ubs,
                                  DOMAIN_LEN)
        else:
            (delta_trade_upper_bound, delta_trade_lower_bound, delta_prev_trade_increase,
             delta_prev_trade_decrease) = self.constraint_trade_new(
                constraints, constraints_position, constraint_counter, opt_quantity, opt_lbs, opt_ubs,
                DOMAIN_LEN, ALL_DOMAINS_LEN)
        self.constraint_supply(constraints, constraints_position, constraint_counter, opt_quantity, opt_ubs, DOMAIN_LEN)
        self.constraint_manufacture(constraints, constraints_position, constraint_counter, opt_quantity, opt_ubs,
                                    DOMAIN_LEN)
        self.constraint_max_harvest(constraints, constraints_position, constraint_counter, opt_quantity, DOMAIN_LEN)
        self.constraint_material_balance(constraints, constraints_position, constraint_counter, opt_quantity,
                                         DOMAIN_LEN)
        self.constraint_material_balance_zy(constraints, constraints_position, constraint_counter, opt_quantity,
                                            DOMAIN_LEN)

        if self.UserOptions.global_material_balance:
            self.constraint_global_material_balance(constraints, constraints_position, constraint_counter, opt_quantity,
                                                    DOMAIN_LEN)

        self.constraint_demand(constraints, constraints_position, constraint_counter, opt_quantity, opt_ubs, opt_lbs,
                               DOMAIN_LEN)
        if self.present_period == 0:
            return (DOMAIN_LEN, ALL_DOMAINS_LEN, opt_quantity, slope, intercept, constraints, constraints_position,
                    opt_ubs, opt_lbs)
        else:
            return (DOMAIN_LEN, ALL_DOMAINS_LEN, opt_quantity, slope, intercept, constraints,
                    constraints_position, opt_ubs, opt_lbs, delta_trade_upper_bound, delta_trade_lower_bound,
                    delta_prev_trade_increase, delta_prev_trade_decrease)

    def optimization(self, solver_max_iteration: int, solver_rel_accuracy: int, solver_abs_accuracy: int,
                     dynamization_activated: bool):
        """
        Defines the objective function and the optimization problem, setup the cvxpy-solver environment. Implement
        penalties for trade deviations considered within optimization for the base period.
        :param solver_max_iteration: solver parameter for maximal iteration
        :param solver_rel_accuracy: solver parameter for relative accuracy
        :param solver_abs_accuracy: solver parameter for absolute accuracy
        :param dynamization_activated: flag to activate or deactivate the dynamization in the model
        :return: optimization problem, optimization parameters (opt_quantity), and
        optimization constraints (constraints, constraints_position)
        """
        if self.present_period == 0:
            (DOMAIN_LEN, ALL_DOMAINS_LEN, opt_quantity, slope, intercept, constraints, constraints_position, opt_ubs,
             opt_lbs) = self.setup_optimization_constraints(
                dynamization_activated=dynamization_activated)
        else:
            (DOMAIN_LEN, ALL_DOMAINS_LEN, opt_quantity, slope, intercept, constraints, constraints_position, opt_ubs,
             opt_lbs, delta_trade_upper_bound, delta_trade_lower_bound,
             delta_prev_trade_increase, delta_prev_trade_decrease) = self.setup_optimization_constraints(
                dynamization_activated=dynamization_activated)

            (trade_bound_deviation_penalty, sum_delta_trade_bound, trade_prev_deviation_penalty, sum_delta_trade_prev
             ) = self.trade_deviation_penalties(ALL_DOMAINS_LEN=ALL_DOMAINS_LEN,
                                                delta_trade_lower_bound=delta_trade_lower_bound,
                                                delta_trade_upper_bound=delta_trade_upper_bound,
                                                delta_prev_trade_decrease=delta_prev_trade_decrease,
                                                delta_prev_trade_increase=delta_prev_trade_increase)

        # Objective function
        if self.present_period == 0:
            objective_function = (cp.multiply(intercept, opt_quantity)
                                  + 1 / 2 * cp.multiply(slope, cp.square(opt_quantity)))
        else:
            objective_function = (cp.multiply(intercept, opt_quantity)
                                  + 1 / 2 * cp.multiply(slope, cp.square(opt_quantity))
                                  - cp.multiply(trade_bound_deviation_penalty, sum_delta_trade_bound))

            # Add following to the objective function to introduce second bound penalizing deviation of optimized trade
            # quantity to trade quantity of last period (allows to limit changes in trade)
            # - cp.multiply(trade_prev_deviation_penalty, sum_delta_trade_prev))

        self.Logger.info(f"Set up objective function done.")
        optimization_problem = cp.Problem(cp.Maximize(cp.sum(objective_function)), constraints)
        problem_data, chain, inversed_data = optimization_problem.get_problem_data(solver=cp.OSQP)
        self.Logger.info(f"===========================")
        self.Logger.info(f"Optimization problem configurations:")
        self.Logger.info(f"===========================")
        self.Logger.info(f"Number of optimized variables: {optimization_problem.size_metrics.num_scalar_variables}")
        self.Logger.info(f"Number of optimization constraints: {len(optimization_problem.constraints)}")
        self.Logger.info(f"Containing {problem_data['n_eq']} equalities and"
                         f" {problem_data['n_ineq']} inequalities")

        self.Logger.info(f"===========================")
        self.Logger.info(f"Solver settings:")
        self.Logger.info(f"===========================")
        self.Logger.info(f"Used solver: {cp.OSQP}")
        self.Logger.info(f"Max iterations: {solver_max_iteration}")
        self.Logger.info(f"Absolute solver accuracy: {format(solver_abs_accuracy, '.5f')}")
        self.Logger.info(f"Relative solver accuracy: {format(solver_rel_accuracy, '.5f')}")
        self.Logger.info(f"===========================")

        try:
            optimization_problem.solve(
                solver=cp.OSQP,
                verbose=self.UserOptions.verbose_optimization_logger,
                max_iter=solver_max_iteration,
                eps_abs=solver_rel_accuracy, 
                eps_rel=solver_abs_accuracy
            )
        except cvxpy.error.DCPError:
            self.Logger.error(f"...DCPError while optimization.", exc_info=True)

        self.Logger.info(f"===========================")
        self.Logger.info(f"Optimization problem for period {self.present_period} solved")
        self.Logger.info(f"===========================")
        self.Logger.info(f"Problem status: {optimization_problem.solution.status}")
        self.Logger.info(f"Optimal objective: {-1 * optimization_problem.solution.opt_val}")
        self.Logger.info(f"Number of iterations needed: {optimization_problem.solution.attr['num_iters']}")
        self.Logger.info(f"Run time: {optimization_problem.solution.attr['solve_time']} sec.")
        self.Logger.info(f"===========================")

        Optimization = DataContainer("optimization_results")
        Optimization.optimization_problem = optimization_problem
        Optimization.optimized_quantity = opt_quantity
        Optimization.optimization_constraints = constraints
        Optimization.optimization_constraints_position = constraints_position
        Optimization.optimization_upper_bound = opt_ubs
        Optimization.optimization_lower_bound = opt_lbs

        if self.present_period == 0:
            self.Data.set_attribute("OptimizationResults", Optimization)
        else:
            self.Data["OptimizationResults"].optimization_problem = Optimization.optimization_problem
            self.Data["OptimizationResults"].optimized_quantity = Optimization.optimized_quantity
            self.Data["OptimizationResults"].optimization_constraints = Optimization.optimization_constraints
            self.Data["OptimizationResults"].optimization_constraints_position = (
                Optimization.optimization_constraints_position)
            self.Data["OptimizationResults"].optimization_upper_bound = Optimization.optimization_upper_bound
            self.Data["OptimizationResults"].optimization_lower_bound = Optimization.optimization_lower_bound

    def dynamize(self, present_period: int, period_length: int, period_block: int, actual_year:int):
        """Call all functions for dynamization from script model_helpers.py
        :param present_period: number of target period
        :param period_length: years of the target period
        :param period_block: number of specification section from exogenous change sheet applied for target period
        :param actual_year: final year of target period for the simulation output
        """
        period_info = {"present": present_period, "length": period_length, "block": period_block, "year": actual_year} #TODO Hard code (future work)
        dynamize_demand(Data=self.Data.Demand.data_aligned,
                        DataChange=self.Data.ExogChangeDemand.data_aligned,
                        period_info=period_info)
        dynamize_supply(self,
                        Data=self.Data.Supply.data_aligned,
                        DataChange=self.Data.ExogChangeSupply.data_aligned,
                        DataForest=self.Data.Forest.data_aligned,
                        DataForestChange=self.Data.ExogChangeForest.data_aligned,
                        Logger=self.Logger,
                        period_info=period_info)
        dynamize_manufacturing_cost(Data=self.Data.ManufactureCost.data_aligned,
                                    DataChange=self.Data.ExogChangeManufactureCost.data_aligned,
                                    period_info=period_info)
        dynamize_manufacturing_coeff(Data=self.Data.ManufactureCoefficients.data_aligned,
                                     DataChange=self.Data.ExogChangeManufactureCoefficients.data_aligned,
                                     period_info=period_info)
        dynamize_transportation(DataExport=self.Data.TransportationExport.data_aligned,
                                DataImport=self.Data.TransportationImport.data_aligned,
                                DataExportChange=self.Data.ExogChangeTradeExport.data_aligned,
                                DataImportChange=self.Data.ExogChangeTradeImport.data_aligned,
                                period_info=period_info)
        self.Logger.info(f"Dynamization finished.")

    def extract_optimization_results(self, opt_quantity: cp.Variable, constraints: list, constraints_position: dict,
                                     opt_ubs: np.ndarray, opt_lbs: np.ndarray, capped_prices: bool,
                                     cleaned_opt_quantity: bool):
        """
        Extracts the optimization results for quantities and prices, update data_aligned (contain data used for 
        the actual period) for the respective optimization domains, add optimization results to OptimizationHelpers 
        (contain data for all periods).
        Optimization results are processed depending on the user input, product prices are either calculated or 
        extracted as shadow prices of the material balances for all region and zy-region. 
        :params opt_quantity: independent variable
        :params constraints: list where constraints are saved for the optimization
        :params constraints_position: dict where information (constraint name and position) are saved for the result
        extraction
        :params opt_ubs: optimization upper bounds
        :params opt_lbs: optimization lower bounds
        :params capped_prices: flag for correction of production prices (demprices=prodprices) # TODO remove after validation?
        :params cleaned_opt_quantity: flag to clean optimization quantities using upper and lower bounds
        """
        domain_col_name = VarNames.DOMAIN_COLNAME.value
        price_col_name = VarNames.PRICE_COLNAME.value
        shadow_price_col_name = VarNames.SHADOW_PRICE_COLNAME.value
        total_production_cost_col_name = VarNames.TOTAL_PRODUCTION_COST.value
        quantity_col_name = VarNames.QUANTITY_COLNAME.value
        transp_cost_col_name = VarNames.TRANSPORT_COSTS.value

        shadow_prod_price_var = VarNames.SHADOW_PROD_PRICE.value
        calc_prod_price_var = VarNames.CALC_PROD_PRICE.value
        shadow_world_price_var = VarNames.SHADOW_WORLD_PRICE.value
        avg_world_price_var = VarNames.AVG_WORLD_PRICE.value
        constant_world_price_var = VarNames.CONSTANT_WORLD_PRICE.value
        exogen_world_price_var = VarNames.EXG_WORLD_PRICE.value

        for domain_name, quantity, price, elasticity_price in DomainIterator.extract_results(
                DomainIterator.OPTIMIZATION_DOMAINS):
            index_domain = self.Data.OptimizationHelpers.data[self.Data.OptimizationHelpers.data[
                                                                  domain_col_name] == domain_name].index
            # Extraction optimized quantities
            opt_quantity_domain = pd.DataFrame(opt_quantity.value[index_domain])[0]

            # Cleaned optimized quantities
            opt_ubs_domain, opt_lbs_domain = pd.DataFrame(opt_ubs[index_domain]), pd.DataFrame(opt_lbs[index_domain])
            opt_quantity_clean = pd.concat([
                opt_ubs_domain,
                pd.concat([opt_quantity_domain, opt_lbs_domain], axis=1).max(axis=1)], axis=1).min(axis=1)

            opt_quantity_domain.clip(lower=Constants.NON_ZERO_PARAMETER.value, inplace=True)
            opt_quantity_clean.clip(lower=Constants.NON_ZERO_PARAMETER.value, inplace=True)
            self.Data[domain_name].data_aligned[quantity].replace(Constants.NON_ZERO_PARAMETER.value, 0, inplace=True)

            if str(Domains.Supply) in domain_name:
                shadow_price = calc_product_shadow_price(self,
                                                         world_data=self.Data,
                                                         domain=domain_name,
                                                         price_column=price,
                                                         constraints=constraints,
                                                         constraints_position=constraints_position)

                calculated_price = calc_product_price(world_data=self.Data,
                                                      domain=domain_name,
                                                      price_column=price,
                                                      quantity_column=quantity,
                                                      elasticity_column=elasticity_price,
                                                      opt_quantity_clean=opt_quantity_clean)

                if self.UserOptions.calc_product_prices == shadow_prod_price_var:

                    shadow_price = shadow_price_correction(
                        deviation_threshold=Constants.PRICE_DEVIATION_THRESHOLD.value,
                        domain_name=domain_name,
                        shadow_price_prev=self.Data[domain_name].data_aligned[price],
                        shadow_price_new=shadow_price[0],
                        calc_price_new=calculated_price,
                        logger=self.Logger)

                elif self.UserOptions.calc_product_prices == calc_prod_price_var:
                    if capped_prices:
                        # post-optimization correction of supplyprices == importprices for rawmaterials

                        (raw_prod, interm_prod, fin_prod, fuelw, othindrnd
                         ) = extract_product_groups(world_data=self.Data, commodity_data=self.Data.Commodities,
                                                    region_data=self.Data.Regions, all_regions=False,
                                                    only_commodity_codes=True)

                        import_price = self.Data.TransportationImport.data_aligned[Domains.TransportationImport.price]
                        index_other_ind_roundwood = self.Data.TransportationImport.data_aligned[
                            self.Data.TransportationImport.data_aligned[
                                Domains.TransportationImport.commodity_code] != othindrnd].index
                        index_corrected_value = calculated_price[(calculated_price > import_price)].index
                        index_corrected_value = index_corrected_value.intersection(index_other_ind_roundwood)
                        calculated_price.loc[index_corrected_value] = import_price

                save_price_data(world_data=self.Data,
                                calc_price=calculated_price,
                                shadow_price=shadow_price,
                                world_price=None,
                                domain_name=domain_name,
                                index_domain=index_domain,
                                domain_price_name=price,
                                price_col_name=price_col_name,
                                shadow_price_col_name=shadow_price_col_name,
                                calc_product_prices_flag=self.UserOptions.calc_product_prices)

            elif str(Domains.Demand) in domain_name:
                shadow_price = calc_product_shadow_price(self,
                                                         world_data=self.Data,
                                                         domain=domain_name,
                                                         price_column=price,
                                                         constraints=constraints,
                                                         constraints_position=constraints_position)

                calculated_price = calc_product_price(world_data=self.Data,
                                                      domain=domain_name,
                                                      price_column=price,
                                                      quantity_column=quantity,
                                                      elasticity_column=elasticity_price,
                                                      opt_quantity_clean=opt_quantity_clean)

                if self.UserOptions.calc_product_prices == shadow_prod_price_var:

                    shadow_price = shadow_price_correction(
                        deviation_threshold=Constants.PRICE_DEVIATION_THRESHOLD.value,
                        domain_name=domain_name,
                        shadow_price_prev=self.Data[domain_name].data_aligned[price],
                        shadow_price_new=shadow_price[0],
                        calc_price_new=calculated_price,
                        logger=self.Logger)

                save_price_data(world_data=self.Data,
                                calc_price=calculated_price,
                                shadow_price=shadow_price,
                                world_price=None,
                                domain_name=domain_name,
                                index_domain=index_domain,
                                domain_price_name=price,
                                price_col_name=price_col_name,
                                shadow_price_col_name=shadow_price_col_name,
                                calc_product_prices_flag=self.UserOptions.calc_product_prices)

            elif str(Domains.ManufactureCost) in domain_name:
                shadow_price = calc_product_shadow_price(self,
                                                         world_data=self.Data,
                                                         domain=domain_name,
                                                         price_column=price,
                                                         constraints=constraints,
                                                         constraints_position=constraints_position)

                calculated_price = calc_product_price(world_data=self.Data,
                                                      domain=domain_name,
                                                      price_column=price,
                                                      quantity_column=quantity,
                                                      elasticity_column=elasticity_price,
                                                      opt_quantity_clean=opt_quantity_clean)

                # Standard setting for manucost price: calculated prices. Change flag to use shadow prices.
                shadow_manucost_flag = False
                if (self.UserOptions.calc_product_prices == shadow_prod_price_var) & shadow_manucost_flag:

                    shadow_price = shadow_price_correction(
                        deviation_threshold=Constants.PRICE_DEVIATION_THRESHOLD.value,
                        domain_name=domain_name,
                        shadow_price_prev=self.Data[domain_name].data_aligned[price],
                        shadow_price_new=shadow_price[0],
                        calc_price_new=calculated_price,
                        logger=self.Logger)

                save_price_data(world_data=self.Data,
                                calc_price=calculated_price,
                                shadow_price=shadow_price,
                                world_price=None,
                                domain_name=domain_name,
                                index_domain=index_domain,
                                domain_price_name=price,
                                price_col_name=price_col_name,
                                shadow_price_col_name=shadow_price_col_name,
                                calc_product_prices_flag=self.UserOptions.calc_product_prices)

            elif str(Domains.TransportationExport) in domain_name:
                shadow_world_price = calc_world_shadow_price(world_data=self.Data,
                                                             constraints=constraints,
                                                             constraints_position=constraints_position)

                if self.UserOptions.calc_world_prices == constant_world_price_var:
                    # static world prices
                    self.Logger.info(f"Constant world prices activated")
                    constant_world_price = (
                        self.Data.WorldPrices.data["WorldPrice"].loc[:len(self.Data.Commodities.data)])
                    DataManager.save_world_prices(WorldData=self.Data, WorldPrices=self.Data.WorldPrices,
                                                  shadow_world_price=constant_world_price,
                                                  present_period=self.present_period)
                    constant_world_price = pd.DataFrame(pd.concat([constant_world_price] *
                                                                  len(self.Data.Regions.data), axis=0)
                                                        ).rename(columns={"WorldPrice": 0}).reset_index(drop=True)
                    world_price = constant_world_price

                elif self.UserOptions.calc_world_prices == shadow_world_price_var:
                    # dynamic world prices
                    self.Logger.info(f"Shadow world prices activated")
                    short_shadow_world_price = shadow_world_price.iloc[:len(self.Data.Commodities.data)]

                    DataManager.save_world_prices(WorldData=self.Data, WorldPrices=self.Data.WorldPrices,
                                                  shadow_world_price=short_shadow_world_price,
                                                  present_period=self.present_period)
                    world_price = shadow_world_price

                # TODO add average_WP to model (future work) 
                elif self.UserOptions.calc_world_prices == avg_world_price_var:
                    self.Logger.info(f"Average world prices activated, !not yet implemented!")

                elif self.UserOptions.calc_world_prices == exogen_world_price_var:
                    # exogen world prices
                    self.Logger.info(f"Exogen world prices activated")
                    exogen_world_price = pd.DataFrame(self.WorldPriceData.data[int(f"{self.actual_year}")]).rename(
                        columns={int(f"{self.actual_year}"): 0})

                    DataManager.save_world_prices(WorldData=self.Data, WorldPrices=self.Data.WorldPrices,
                                                  shadow_world_price=exogen_world_price,
                                                  present_period=self.present_period)
                    exogen_world_price = pd.DataFrame(pd.concat([exogen_world_price] *
                                                                len(self.Data.Regions.data), axis=0)
                                                      ).rename(columns={"WorldPrice": 0}).reset_index(drop=True)

                    world_price = exogen_world_price

                save_price_data(world_data=self.Data,
                                calc_price=None,
                                shadow_price=shadow_world_price,
                                world_price=world_price,
                                domain_name=domain_name,
                                index_domain=index_domain,
                                domain_price_name=price,
                                price_col_name=price_col_name,
                                shadow_price_col_name=shadow_price_col_name,
                                calc_product_prices_flag=self.UserOptions.calc_product_prices)

                world_price = pd.DataFrame(
                    world_price[: len(self.Data.Commodities.data)]).rename(columns={0: "world prices"})
                world_price = pd.concat([self.Data.Commodities.data,
                                         pd.DataFrame([self.present_period] * len(self.Data.Commodities.data)),
                                         world_price], axis=1).rename(columns={0: "Period"})

                if self.UserOptions.verbose_calculation_logger:
                    self.Logger.info(f"World prices: {world_price}")

            elif str(Domains.TransportationImport) in domain_name:
                shadow_world_price = calc_world_shadow_price(world_data=self.Data,
                                                             constraints=constraints,
                                                             constraints_position=constraints_position)

                transportation_cost = calc_product_price(world_data=self.Data,
                                                         domain=domain_name,
                                                         price_column=transp_cost_col_name,
                                                         quantity_column=quantity,
                                                         elasticity_column=elasticity_price,
                                                         opt_quantity_clean=opt_quantity_domain)

                transportation_cost = transportation_cost + self.Data.TransportationExport.data_aligned[price]

                transportation_cost.fillna(0, inplace=True)
                transportation_cost.replace(np.inf, 0, inplace=True)
                transportation_cost.replace(-np.inf, 0, inplace=True)

                save_price_data(world_data=self.Data,
                                calc_price=None,
                                shadow_price=shadow_world_price,
                                world_price=transportation_cost,
                                domain_name=domain_name,
                                index_domain=index_domain,
                                domain_price_name=price,
                                price_col_name=price_col_name,
                                shadow_price_col_name=shadow_price_col_name,
                                calc_product_prices_flag=self.UserOptions.calc_product_prices)

            if cleaned_opt_quantity:
                self.Data[domain_name].data_aligned[quantity] = opt_quantity_clean
                self.Data.OptimizationHelpers.data.loc[index_domain, quantity_col_name] = pd.DataFrame(
                    opt_quantity_clean).set_index(index_domain)[0]
            else:
                self.Data[domain_name].data_aligned[quantity] = opt_quantity_domain
                self.Data.OptimizationHelpers.data.loc[index_domain, quantity_col_name] = pd.DataFrame(
                    opt_quantity_domain).set_index(index_domain)[0]

        # unit test - verification trade balance
        verify_trade_balance(world_data=self.Data,
                             user_option=self.UserOptions,
                             logger=self.Logger,
                             verification_threshold=1)

        # unit test - verification material balance
        verify_material_balance(world_data=self.Data,
                                user_option=self.UserOptions,
                                logger=self.Logger,
                                verification_threshold=1)

        # unit test - verification global material balance
        verify_global_material_balance(world_data=self.Data,
                                       user_option=self.UserOptions,
                                       logger=self.Logger)

        # unit test - verification supply upper bound
        verify_supply_upper_bound(world_data=self.Data,
                                  user_option=self.UserOptions,
                                  logger=self.Logger,
                                  domain_col_name=domain_col_name,
                                  verification_threshold=1)

        # unit test - verification trade bounds
        verify_trade_bounds(world_data=self.Data,
                            opt_lbs=opt_lbs,
                            opt_ubs=opt_ubs,
                            user_option=self.UserOptions,
                            logger=self.Logger,
                            verification_threshold=1)

        self.Logger.info(f"Extraction done.")
