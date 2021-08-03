from packaging.version import parse
import json
import os
import requests
import subprocess

apps_path = './apps/'


class repos():
    def pypi(repo_strings):
        version = parse('0')

        response = requests.get(repo_strings['url']).json()
        for release in response['releases']:
            if parse(release) > version and not version.is_prerelease:
                version = parse(release)

        return version


def build(name):
    print('Starting build for ' + name + '. This could take some time.')
    # Build Docker Command and Deploy
    docker_build_command = ('docker buildx build '
                            '--push '
                            '--platform '
                            'linux/amd64,linux/arm64,'
                            'linux/ppc64le,linux/s390x,linux/386,'
                            'linux/arm/v7,'
                            'linux/arm/v6 '
                            '--tag ghcr.io/learnersblock/' + name.lower() +
                            ':latest '
                            './apps/' + name.lower())

    output = subprocess.Popen(docker_build_command,
                              shell=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True)

    output.wait()

    # Print the log output
    print(output.communicate()[0].rstrip())

    # Check if process completed ok and if not exit 1
    if (output.returncode != 0):
        raise Exception('Non-zero return code')


if __name__ == '__main__':
    print('Running run.py')

    database = {}
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
            # Set variables
            existing_entry = False

            # See if it is a new entry for the database
            for item in json_database:
                if i == item:
                    existing_entry = True

            # Check to see if there are build steps required and if not skip
            if not json_data[i]["repo"]["name"]:
                continue

            # Fetch the latest version for it's repo
            repo_call = json_data[i]["repo"]["name"].lower()

            if repo_call == 'pypi':
                latest_version = repos.pypi(json_data[i]["repo"]["strings"])
            #                          #
            # Add more repo types here #
            #                          #
            else:
                raise Exception('Not a recognised repo')

            # Check if it's a new version or a new entry
            if latest_version > parse(json_data[i]["version"]) or \
                    existing_entry is False:
                # Build Docker image and deploy
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
