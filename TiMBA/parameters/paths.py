# Data folder
DATA_FOLDER = r"TiMBA/data/"

# Paths for input files
INPUT_WORLD_PATH = r"input/01_Input_Files/"
ADDITIONAL_INFORMATION_PATH = (
    r"input/02_Additional_Information/additional_information.xlsx")
WORLDPRICE_PATH = r"input/02_Additional_Information/worldprice_world500.xlsx"
PKL_WORLD_PATH = r"input/03_Serialization/WorldDataContent.pkl"
PKL_ADD_INFO_PATH = r"input/03_Serialization/AddInfoContent.pkl"
PKL_WORLDPRICE_PATH = r"input/03_Serialization/WorldPriceContent.pkl"

# Paths for output files
output_name = "results_D"
output_agg_name = "results_aggregated_D"
forest_output_name = "forest_D"
world_price_output_name = "world_prices_D"
manufacture_output_name = "manufacture_D"

LOGGING_OUTPUT_FOLDER = r"output/logs/"
OUTPUT_DIR = r"output/data/"
ADDINFOPTHTOOLBOX = r"input/02_Additional_Information/"

# Input to adress data storage in GIT Repo
GIT_USER="TI-Forest-Sector-Modelling"
GIT_REPO="TiMBA_Additional_Information"
GIT_BRANCH="bilateral_trade_data_cm"
GIT_FOLDER="Input_Data/default_scenario"
DESTINATION_PATH=r"TiMBA/data/input/"

#Paths used in TiMBA_Trade
timba_trade_paths = {
    "SCENARIO_DIR": None,
    "BACI_DIR": ADDINFOPTHTOOLBOX,
    "OUTPUT_DIR": None,
    "LOG_DIR": LOGGING_OUTPUT_FOLDER,
    "scen_name": None,
    "baci_file_name": r"BACI_DATA_as_vector.parquet",
}
