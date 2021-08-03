from packaging.version import parse
import json
import os
import requests
import subprocess
from time import sleep

apps_path = './apps/'


class repos():
    # Group of repos for fetching version number
    def pypi(repo_strings):
        version = parse('0')

        response = requests.get(repo_strings['url'], timeout=10).json()
        for release in response['releases']:
            if parse(release) > version and not parse(release).is_prerelease:
                version = parse(release)
        return version


def build(name):
    print('Starting build for ' + name + '. This could take some time.')

    # Create required cache directories
    try:
        os.makedirs('/tmp/.buildx-cache/' + name)
        os.makedirs('/tmp/.buildx-cache-new/' + name)
    except Exception:
        # Folder already exists. Continuing.
        pass

    # Build Docker Command and Deploy
    docker_build_command = ('docker buildx build '
                            '--push '
                            '--cache-from=type=local,src=/tmp/.buildx-cache/'
                            + name +
                            ' --cache-to=type=local,mode=max,dest=/tmp/'
                            '.buildx-cache-new/'
                            + name +
                            ' --platform '
                            'linux/amd64,'
                            'linux/arm64,'
                            'linux/arm/v7 '
                            '--tag ghcr.io/learnersblock/' + name.lower() +
                            ':latest '
                            './apps/' + name.lower())

    output = subprocess.Popen(docker_build_command,
                              shell=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True)

    # Print the log output
    while stream_process(output):
        sleep(0.1)

    # Check if process completed ok and if not exit 1
    if (output.returncode != 0):
        raise Exception('Non-zero return code')


def stream_process(process):
    go = process.poll() is None
    for line in process.stdout:
        print(line)
    return go


if __name__ == '__main__':
    print('Running run.py')

    # Set vars
    database = {}

    # Fetch and store main database file as var
    try:
        with open('./database.json', 'r') as jsonFile:
            json_database = json.loads(jsonFile.read())
    except Exception:
        json_database = {}

    # For each folder in the apps folder
    for file_path in sorted(next(os.walk(apps_path))[1]):
        # Create a path to the data.json file
        full_file_path = apps_path + file_path + '/data.json'
        # Read the data.json file
        with open(full_file_path, 'r') as readfile:
            json_data = json.loads(readfile.read())

        # Work with first JSON object which will be the app name
        for i in json_data:
            # Set vars
            existing_entry = False

            # See if it is a new entry for the database
            for item in json_database:
                if i == item:
                    existing_entry = True

            # If it is not an existing entry, build it, then move on
            if existing_entry is False:
                build(i)
                continue

            # Check if repo details exist for auto updates
            if json_data[i]["repo"]["name"]:
                # Store repo name
                repo_call = json_data[i]["repo"]["name"].lower()

                # Call function based on apps repo
                if repo_call == 'pypi':
                    latest_version = repos.pypi(json_data[i]
                                                ["repo"]
                                                ["strings"])
                #                          #
                # else if:                 #
                # Add more repo types here #
                #                          #
                else:
                    # Raise an error if the repo details are wrong
                    raise ('Not a recognised repo')

                # Check if it's a new version or a new entry
                if latest_version > parse(json_data[i]["version"]):
                    # Build Docker image and deploy if it's a LB image
                    if json_data[i]["image"][:21] == 'ghcr.io/learnersblock':
                        build(i)

                    # Update app's JSON file with the new version
                    json_data[i]["version"] = str(latest_version)

                    # Write the app's JSON file
                    with open(full_file_path, 'w') as jsonFile:
                        json.dump(json_data, jsonFile, indent=2)

            # End the loop as only one entry to be processed per file
            break
        # Store the entry for final database file to be used later
        database.update(json_data)

    # Write the final database file
    with open('./database.json', 'w') as jsonFile:
        json.dump(database, jsonFile, indent=2)
