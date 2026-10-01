import os
from typing import Tuple
from pathlib import Path
from .paths import (
    INPUT_WORLD_PATH,
    ADDITIONAL_INFORMATION_PATH,
    WORLDPRICE_PATH,
    EULULUCF_TARGET_PATH,
    PKL_WORLD_PATH,
    PKL_ADD_INFO_PATH,
    PKL_WORLDPRICE_PATH,
    LOGGING_OUTPUT_FOLDER,
    OUTPUT_DIR,
)


def get_pkl_paths(DATA_PATH: Path) -> Tuple[Path, Path, Path]:
    """
    Returns correct paths for and of serialized pkl-files based on user input.
    :param output_path: Folderpath given by user
    :return: tuple of strings being paths
    """
    pkl_world_path = DATA_PATH / PKL_WORLD_PATH
    pkl_add_info_path = DATA_PATH / PKL_ADD_INFO_PATH
    pkl_worldprice_path = DATA_PATH / PKL_WORLDPRICE_PATH
    return pkl_world_path, pkl_add_info_path, pkl_worldprice_path


def get_global_paths(data_path: Path, worldversion: str, UserIO) -> Tuple[Path, Path, Path, Path]:
    """
    Returns correct paths for files based on user input.
    :param data_path: Folderpath given by user
    :return: tuple of strings being paths
    """
    input_world_path = data_path / INPUT_WORLD_PATH / worldversion
    additional_information_path = data_path / ADDITIONAL_INFORMATION_PATH
    worldprice_path = data_path / WORLDPRICE_PATH
    if UserIO.carbon_constraint:
        carbon_constraint_path = data_path / EULULUCF_TARGET_PATH
    if UserIO.carbon_constraint:
        return input_world_path, additional_information_path, worldprice_path, carbon_constraint_path
    else:
        return input_world_path, additional_information_path, worldprice_path


def get_output_paths(Data_Path: Path, time_stamp: str, sc_name: str):
    """
    Collect outpaths for pkl files.
    :param package_dir: absolute folder of the model on any environment.
    :param time_stamp: time stamp from main
    :param sc_name: scenario name from main
    :param PKL_OUTPUT_PATH: path to pkl output
    :return: output paths for the pkl files
    """
    OUTPUT_DIRECTORY = Data_Path / OUTPUT_DIR
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    file_name = str(f"DataContainer_Sc_{sc_name}_{time_stamp}.pkl")
    OUTPUT_PATH = OUTPUT_DIRECTORY / file_name

    return OUTPUT_PATH, OUTPUT_DIRECTORY


__all__ = [
    "get_global_paths",
    "INPUT_WORLD_PATH",
    "ADDITIONAL_INFORMATION_PATH",
    "WORLDPRICE_PATH",
    "LOGGING_OUTPUT_FOLDER"
]
