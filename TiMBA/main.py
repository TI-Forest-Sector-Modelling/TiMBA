from TiMBA.main_runner.main_runner import main
from TiMBA.parameters import INPUT_WORLD_PATH, DATA_FOLDER
from TiMBA.logic.model_extensions import run_extensions
from TiMBA.data_management.ParameterCollector import ParameterCollector
from TiMBA.parameters.paths import INPUT_WORLD_PATH,OUTPUT_DIR, ADDINFOPTHTOOLBOX 
from pathlib import Path
import datetime as dt
import os
import warnings
from Toolbox.toolbox import timba_dashboard 
import sys
warnings.simplefilter(action='ignore', category=FutureWarning)
from TiMBA.results_logging.base_logger import close_logger
from TiMBA.parameters.paths import (
    DATA_FOLDER, GIT_USER, GIT_REPO, GIT_BRANCH,
    GIT_FOLDER, INPUT_WORLD_PATH, DESTINATION_PATH,
    ADDINFOPTHTOOLBOX
)
from TiMBA.data_management.Load_Data import load_data

def run_timba(Parameters:dict=None,folderpath:str=None):
    if Parameters is None:
        print("Paramerters need to be set before running TiMBA.",
              "Note: For this simulation standard parameters are used from, ",
              "TiMBA.user_io.default_parameters")
        Parameters = parameter_setter()
    PACKAGEDIR = Path(__file__).parent.parent.absolute()
    if folderpath is None:
            folderpath = PACKAGEDIR
    INPUT_PATH = folderpath / DATA_FOLDER / INPUT_WORLD_PATH
    if os.path.exists(INPUT_PATH):
        pass
    else:
        print("FileNotFoundError at: ",INPUT_PATH)
        print(f"Make sure input data is downloaded to {INPUT_PATH} \nor ",
              "change the folder path where the data is stored.",
              "Note: For this simulation standard input files will be loaded from GitHub",
              f"and saved at {folderpath / DESTINATION_PATH}")
        load_data(
            user=GIT_USER,
            repo=GIT_REPO,
            branch=GIT_BRANCH,
            source_folder=GIT_FOLDER,
            dest_folder=folderpath / DESTINATION_PATH
        )
    world_list = os.listdir(INPUT_PATH)
    for world in world_list:
        try:
            current_dt = dt.datetime.now().strftime("%Y%m%dT%H-%M-%S")
            print("The model starts now:", (dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")),"\n")
            print(f"Path: {folderpath}")
            print(f"Name of input file: {world[:len(world) - 5]} \n")
            print("User input for model settings:\n",
                f"Start year: {Parameters.year}\n",
                f"Number of periods: {Parameters.max_period}\n",
                f"Calculation of prices by: {Parameters.calc_product_prices}\n",
                f"Calculation of world prices by: {Parameters.calc_world_prices}\n",
                f"Material balance: {Parameters.material_balance}\n",
                f"Input data through serialization: {Parameters.serialization}\n",
                f"Dynamization activated: {Parameters.dynamization_activated}\n",
                f"Prices are capped: {Parameters.capped_prices}\n",
                f"Optimization gives verbose logs: {Parameters.verbose_optimization_logger}\n",
                f"TiMBA gives verbose logs: {Parameters.verbose_calculation_logger}\n",
                f"Read additional informations: {Parameters.addInfo}\n")
            main(UserIO=Parameters,
                world_version=world,
                time_stamp=current_dt,
                Data_Path=folderpath / DATA_FOLDER,
                sc_name=world[:len(world) - 5])     
            close_logger()
        except PermissionError:
            pass

    if Parameters.chart_flag:
        world_count = len(world_list)
        SC_FOLDER = Path(DATA_FOLDER) / Path(OUTPUT_DIR)
        ADDINFO_FOLDER = Path(DATA_FOLDER) / Path(ADDINFOPTHTOOLBOX)
        td = timba_dashboard(
            num_files_to_read=world_count,
            FOLDER_PATH=PACKAGEDIR,
            SCENARIO_PATH=SC_FOLDER,
            ADDINFO_PATH=ADDINFO_FOLDER,
        )
        td.run()
    
def parameter_setter():
    from TiMBA.data_management.ParameterCollector import ParameterCollector
    from TiMBA.user_io.default_parameters import user_input
    return ParameterCollector(user_input=user_input)

if __name__ == '__main__':
    Parameters = parameter_setter()
    Parameters.max_period = 1
    Parameters.chart_flag = True
    world_list = run_timba(Parameters=Parameters,folderpath=Path(r"E:/"))
    #run_extensions(UserIO=Parameters)

