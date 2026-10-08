from urllib.error import URLError
from pathlib import Path
import os
import shutil
import tempfile
import zipfile
import urllib.request


def check_and_load_data(
    user: str,
    repo: str,
    branch: str,
    source_folder: str,
    dest_folder: str,
    check_flag: bool,
    load_flag: bool):

    zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, f"{repo}.zip")
            if load_flag:
                print(f"Load {zip_url} ...")
            urllib.request.urlretrieve(zip_url, zip_path)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)

            repo_root = os.path.join(tmpdir, f"{repo}-{branch}")
            source_path = os.path.join(repo_root, source_folder)
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"Folder {source_folder} not found in {repo}")
            
            # if os.path.exists(dest_folder):
            #    print(f" {dest_folder} already exist and will be overwritten")
            #    try:
            #        shutil.rmtree(dest_folder)
            #    except PermissionError as e:
            #        print(f"PermissionError to remove {e.filename}.",
            #              "Folder will not be overwritten.")
            
            if check_flag:
                source_path = Path(source_path)
                dest_folder = Path(dest_folder)

                source_folders = {
                    path.relative_to(source_path)
                    for path in source_path.rglob("*")
                    if path.is_dir()
                }

                dest_folders = {
                    path.relative_to(dest_folder)
                    for path in dest_folder.rglob("*")
                    if path.is_dir()
                }
                missing_source_folders = sorted(source_folders - dest_folders)
                if not load_flag:
                    return len(missing_source_folders) == 0

            if load_flag:
                try:
                    os.makedirs(os.path.dirname(dest_folder), exist_ok=True)

                    for folder in missing_source_folders:
                        source_folder = source_path / folder
                        destination_folder = dest_folder / folder

                        shutil.copytree(source_folder, destination_folder)

                    # shutil.copytree(source_path, dest_folder)
                    print(f"Input data is saved")
                except FileExistsError:
                    pass
                except PermissionError as e:
                    print(f"PermissionError for {e.filename}.",
                          "File can not be saved at this location.")

    except URLError:
        print(f"Failed to download input data from GitHub.\n",
              "Please check your internet connection, ensure that",
              "'https://github.com' is reachable from your environment and try again.")