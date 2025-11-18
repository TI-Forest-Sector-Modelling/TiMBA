import pandas as pd
import numpy as np

from TiMBA.helpers.utils import DomainIterator, mask_data
from TiMBA.parameters.Domains import Domains, RestOfWorld
from TiMBA.data_management.DataContainer import DataContainer, InterfaceWorldData, AdditionalInformation
from TiMBA.parameters.Defines import Constants
from TiMBA.data_management.ParameterCollector import ParameterCollector
from TiMBA.parameters.REGEX_patterns import PERIOD_PATTERN
from TiMBA.parameters.paths import RESULTS_OUTPUT, RESULTS_OUTPUT_AGG, FOREST_OUTPUT, WORLD_PRICE_OUTPUT, MANUFACTURE_OUTPUT
from TiMBA.parameters.Defines import VarNames
from TiMBA.logic.model_helpers import extract_product_groups
from pathlib import Path
from os import path
import os


class DataManager:

    @staticmethod
    def load_data(filepath, table_name, input_source):
        if input_source.lower() == "excel":
            return DataManager.read_excel(filepath, table_name)
        elif input_source.lower() == "csv":
            return DataManager.read_csv(filepath)
        elif input_source.lower() == "sql":
            return DataManager.load_table()
        else:
            raise TypeError(f"Input source type {input_source} is not defined.")

    @staticmethod
    def create_subset(Data: DataContainer, get_attr: str, subset: list, attribute_name: str = None,
                      create_view: bool = False):
        """
        Method to set a subset of obj.data as view or copy to a new attribute or overwrite data.
        :param Data: original DF
        :param get_attr: name of domain
        :param subset: Subset of chosen variable names / column names
        :param attribute_name: Name for new attribute passed to obj.set_attribute()
        :param create_view: If True, the newly created subset of data in attribute obj.name, is a view of obj.data.
            This can lead to warnings when setting values to a slice/view of a DataFrame.
        """
        if attribute_name is None:
            Data[get_attr] = Data[get_attr][subset]
        elif isinstance(attribute_name, str) and len(attribute_name) > 0:
            if create_view:
                Data.set_attribute(attribute_name, Data[get_attr][subset])
            else:
                Data.set_attribute(attribute_name, Data[get_attr][subset].copy())
        else:
            raise AttributeError(f"Acceptable filter conditions not met.")

    @staticmethod
    def set_attribute(Data: DataContainer, name, value):
        Data.set_attribute(name, value)

    @staticmethod
    def read_excel(input_filepath, table_name):
        xlsx_connection = pd.ExcelFile(input_filepath)
        return xlsx_connection.parse(table_name)

    @staticmethod
    def read_csv(input_filepath):
        return pd.read_csv(input_filepath)

    @staticmethod
    def load_table():
        raise NotImplementedError("No SQL-Table load currently implemented.")

    @staticmethod
    def write_to_csv(Data: DataContainer, attribute: str, target_filepath: str, mode: str = "a+", sep: str = ",",
                     index: bool = False):
        Data[attribute].to_csv(target_filepath, mode=mode, sep=sep, index=index)

    @staticmethod
    def serialize_to_pickle(obj, target_filepath: str):
        """
        Write ("wb") object as pickle file to target path.
        :param obj: Object to save
        :param target_filepath: file path to save the object
        """
        import pickle
        import gzip
        with gzip.open(target_filepath, "wb") as pkl_file:
            pickle.dump(obj, pkl_file)

    @staticmethod
    def restore_from_pickle(src_filepath: str):
        """
        Read ("rb") object from pickle file in source path.
        :param src_filepath: source path to read the object from pkl
        """
        import pickle
        import gzip
        with gzip.open(src_filepath, "rb") as pkl_file:
            obj = pickle.load(pkl_file)
        return obj

    @staticmethod
    def read_world_data(Data: DataContainer, domain_name: str) -> None:
        """
        Load world.xlsx and save to DataContainer.
        :param Data: DataContainer to be filled with data from Excel
        :param domain_name: Domain specific name
        """
        Data.data = DataManager.load_data(Data.filepath, domain_name, "Excel")
        Data.update_domain_name(domain_name)

    @staticmethod
    def read_world(WorldData: InterfaceWorldData):
        """
        Load world.xlsx and saved them to InterfaceWorldData
        :param WorldData: InterfaceworldData to be filled with data from Excel
        """
        for domain_name in DomainIterator.get_domain_names(DomainIterator.MAIN_DOMAINS):
            WorldData.check_attr(domain_name, temporary=True)
            WorldData.set_attribute(domain_name, DataContainer(WorldData.filepath))
            DataManager.read_world_data(WorldData[domain_name], domain_name)

    @staticmethod
    def retrieve_periods(Data: DataContainer):
        """
        Retrieves Period Nr and Year from ExogChange and adds to ExogChange.
        : param Data:  DataContainer to be filled with data from Excel
        """
        Data.data['Period'] = None
        Data.data['ForecastYears'] = None
        regex_res = Data.data.iloc[:, 0].apply(
            lambda x: PERIOD_PATTERN.findall(x)[0] if PERIOD_PATTERN.findall(x) else None).dropna()
        split_indices = regex_res.index.values

        for i, (idx, (period, forcast_years)) in enumerate(regex_res.items()):
            next_idx = split_indices[i + 1] - 1 if i + 1 < len(split_indices) else Data.data.shape[0]
            Data.data.loc[idx:next_idx, 'Period'] = int(period)
            Data.data.loc[idx:next_idx, 'ForecastYears'] = int(forcast_years)

    @staticmethod
    def drop_masking_column(WorldData: InterfaceWorldData):
        """
        Treat domains which are splitted by columns and drop the column on which domain was splitted. Runs in
        separate loop to ensure propper splitting of nested periods.
        :param WorldData: Container which contains complete world data of all domains.
        """
        for domain_name, split_list in DomainIterator.get_domain_splitting(DomainIterator.SPLIT_DOMAINS):
            for i, sub_domain in enumerate(split_list):
                sub_domain_name = str(sub_domain)
                if sub_domain.mask_axis == 0:
                    mask_column_name = WorldData[domain_name].data.iloc[:, sub_domain.column_index].name
                    WorldData[sub_domain_name].data.drop(mask_column_name, inplace=True, axis=1)

    @staticmethod
    def split_base_content(WorldData: InterfaceWorldData):
        """
        Loop for splitting base content in sub domains (Manufacture, Transportation, ExogChange)
        :param WorldData: World data collection
        """
        DataManager.retrieve_periods(WorldData.ExogChange)

        for domain_name, split_list in DomainIterator.get_domain_splitting(DomainIterator.SPLIT_DOMAINS):
            for i, sub_domain in enumerate(split_list):
                sub_domain_name = str(sub_domain)
                WorldData.check_attr(sub_domain_name, temporary=True)
                WorldData.set_attribute(sub_domain_name, DataContainer(WorldData.filepath))
                WorldData[sub_domain_name].data = mask_data(
                    WorldData[domain_name], sub_domain.column_index, sub_domain.splitting_mask, sub_domain.mask_axis)
                WorldData[sub_domain_name].update_domain_name(sub_domain_name)

        DataManager.drop_masking_column(WorldData)

    @staticmethod
    def drop_sheet_description(WorldData: InterfaceWorldData):
        """
        Drop the first rows of every sheet where the column names are described
        :param WorldData: World data collection
        """
        for domain_name in DomainIterator.get_domain_names(DomainIterator.DESCRIPTION_DOMAINS):
            start_index = max(
                    WorldData[domain_name].data[WorldData[domain_name].data[WorldData[
                        domain_name].data.columns[0]] == '='].index) + 1

            WorldData[domain_name].data = WorldData[domain_name].data.iloc[start_index:].reset_index(drop=True)

    @staticmethod
    def drop_empty_columns(WorldData: InterfaceWorldData):
        """
        Drop all columns from world.xlsx with NA
        :param WorldData: World data collection
        """
        for domain_name in DomainIterator.get_domain_names(DomainIterator.FINAL_DOMAINS):
            WorldData[domain_name].data.dropna(axis=1, how='all', inplace=True)

    @staticmethod
    def get_column_length(WorldData: InterfaceWorldData, domain):
        """
        Length of column for specific domain is retrieved and saved as a new attribute "df_length" in the domain
        :param WorldData: World data collection
        :param domain: Any domain for which column length is needed
        """
        WorldData[str(domain)].set_attribute("df_length", WorldData[str(domain)].data.shape[0])

    @staticmethod
    def add_rest_world(WorldData: InterfaceWorldData):
        """
        Add RestOfWorld-region (zy) to Domain.Region
        :param WorldData: World data collection
        """
        WorldData.Regions.data = pd.concat([WorldData.Regions.data,
                                            pd.DataFrame(RestOfWorld)]).reset_index(drop=True)

    @staticmethod
    def create_base_matrix(WorldData: InterfaceWorldData):
        """
        Creates cartesian product table - matrix from Regions and Commodities, saved as a new attribute
        "data_aligned" to World data collection
        :param WorldData: World data collection
        """
        basematrix = WorldData.Regions.data.join(WorldData.Commodities.data, how="cross")
        WorldData.set_attribute("data_aligned", basematrix)

    @staticmethod
    def verify_base_year(WorldData: InterfaceWorldData, UserOptions: ParameterCollector, Logger):
        """
        Compare base year from input file and from user input. At the moment the base 
        year from input file will overwrite the user input.
        :param WorldData: World data collection
        :param UserOptions: User input
        :param Logger: Logger
        """
        base_year_world = WorldData.Specification.data["Property Value"][0]

        if UserOptions.year != int(base_year_world):
            Logger.info(f"User input for base year ({UserOptions.year}) does not correspond to base year from world"
                        f" input file ({int(base_year_world)}).")
            Logger.info(f"User input for base year is replaced by base year from world input file.")
            UserOptions.year = int(base_year_world)

    @staticmethod
    def align_df(WorldData: InterfaceWorldData):
        """
        Align all relevant dataframes for further calculations to the uniform length of the base_matrix.
        Aligned dataframes are saved as a new attribute "data_aligned" to each Domains of ALIGN_DOMAINS
        For ExogChange-Domains, each period is aligned separatly and period info are added
        :param WorldData: World data collection
        """
        for domain in DomainIterator.get_domain(DomainIterator.ALIGN_DOMAINS):
            domain_name = str(domain)
            domain_region_code = domain.region_code
            domain_commodity_code = domain.commodity_code
            if 'ExogChange' in domain_name:
                for year in sorted(set(WorldData[domain_name].data['Period'])):
                    subset = WorldData[domain_name].data[WorldData[domain_name].data['Period'] == year]
                    data_aligned = pd.merge(
                        WorldData.data_aligned, subset,
                        left_on=[Domains.Regions.region_code, Domains.Commodities.commodity_code],
                        right_on=[domain_region_code, domain_commodity_code], how='left'
                    )
                    period_length = subset['ForecastYears'].unique()
                    data_aligned.loc[:, 'Period'] = data_aligned['Period'].fillna(year)
                    data_aligned.loc[:, 'ForecastYears'] = data_aligned['ForecastYears'].fillna(period_length[0])
                    if not hasattr(WorldData[domain_name], "data_aligned"):
                        WorldData[domain_name].set_attribute("data_aligned", data_aligned.copy())
                    else:
                        WorldData[domain_name].data_aligned = pd.concat(
                            [WorldData[domain_name].data_aligned, data_aligned.copy()], axis=0).reset_index(drop=True)
            else:
                WorldData[domain_name].set_attribute("data_aligned", WorldData.data_aligned.merge(
                    WorldData[domain_name].data,
                    left_on=[Domains.Regions.region_code, Domains.Commodities.commodity_code],
                    right_on=[domain_region_code, domain_commodity_code], how='left'))

    @staticmethod
    def align_forest(Forest: InterfaceWorldData.Forest, ExogChangeForest: InterfaceWorldData.ExogChangeForest,
                     Commodities: InterfaceWorldData.Commodities):
        """
        Align data-DataFrame of Forest in World Data Collection for all regions except zy-region and
        add new attribute "data_aligned" in Forest of World Data Collection, covering all combinations of
        products and regions
        :param Forest: Domain Forest of World Data Collection
        :param ExogChangeForest: Domain ExogChangeForest of World Data Collection
        :param Commodities: Domain Commodities of World Data Collection
        """
        data_aligned_forest, data_aligned_exogchange_forest = pd.DataFrame(), pd.DataFrame()
        for region in Forest.data[Domains.Forest.region_code]:
            forest_region = Forest.data[Forest.data[Domains.Forest.region_code] == region]

            data_aligned_forest = pd.concat([
                data_aligned_forest, pd.concat([forest_region] * Commodities.df_length)]).reset_index(drop=True)
        Forest.set_attribute("data_aligned", data_aligned_forest)

        for year in sorted(set(ExogChangeForest.data['Period'])):
            exogchange_forest_subset = ExogChangeForest.data[ExogChangeForest.data['Period'] == year]
            for region in exogchange_forest_subset[Domains.ExogChangeForest.region_code]:
                exogchange_forest_region = exogchange_forest_subset[exogchange_forest_subset[
                                                                        Domains.ExogChangeForest.region_code] == region]

                data_aligned_exogchange_forest = pd.concat([
                    data_aligned_exogchange_forest, pd.concat([exogchange_forest_region] *
                                                              Commodities.df_length)]).reset_index(drop=True)
        ExogChangeForest.set_attribute("data_aligned", data_aligned_exogchange_forest)

    @staticmethod
    def update_fuelwood_forest_param(WorldData:InterfaceWorldData):
        """
        Overwrites column fraction_fuelwood in data_aligned of Forest in World Data Collection with
        vector containing fraction_fuelwood for product 80 (fuelwood), 1 for product 78, 81, 82 (raw materials), and
        0 for other products (intermediate and semi-finished products). Commodity codes adapt dynamically to the input
        data. Obtained vector is used calculations for maximal harvestable forest stock (optimization constraint) and
        dynamization of Forest Domain.
        :param WorldData: World Data Collection
        """
        zy_region_var = VarNames.ZY_REGION.value
        (raw_prod, interm_prod, fin_prod, fuelw, othindrnd) = extract_product_groups(
            world_data=WorldData, commodity_data=WorldData.Commodities, region_data=WorldData.Regions,
            all_regions=False, only_commodity_codes=True)

        list_raw_material = sorted(list(set(
            WorldData.Supply.data[(WorldData.Supply.data[Domains.Supply.region_code] != zy_region_var) &
                                  (WorldData.Supply.data[Domains.Supply.commodity_code] <= othindrnd)]
            [Domains.Supply.commodity_code])))

        index_fuelwood = WorldData.data_aligned[
            WorldData.data_aligned[Domains.Commodities.commodity_code] == fuelw].index
        raw_material_from_forest = pd.concat([pd.DataFrame(index_fuelwood).rename(columns={0: "IndexFuelwood"}),
                                             WorldData.Forest.data[Domains.Forest.fraction_fuelwood]], axis=1).fillna(0)
        raw_material_from_forest = WorldData.data_aligned.reset_index().merge(
            raw_material_from_forest, left_on=["index"], right_on=["IndexFuelwood"], how="left")

        updated_raw_material_from_forest = pd.DataFrame()

        for region in WorldData.Regions.data[Domains.Regions.region_code]:
            for commodity in WorldData.Commodities.data[Domains.Commodities.commodity_code]:
                temporary_var = raw_material_from_forest[
                    (raw_material_from_forest[Domains.Regions.region_code] == region) &
                    (raw_material_from_forest[Domains.Commodities.commodity_code] == commodity)]

                if pd.Series(temporary_var[Domains.Commodities.commodity_code]).isin(pd.Series(
                        list_raw_material)).item():
                    updated_raw_material_from_forest = pd.concat([updated_raw_material_from_forest, pd.DataFrame(
                            temporary_var.loc[temporary_var[Domains.Commodities.commodity_code] == commodity,
                                              Domains.Forest.fraction_fuelwood]).fillna(1)])
                else:
                    updated_raw_material_from_forest = pd.concat([updated_raw_material_from_forest, pd.DataFrame(
                        temporary_var.loc[temporary_var[Domains.Commodities.commodity_code] == commodity,
                                          Domains.Forest.fraction_fuelwood]).fillna(0)])

        WorldData.Forest.data_aligned[Domains.Forest.fraction_fuelwood] = updated_raw_material_from_forest

    @staticmethod
    def add_default_io(WorldData: InterfaceWorldData):
        """
        Adds an attribute "default_io" that stores maximal io-coefficients retrieved from the Model-calibration into the
        object ManufactureCoefficients. Default_io are used to complement missing io-coefficients in World-inputfile to
        allow a production for all represented countries. When further processing the function, it
        must be ensured that the trade intertias for export are complemented.
        :param WorldData: World data collection
        """

        default_io = pd.DataFrame.from_dict(Domains.ManufactureCoefficients.default_IO)
        default_io = default_io.set_index(WorldData.Commodities.data[Domains.Commodities.commodity_code])
        default_io = default_io.loc[WorldData.Commodities.data[Domains.Commodities.commodity_code],
                                    [int(x) for x in WorldData.Commodities.data[Domains.Commodities.commodity_code]]]
        default_io = default_io.reset_index(drop=True)
        WorldData[str(Domains.ManufactureCoefficients)].set_attribute("default_io", default_io) # TODO hard coded future work

    @staticmethod
    def create_io_matrix(WorldData: InterfaceWorldData, update: bool = False, default_io: bool = False):
        """
        Builds a matrix of input-output-coefficients (io) for all combinations of regions and commodities;
        shape = (len(commodities) * len(regions)) * (len(commodities) * len(regions)); Missing io-coefficients are
        replaced using default io-coefficients; Save matrix as new attribute "ioMatrix" (= with zy-region) and
        "ioMatrixshort" (= without zy-region) in ManufactureCoefficients of World
        data collection
        :param WorldData: World data collection
        :param update: allows to create ioMatrix (update=False) or update existing ioMatrix (update=True)
        :param default_io: allows to implace default_io for originally non-producing regions
        """
        manufacture_coefficients = WorldData.ManufactureCoefficients.data_aligned
        flat_io_matrix = WorldData.data_aligned[[Domains.Regions.region_code, Domains.Commodities.commodity_code]]
        for runner in range(WorldData.Commodities.df_length):
            short_io_vector = manufacture_coefficients[manufacture_coefficients.CommodityCode == min(
                WorldData.data_aligned.CommodityCode) + runner].rename(
                columns={Domains.ManufactureCoefficients.quantity: min(WorldData.data_aligned.CommodityCode) + runner})
            long_io_vector = WorldData.data_aligned[[
                Domains.Regions.region_code, Domains.Commodities.commodity_code]].merge(
                short_io_vector, left_on=[Domains.Regions.region_code, Domains.Commodities.commodity_code],
                right_on=[Domains.ManufactureCoefficients.region_code,
                          Domains.ManufactureCoefficients.output_commodity], how="left")
            flat_io_matrix = pd.concat([flat_io_matrix, long_io_vector[min(
                WorldData.data_aligned.CommodityCode) + runner]], axis=1)

        flat_io_matrix = flat_io_matrix.drop([Domains.Regions.region_code,
                                              Domains.Commodities.commodity_code], axis=1).fillna(0)

        if default_io:
            flat_io_matrix_all = flat_io_matrix.iloc[
                                 :WorldData.Commodities.df_length * (WorldData.Regions.df_length - 1)]
            flat_io_matrix_zy = flat_io_matrix.iloc[
                                WorldData.Commodities.df_length * (WorldData.Regions.df_length - 1):]

            flat_default_io = pd.concat(
                [WorldData.ManufactureCoefficients.default_io] * (WorldData.Regions.df_length - 1),
                axis=0).reset_index(drop=True)
            flat_io_matrix_updated = pd.DataFrame()
            for commodity in WorldData.Commodities.data[Domains.Commodities.commodity_code]:
                flat_io_matrix_temp = flat_io_matrix_all[commodity].copy()
                flat_default_io_temp = flat_default_io[int(commodity)].copy()
                missing_io_index = flat_io_matrix_temp[flat_io_matrix_temp == 0].index
                flat_io_matrix_temp.loc[missing_io_index] = flat_default_io_temp[missing_io_index]
                flat_io_matrix_updated = pd.concat([flat_io_matrix_updated, flat_io_matrix_temp], axis=1)
            flat_io_matrix_updated = pd.concat([flat_io_matrix_updated, flat_io_matrix_zy], axis=0)

            flat_io_matrix = flat_io_matrix_updated

        large_io_matrix = np.zeros([0, len(WorldData.Regions.data) * len(WorldData.Commodities.data)])
        for i in range(len(WorldData.Regions.data)):
            matrix_main = np.array(flat_io_matrix[i * len(WorldData.Commodities.data):(i + 1) * len(
                WorldData.Commodities.data)].T)
            matrix_before = np.zeros([len(WorldData.Commodities.data), i * len(WorldData.Commodities.data)])
            matrix_after = np.zeros([len(WorldData.Commodities.data), len(WorldData.Regions.data) * len(
                WorldData.Commodities.data) - (i + 1) * len(WorldData.Commodities.data)])
            matrix_row = np.concatenate([matrix_before, matrix_main, matrix_after], axis=1)
            large_io_matrix = np.concatenate([large_io_matrix, matrix_row], axis=0)

        short_io_matrix = np.array(pd.DataFrame(large_io_matrix).iloc[
                                          : WorldData.data_aligned.shape[0] - WorldData.Commodities.df_length,
                                          :WorldData.data_aligned.shape[0] - WorldData.Commodities.df_length])

        if not update:
            WorldData.ManufactureCoefficients.set_attribute("ioMatrix", large_io_matrix)
            WorldData.ManufactureCoefficients.set_attribute("ioMatrixshort", short_io_matrix)
        else:
            WorldData.ManufactureCoefficients.ioMatrix = large_io_matrix
            WorldData.ManufactureCoefficients.ioMatrixshort = short_io_matrix

    @staticmethod
    def add_missing_manu_costs(WorldData: InterfaceWorldData):
        """
        Add missing manufacture costs for regions that do not produce specific commodities in world input data. Global
        maximal manufacture costs for each product are implaced. Uniform output elasticity of manufacture costs are
        implaced. Save updated manufacture costs in WorldData.ManufactureCost. When further processing the function, it
        must be ensured that the trade intertias for export are complemented and the zy-regions removed for the
        operations.
        :param WorldData: World Data Collection
        """

        manu_costs = WorldData.ManufactureCost.data_aligned.iloc[:WorldData.Commodities.df_length *
                                                                  (WorldData.Regions.df_length - 1)]
        manu_costs_zy = WorldData.ManufactureCost.data_aligned.iloc[WorldData.Commodities.df_length *
                                                                    (WorldData.Regions.df_length - 1):]

        updated_manu_costs = pd.DataFrame()
        for commodity in WorldData.Commodities.data[Domains.Commodities.commodity_code]:
            manu_costs_temp = manu_costs[manu_costs[Domains.ManufactureCost.commodity_code] == commodity].copy()
            max_manu_cost_temp = max(manu_costs_temp[Domains.ManufactureCost.net_manufacturing_cost])
            max_elast_temp = max(manu_costs_temp[Domains.ManufactureCost.elasticity_price])
            missing_manu_cost_index = manu_costs_temp[manu_costs_temp[
                                                          Domains.ManufactureCost.net_manufacturing_cost] == 0].index
            manu_costs_temp.loc[missing_manu_cost_index,
                                [Domains.ManufactureCost.net_manufacturing_cost]] = max_manu_cost_temp

            manu_costs_temp.loc[missing_manu_cost_index,
                                [Domains.ManufactureCost.elasticity_price]] = max_elast_temp

            updated_manu_costs = pd.concat([updated_manu_costs, manu_costs_temp], axis=0)

        WorldData.ManufactureCost.data_aligned = pd.concat([updated_manu_costs, manu_costs_zy], axis=0).sort_values(
            by=[Domains.ManufactureCost.region_code, Domains.ManufactureCost.commodity_code]).reset_index(drop=True)

    @staticmethod
    def fill_na(WorldData: InterfaceWorldData):
        """
        Create 0 for all NAN in data_aligned
        :param WorldData: World Data Collection
        :return: new data_aligned for all domains of World Data Collection filled with 0 instead of NAN
        :rtype: pd.DataFrame
        """
        for domain in DomainIterator.get_domain(DomainIterator.ALIGN_DOMAINS):
            domain = str(domain)
            WorldData[domain].data_aligned.fillna(0, inplace=True)

    @staticmethod
    def rename_header(WorldData: InterfaceWorldData):
        """
        removes the column names and replace them with new ones
        :param WorldData: World Data Collection
        """
        for domain_name, rename_dict in DomainIterator.get_domain_header(DomainIterator.FINAL_DOMAINS):
            WorldData[domain_name].data.rename(columns=rename_dict, inplace=True)

    @staticmethod
    def get_world_prices(WorldData: InterfaceWorldData):
        """
        Extract world prices for base period for input data
        :param WorldData: World data collection for world data container
        :return: new attribute "WorldPrices" in world data collection
        :rtype: pd.DataFrame
        """
        world_prices = WorldData.TransportationImport.data_aligned[[
            Domains.TransportationImport.commodity_code, Domains.TransportationImport.price]].iloc[
                       0: WorldData.Commodities.df_length].rename(
            columns={Domains.TransportationImport.price: "WorldPrice"})
        world_price_container = DataContainer("")
        world_price_container.data = world_prices
        WorldData.set_attribute("WorldPrices", world_price_container)

    @staticmethod
    def read_additional_information(WorldData: InterfaceWorldData, AdditionalInfo: AdditionalInformation):
        """
        Read in additional information. If all commodities from input file are captured 
        in additional information than the infos from additional infromation will be loaded.
        If not you got an error massage that you should update the additional information file.
        :param WorldData: World data collection for world data container
        :param AdditionalInfo: Additional Information about commodities, elements and countries
        """
        
        for sheet_name in pd.ExcelFile(AdditionalInfo.filepath).sheet_names:
            if "Commodity_" in sheet_name:
                commodity_data_world = WorldData.Commodities.data
                commodity_data_add_info = DataManager.load_data(AdditionalInfo.filepath, sheet_name, "Excel")
                new_sheet_name = sheet_name.split('_')[0]

                if commodity_data_world['CommodityCode'].astype('int64').equals(
                        commodity_data_add_info['GFPMCom-Code']):
                    AdditionalInfo[new_sheet_name].data = DataManager.load_data(
                        AdditionalInfo.filepath, sheet_name, "Excel")
                    AdditionalInfo[new_sheet_name].update_domain_name(new_sheet_name)

            else:
                AdditionalInfo[sheet_name].data = DataManager.load_data(AdditionalInfo.filepath, sheet_name, "Excel")
                AdditionalInfo[sheet_name].update_domain_name(sheet_name)

            if sheet_name == "CommodityList":
                commodity_intersection = set(AdditionalInfo[sheet_name].data["Commodity Code"]).intersection(
                    WorldData.Commodities.data[Domains.Commodities.commodity_code])
                commodity_indices = [list(AdditionalInfo[sheet_name].data["Commodity Code"]).index(x) for x in
                                     commodity_intersection]
                AdditionalInfo[sheet_name].data = AdditionalInfo[sheet_name].data.loc[commodity_indices]

    @staticmethod
    def add_fao_codes(WorldData: InterfaceWorldData, AdditionalInfo: AdditionalInformation):
        """
        Add corresponding fao codes for gfpm-products and gfpm-regions to Datacontainer Commodities.data and
        Regions.data
        :param WorldData: World data collection
        :param AdditionalInfo: Additional information collection
        """
        WorldData.Commodities.data = WorldData.Commodities.data.merge(
            AdditionalInfo.Commodity.data, left_on="CommodityCode", right_on="GFPMCom-Code",
            how="left")[["CommodityCode", "CommodityName", "FAOCom_Code"]] #TODO Hard code (future work)
        WorldData.Regions.data = WorldData.Regions.data.merge(
            AdditionalInfo.Country.data, left_on="RegionCode", right_on="Country-Code",
            how="left")[["RegionCode", "RegionName", "FAOCou-Code", "ISO-Code"]]#TODO Hard code (future work)

    @staticmethod
    def add_additional_code(WorldData: InterfaceWorldData, AdditionalInfo: AdditionalInformation):
        """
        Add additional FAO-codes for products and countries and ISO3-codes for countries to attributes Commodities and
        Regions of World data collection.
        :param WorldData: World data collection
        :param AdditionalInfo: Additional information collection
        """
        try:
            WorldData.Commodities.data = WorldData.Commodities.data.merge(
                AdditionalInfo.Commodity.data, left_on=[Domains.Commodities.commodity_code], right_on=["GFPMCom-Code"],
                how="left")[[Domains.Commodities.commodity_code, Domains.Commodities.commodity_name, "FAOCom_Code"]]

            WorldData.Regions.data = WorldData.Regions.data.merge(
                AdditionalInfo.Country.data, left_on=[Domains.Regions.region_code], right_on=["Country-Code"],
                how="left")[[Domains.Regions.region_code, Domains.Regions.region_name, "ISO-Code", "FAOCou-Code",
                            VarNames.CONTINENT_COLNAME.value]]
        except TypeError:
            print("\nAddInfoError: complement all information about the product transformation to", 
                  "AdditionalInformation file or set the addinfo flag in userio to false.\n")

    @staticmethod
    def read_world_prices(Data: DataContainer):
        """
        Read world prices from previous scenarios.
        :param Data: Current DataContainer in particular ExogenousChange
        """
        sheet_name = "worldprice" # TODO Hard code (future work)
        Data.data = DataManager.load_data(Data.filepath, sheet_name, "Excel")
        Data.update_domain_name(sheet_name)

    @staticmethod
    def update_period_data_full_copy(WorldData: InterfaceWorldData, period_container: dict, period: int):
        """
        Stores a copy data structure.
        :param WorldData: Current WorldDataContainer
        :param period_container: dict to store data per period
        :param period: current period
        """
        from copy import deepcopy
        period_container[period] = deepcopy(WorldData)

    @staticmethod
    def update_period_data(Data: DataContainer, period: int, accessor: str):
        """
        Finds the period number as a string and displays it, if available.
        :param Data: Current DataContainer in particular ExogenousChange
        :param period: number of current period
        :param accessor: string "period"
        :return: number (int) of the current period
        """
        if "Period" not in Data[accessor].columns or (period == 0):
            Data[accessor]["Period"] = period
            Data.set_attribute("data_periods", Data[accessor].copy())
        else:
            Data[accessor]["Period"] = period
            Data.data_periods = pd.concat([Data.data_periods, Data[accessor].copy()], axis=0)
            Data.data_periods.reset_index(drop=True, inplace=True)

    @staticmethod
    def update_periods(WorldData: InterfaceWorldData, period: int):
        """
        update the current number of period to WorldDataContainer
        :param WorldData: current WorldDataContainer
        :param period: number of current period
        :return: number (int) of current period in pd.DataFrame
        """
        for domain_name in DomainIterator.get_domain_names(DomainIterator.UPDATE_DOMAINS):
            DataManager.update_period_data(WorldData[domain_name], period, accessor="data_aligned")
        DataManager.update_period_data(WorldData.WorldPrices, period, accessor="data")
        DataManager.update_period_data(WorldData["OptimizationHelpers"], period, accessor="data")

    @staticmethod
    def get_period_forecast_data(WorldData: InterfaceWorldData):
        """
        Retrieves information about periods and forecast years from WorldData.ExogenChangeDemand and saves it as dict
        "periods_forecast" to the attribute WorldData.periods_forecast
        :param WorldData: Interface World Data
        """
        _tmp_df = WorldData.ExogChangeDemand.data[["Period", "ForecastYears"]].copy()
        _tmp_df.drop_duplicates(inplace=True)
        _tmp_df.reset_index(drop=True, inplace=True)
        _tmp_df = _tmp_df.convert_dtypes()
        WorldData.periods_forecast = _tmp_df.to_dict("list")

    @staticmethod
    def aggregate_results(WorldData: pd.DataFrame, OptimData: pd.DataFrame, RegionData: pd.DataFrame):
        """
        #TODO rebuild in analysis toolbox (future work)
        Aggregates Optimization results stored in OptimizationHelpers using continental aggregates given in
        AdditionalInformation. Aggregated results are saved as an attribute of OptimizationHelpers ("data_aggregated").
        :param WorldData: World data collection
        :param OptimData: OptimizationHelpers, attribute of world data collection
        :param RegionData: Regions, attribute of world data collection
        """
        try:
            quantity_col_name = VarNames.QUANTITY_COLNAME.value
            price_col_name = VarNames.PRICE_COLNAME.value
            domain_col_name = VarNames.DOMAIN_COLNAME.value
            period_col_name = VarNames.PERIOD_COLNAME.value
            year_col_name = VarNames.YEAR_COLNAME.value
            contionent_col_name = VarNames.CONTINENT_COLNAME.value

            OptimData = OptimData.merge(RegionData[[Domains.Regions.region_code, contionent_col_name]],
                                        left_on=Domains.Regions.region_code, right_on=Domains.Regions.region_code,
                                        how="left")
            OptimData["Value"] = OptimData[quantity_col_name] * OptimData[price_col_name]

            OptimData_agg = pd.concat([
                pd.concat([
                    pd.DataFrame(OptimData.groupby([contionent_col_name, "CommodityCode", domain_col_name, period_col_name,
                                                    year_col_name])[quantity_col_name].sum()),
                    pd.DataFrame(OptimData.groupby([contionent_col_name, "CommodityCode", domain_col_name, period_col_name,
                                                    year_col_name])["Value"].sum() /
                                 OptimData.groupby([contionent_col_name, "CommodityCode", domain_col_name, period_col_name,
                                                    year_col_name])[quantity_col_name].sum())], axis=1),
                pd.concat([
                    pd.concat([pd.DataFrame(OptimData.groupby(["CommodityCode", domain_col_name, period_col_name,
                                                               year_col_name])[quantity_col_name].sum()),
                               pd.DataFrame(OptimData.groupby(["CommodityCode", domain_col_name, period_col_name,
                                                               year_col_name])["Value"].sum() /
                                            OptimData.groupby(["CommodityCode", domain_col_name, period_col_name,
                                                               year_col_name])[quantity_col_name].sum())],
                              axis=1)], keys=["Global"], names=[contionent_col_name])
            ], axis=0).rename(columns={0: "weighted_price"}).reset_index()

            WorldData.OptimizationHelpers.set_attribute("data_aggregated", OptimData_agg)
        except KeyError:
            print("\nAddInfoError: complement all information about the product transformation to", 
                  "AdditionalInformation file or set the addinfo flag in userio to false.\n")

    @staticmethod
    def get_forest_output(WorldData: InterfaceWorldData):
        """
        Build output table for forest from data_periods.
        :param WorldData: World data collection
        """
        forest_output = WorldData.Forest.data_periods[[
            Domains.Forest.region_code,
            VarNames.PERIOD_COLNAME.value,
            Domains.Forest.forest_stock,
            Domains.Forest.forest_area,
            Domains.Forest.gdp_per_capita_base_period,
            Domains.Forest.alpha,
            Domains.Forest.gamma,
            Domains.Forest.periodic_growth_rate_of_forest_area,
            Domains.Forest.fraction_fuelwood,
            Domains.Forest.forest_growth_without_harvest,
            Domains.Forest.supply_from_forest,
        ]]

        WorldData.Forest.set_attribute("forest_output", forest_output)

    @staticmethod
    def get_manufacture_output(WorldData: InterfaceWorldData):
        """
        Build output table for manufacturing from data_periods.
        :param WorldData: World data collection
        """
        manufacture_output = WorldData.ManufactureCost.data_periods[[
            Domains.ManufactureCost.region_code,
            Domains.ManufactureCost.commodity_code,
            VarNames.PERIOD_COLNAME.value,
            Domains.ManufactureCost.net_manufacturing_cost,
            VarNames.RAW_MATERIAL_COST.value,
            VarNames.TOTAL_PRODUCTION_COST.value
        ]]

        WorldData.ManufactureCost.set_attribute("manufacture_output", manufacture_output)

    @staticmethod
    def save_world_prices(WorldData: InterfaceWorldData, WorldPrices: DataContainer, shadow_world_price: pd.DataFrame,
                          present_period: int):
        """
        Build output table for world prices from world price data container.
        :param WorldData: World data collection
        :param WorldPrices: original data of world prices
        :param shadow_world_price: contain shadow price data
        :param present_period: current period
        """      
        if present_period == 0:
            commodity_data = WorldData.Commodities.data["CommodityCode"]
            period_data = pd.DataFrame([present_period] * len(WorldData.Commodities.data)
                                       ).rename(columns={0: "Period"})
            world_price_output = pd.DataFrame(shadow_world_price).rename(columns={0: "WorldPrice"})
            world_price_output = pd.concat([commodity_data, period_data, world_price_output], axis=1)
            WorldPrices.data = world_price_output
        else:
            commodity_data = WorldData.Commodities.data["CommodityCode"]
            period_data = pd.DataFrame([present_period] * len(WorldData.Commodities.data)
                                       ).rename(columns={0: "Period"})
            world_price_output = pd.DataFrame(shadow_world_price).rename(columns={0: "WorldPrice"})
            world_price_output = pd.concat([commodity_data, period_data, world_price_output], axis=1)
            WorldPrices.data = world_price_output.reset_index(drop=True)

    @staticmethod
    def save_model_output(model_data: InterfaceWorldData, time_stamp: str, world_version: str, logger: classmethod,
                          output_path: dict):
        """
        Saves model outputs for each input world as separate csv files and one merged pkl file.
        :param model_data: World data collection
        :param time_stamp: Time stamp of the model start
        :param world_version: Name of the world input file
        :param userIO: Collector of user inputs
        :param logger: Model logger
        :param output_path: dict storing ouput paths for pkl files
        """
        results_output = f"{RESULTS_OUTPUT}{time_stamp}_{world_version[:-5]}.csv"
        results_output_agg = f"{RESULTS_OUTPUT_AGG}{time_stamp}_{world_version[:-5]}.csv"
        forest_output = f"{FOREST_OUTPUT}{time_stamp}_{world_version[:-5]}.csv"
        manufacture_output = f"{MANUFACTURE_OUTPUT}{time_stamp}_{world_version[:-5]}.csv"
        world_price_output = f"{WORLD_PRICE_OUTPUT}{time_stamp}_{world_version[:-5]}.csv"

        results_output = path.abspath(path.join(*Path(__file__).parts[:-2], results_output))
        results_output_agg = path.abspath(path.join(*Path(__file__).parts[:-2], results_output_agg))
        forest_output = path.abspath(path.join(*Path(__file__).parts[:-2], forest_output))
        manufacture_output = path.abspath(path.join(*Path(__file__).parts[:-2], manufacture_output))
        world_price_output = path.abspath(path.join(*Path(__file__).parts[:-2], world_price_output))

        model_data.Forest.forest_output.to_csv(forest_output, index=False)
        model_data.ManufactureCost.manufacture_output.to_csv(manufacture_output, index=False)
        try:
            model_data.OptimizationHelpers.data_aggregated.to_csv(results_output_agg, index=False)
        except AttributeError:
            print("AddInfoError: Aggregated output could not be saved.")
        model_data.OptimizationHelpers.data_periods.to_csv(results_output, index=False)
        model_data.WorldPrices.data_periods.to_csv(world_price_output, index=False)

        data_output = {}
        data_output.update({"Forest": model_data.Forest.forest_output})
        data_output.update({"ManufactureCost": model_data.ManufactureCost.manufacture_output})
        try:
            data_output.update({"data_aggregated": model_data.OptimizationHelpers.data_aggregated})
        except AttributeError:
            print("AddInfoError: Aggregated output could not be saved.")
        data_output.update({"data_periods": model_data.OptimizationHelpers.data_periods})
        data_output.update({"ManufactureCoeff": model_data.ManufactureCoefficients.data_periods})
        data_output.update({"WorldPrices": model_data.WorldPrices.data_periods})

        DataManager.serialize_to_pickle(data_output, output_path["output_path"])
        if os.path.exists(Path(output_path["pkl_output_path"]).parent.absolute()):
            DataManager.serialize_to_pickle(data_output, output_path["pkl_output_path"])
        else:
            logger.info(
                "PKL output path for analysis toolbox doesn't exist, change path in paths.py to save pkl file in"
                " toolbox")

    @staticmethod
    def readin_preprocess(WorldData: InterfaceWorldData, AdditionalInfo: AdditionalInformation ,
                          WorldPrices: DataContainer, UserOptions: ParameterCollector, Logger):
        """
        Calls all methods to read input data.
        :param AdditionalInfo: additional information about countries, comodities and elements
        :param WorldPrices: contain data about world prices
        :param WorldData: World data collection
        """
        DataManager.read_world_prices(WorldPrices)
        DataManager.read_world(WorldData)
        DataManager.drop_sheet_description(WorldData)
        DataManager.split_base_content(WorldData)
        DataManager.verify_base_year(WorldData, UserOptions, Logger)
        DataManager.get_period_forecast_data(WorldData)
        DataManager.rename_header(WorldData)
        DataManager.drop_empty_columns(WorldData)
        DataManager.read_additional_information(WorldData, AdditionalInfo)
        DataManager.specification_preprocess(WorldData, AdditionalInfo)
        DataManager.get_world_prices(WorldData)
        # TODO (future work) 
        # Note: activate add_default_io() to allow originally non-producing countries to produce. default_io are used in
        # create_io_matrix() - Has to be actived in combination with add_missing_manu_costs() to work properly
        # DataManager.add_default_io(WorldData)
        # Note: activate add_missing_manu_costs() to provide manufacture costs to originally non-producing countries
        # DataManager.add_missing_manu_costs(WorldData)
        DataManager.create_io_matrix(WorldData, update=False, default_io=False)

    @staticmethod
    def specification_preprocess(WorldData: InterfaceWorldData, AdditionalInfo: AdditionalInformation):
        """
        Calling functions for data processing and preprocessing of world.xlsx.
        :params WorldData: World data collection
        :params AdditionalInfo: Additional information collection
        """
        DataManager.add_rest_world(WorldData)
        DataManager.get_column_length(WorldData, Domains.Regions)
        DataManager.get_column_length(WorldData, Domains.Commodities)
        DataManager.create_base_matrix(WorldData)
        DataManager.align_df(WorldData)
        DataManager.align_forest(WorldData.Forest, WorldData.ExogChangeForest, WorldData.Commodities)
        DataManager.update_fuelwood_forest_param(WorldData)
        DataManager.fill_na(WorldData)
        DataManager.add_additional_code(WorldData, AdditionalInfo)

    @staticmethod
    def get_additional_output(WorldData: InterfaceWorldData, OptimData: pd.DataFrame, RegionData: pd.DataFrame):
        """
        Generates additional output (aggregated output and forest output). Additional output-dataframes are saved as
        attributes of OptimizationHelpers and Forest
        :param WorldData: World data collection
        :param OptimData: Results from the optimization (OptimizationHelpers) that will aggregated
        :param RegionData: Data of regions used for the aggregation
        """
        DataManager.aggregate_results(WorldData, OptimData, RegionData)
        DataManager.get_forest_output(WorldData)
        DataManager.get_manufacture_output(WorldData)
