"""Command Line interface to the konfuzio_sdk package."""

import os
import sys
import json
import logging
import getpass
import tabulate

from tqdm import tqdm

from konfuzio_sdk.api import get_auth_token, get_project_list, create_new_project

sys.tracebacklimit = 0

logger = logging.getLogger(__name__)

CLI_ERROR = """
Please enter a valid command line option.
----------------------------------------
Valid options:
konfuzio_sdk init: inits the konfuzio Package by setting the necessary files
konfuzio_sdk download_data: downloads the data from an example project

These commands should be run inside of your working directory.
"""

SETTINGS_FILE_CONTENT = '''
"""Konfuzio SDK settings."""

import os

from decouple import config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

KONFUZIO_PROJECT_ID = config('KONFUZIO_PROJECT_ID', default=-1, cast=int)
KONFUZIO_HOST = config('KONFUZIO_HOST', default="https://app.konfuzio.com")
KONFUZIO_USER = config('KONFUZIO_USER', default=None)
KONFUZIO_TOKEN = config('KONFUZIO_TOKEN', default=None)
KONFUZIO_DATA_FOLDER = config('KONFUZIO_DATA_FOLDER', default='data')

'''


def init_settings(project_folder):
    """
    Add settings file to the working directory.

    :param project_folder: root folder of the project where to place the settings file
    """
    settings_file = "settings.py"

    with open(os.path.join(project_folder, settings_file), "w", encoding="utf-8") as f:
        f.write(SETTINGS_FILE_CONTENT)


def init_env(project_folder):
    """
    Add the .env file to the working directory.

    :param project_folder: Root folder of the project where to place the .env file
    :return: file content
    """
    user = input("Username you use to login to Konfuzio APP: ")
    password = getpass.getpass("Password you use to login to Konfuzio APP: ")
    host = input("Host from where to get the data (the default is https://app.konfuzio.com): ")

    if host == "":
        host = "https://app.konfuzio.com"

    response = get_auth_token(user, password)
    if response.status_code == 200:
        token = json.loads(response.text)['token']
    else:
        raise ValueError(
            "[ERROR] Your credentials are not correct! Please run init again and provide the correct credentials."
        )

    data_folder = input("Folder where to allocate the data (the default is 'data'): ")
    if data_folder == "":
        data_folder = "data"
    if os.path.exists(f"{project_folder}/{data_folder}"):
        if len(os.listdir(f"{project_folder}/{data_folder}")) != 0:
            print(
                f"The directory: {project_folder}/{data_folder} is not empty."
                f"If you choose to continue, the old data will be deleted permanently.")
            update_data_dir = input("Choose another folder to allocate the data? (Y/N)")
            if update_data_dir == 'Y':
                data_folder = input("Folder where to allocate the data: ")

    with open(os.path.join(project_folder, ".env"), "w") as f:
        f.write("KONFUZIO_HOST = %s" % host)
        f.write("\n")
        f.write("KONFUZIO_USER = %s" % user)
        f.write("\n")
        f.write("KONFUZIO_TOKEN = %s" % token)
        f.write("\n")
        f.write("KONFUZIO_DATA_FOLDER = %s" % data_folder)
        f.write("\n")

    project_list = json.loads(get_project_list(token).text)

    if len(project_list) == 0:
        print("There are no available projects. Creating a new project now...")
        _ = create_project(token)
        project_list = json.loads(get_project_list(token).text)

    print(f"List with all the available projects for {user}:")
    header = ["Project ID", "Project name"]
    rows = [list(x.values())[:2] for x in project_list]
    rows.append([0, '[TO CREATE A NEW PROJECT]'])
    print(f"{tabulate.tabulate(rows, header)}\n")

    project_id = input("ID of the project you want to connect: ")

    if project_id not in [str(row[0]) for row in rows]:
        raise ValueError(
            "[ERROR] The ID that you provided is not valid. Please run init again."
        )

    if int(project_id) == 0:
        print("Creating a new project...")
        project_id = create_project(token)

    with open(os.path.join(project_folder, ".env"), "a") as f:
        f.write("KONFUZIO_PROJECT_ID = %s" % project_id)

    env_file = open(os.path.join(project_folder, ".env"), "r")
    print("[SUCCESS] SDK initialized!")

    return env_file.read()


def init(project_folder="./"):
    """
    Add settings and .env files to the working directory.

    :param project_folder: Root folder of the project
    """
    init_settings(project_folder)
    init_env(project_folder)


def data():
    """
    Download the data from the example project.

    It has to be run after having the .env and settings.py files.
    """
    print("Starting the download. Please wait until the data download is finished..")
    from konfuzio_sdk.data import Project

    training_prj = Project()
    training_prj.update()

    if len(training_prj.documents + training_prj.test_documents) == 0:
        raise ValueError("No documents in the training or test set. Please add them.")

    for document in tqdm(training_prj.documents + training_prj.test_documents):
        document.get_file()
        document.get_images()
    print("[SUCCESS] Data downloading finished successfully!")


def create_project(token=None):
    """Create a new project."""
    project_name = input("Name of the project: ")
    response = create_new_project(project_name, token)
    if response.status_code == 201:
        project_id = json.loads(response.text)["id"]
        print(f"Project {project_name} (ID {project_id}) was created successfully!"
              f"Initializing the environment with the project that was created.")
        return project_id
    else:
        raise Exception(f'The project {project_name} was not created.')


def main():
    """CLI of Konfuzio SDK."""
    cli_options = sys.argv
    _cli_file_path = cli_options.pop(0)  # NOQA

    try:
        first_arg = cli_options.pop(0)
    except IndexError:
        print(CLI_ERROR)
        return -1

    if first_arg == "init":
        init()

    elif first_arg == "download_data":
        data()

    else:
        print(CLI_ERROR)


if __name__ == "__main__":
    main()
