import json
import os
import requests
import shutil
import subprocess
from datetime import datetime
from packaging.version import parse
from time import sleep

apps_path = './apps/'


# Repos for fetching latest version number
class repos():
    # Run at a set interval
    def cron(repo_strings):
        if datetime.today().weekday() != repo_strings['dow']:
            # Fetch release versions
            response = requests.get(repo_strings['url'], timeout=10).json()
            return True, response['object']['sha'][:7]
        else:
            return False, False

    # Check for new commits on a GitHub repo
    def gh_commits(repo_strings, cache_folder):
        # Fetch release versions
        response = requests.get(repo_strings['url'], timeout=10).json()

        # Read cached sha
        try:
            with open(cache_folder + '/cache.json', 'r') as jsonFile:
                cache = json.loads(jsonFile.read())
        except Exception:
            with open(cache_folder + '/cache.json', 'w') as jsonFile:
                json.dump({"sha": "new_entry"}, jsonFile, indent=2)

            cache = {"sha": "new_entry"}

        # Check if new commit
        if response['object']['sha'] != cache['sha']:
            # Update and write new sha
            cache["sha"] = response['object']['sha']

            # Write new cache
            with open(cache_folder + '/cache.json', 'w') as jsonFile:
                json.dump(cache, jsonFile, indent=2)

            # Return new version number as version object
            return True, cache["sha"][:7]
        else:
            return False, cache["sha"][:7]

    # Check for new releases on a GitHub repo
    def gh_release(repo_strings, cache_folder):
        # Fetch release versions
        response = requests.get(repo_strings['url'], timeout=10).json()

        # Read release data
        try:
            with open(cache_folder + '/cache.json', 'r') as jsonFile:
                cache = json.loads(jsonFile.read())
        except Exception:
            with open(cache_folder + '/cache.json', 'w') as jsonFile:
                json.dump({"tag_name": "new_entry"}, jsonFile, indent=2)

            cache = {"tag_name": "new_entry"}

        # Check if new commit
        if response['tag_name'] != cache['tag_name'] and \
            response['prerelease'] is False and \
                response['draft'] is False:

            # Write new cache
            with open(cache_folder + '/cache.json', 'w') as jsonFile:
                json.dump({"tag_name": response['tag_name']},
                          jsonFile,
                          indent=2)

            # Return new version number as version object
            return True, response['tag_name']
        else:
            return False, response['tag_name']

    # Check for new releases on PyPi.org
    def pypi(repo_strings, current_version):
        # Set vars
        version_name = parse('0')
        new = False

        # Fetch latest commit
        response = requests.get(repo_strings['url'], timeout=10).json()

        # For each release in PyPi find the most recent
        for release in response['releases']:
            if parse(release) > version_name and not \
                    parse(release).is_prerelease:
                version_name = parse(release)

        if version_name > parse(current_version):
            new = True

        # Return the most recent version
        return new, version_name


def build(name):
    print(f"Starting build for {name}. This could take some time.")

    # Set vars
    cache_from = f"/tmp/.buildx-cache/{name}"
    cache_to = f"/tmp/.buildx-cache-new/{name}"

    # Create required cache directories in case not there
    try:
        os.makedirs(cache_from)
    except Exception:
        # cache_from folder already exists. Continuing.
        pass

    try:
        os.makedirs(cache_to)
    except Exception:
        # cache_to folder already exists. Continuing.
        pass

    # Build Docker Command and Deploy
    docker_build_command = ('docker buildx build '
                            '--push '
                            f"--cache-from=type=local,src={cache_from} " +
                            f"--cache-to=type=local,mode=max,dest={cache_to}" +
                            ' --platform '
                            'linux/amd64,'
                            'linux/arm64,'
                            'linux/arm/v7 '
                            f"--tag ghcr.io/learnersblock/{name.lower()}" +
                            ':latest '
                            f"./apps/{name.lower()}")

    output = subprocess.Popen(docker_build_command,
                              shell=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True)

    # Print the log output
    while stream_progress(output):
        sleep(0.1)

    # Check if process completed ok and if not exit 1
    if (output.returncode != 0):
        raise Exception('Non-zero return code')

    # Check cache exists and move into place
    if any(os.scandir(cache_to)):
        shutil.rmtree(cache_from)
        shutil.move(cache_to, cache_from)


def stream_progress(progress):
    go = progress.poll() is None
    for line in progress.stdout:
        print(line)
    return go


if __name__ == '__main__':
    print("Running Learner's Block App-Store Update.")

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
        for app_json_file in json_data:
            # Set vars
            existing_entry = False

            # See if it is a new entry for the database
            for item in json_database:
                if app_json_file == item:
                    existing_entry = True

            # If it is not an existing entry, build it, then move on
            if existing_entry is False and \
                (json_data[app_json_file]["image"][:21]) \
                    == 'ghcr.io/learnersblock':
                build(app_json_file)
                continue

            # Check if repo details exist for auto updates
            if json_data[app_json_file]["repo"]["name"]:
                # Store repo name
                repo_call = json_data[app_json_file]["repo"]["name"].lower()

                # Call function based on apps repo
                if repo_call == 'cron':
                    new, version_name = repos.cron(json_data
                                                   [app_json_file]
                                                   ["repo"]
                                                   ["strings"])

                elif repo_call == 'gh_commits':
                    new, version_name = repos.gh_commits(json_data
                                                         [app_json_file]
                                                         ["repo"]
                                                         ["strings"],
                                                         apps_path + file_path)
                elif repo_call == 'gh_release':
                    new, version_name = repos.gh_release(json_data
                                                         [app_json_file]
                                                         ["repo"]
                                                         ["strings"],
                                                         apps_path + file_path)
                elif repo_call == 'pypi':
                    new, version_name = repos.pypi(json_data[app_json_file]
                                                   ["repo"]
                                                   ["strings"],
                                                   json_data
                                                   [app_json_file]
                                                   ["version_name"])
                #                          #
                # elif:                    #
                # Add more repo types here #
                #                          #
                else:
                    # Raise an error if the repo details are wrong
                    raise ('Not a recognised repo')

                # Check if it is a new version or a new entry
                if new is True:
                    # Build Docker image and deploy if it's an LB image
                    if (json_data[app_json_file]["image"][:21]
                            == 'ghcr.io/learnersblock'):
                        build(app_json_file)

                    # Update app's JSON with the new version
                    json_data[app_json_file]["version_name"] = \
                        str(version_name)
                    json_data[app_json_file]["version"] = \
                        int(json_data[app_json_file]["version"])+1

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

    print("Learner's Block App-Store update complete.")
