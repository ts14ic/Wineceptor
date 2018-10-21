#!/bin/env python

import configparser
import os
import sys

INI_SUFFIX = ".wineceptor.ini"
INI_BASENAME = "wineceptor.ini"


def main(args):
    if len(args) < 2:
        print("Usage: {} file.exe".format(args[0]))
        exit(code=0)

    executable = args[1]

    try:
        prefix = find_wine_prefix(executable, max_search_depth=15)

        execute(
            executable=executable,
            prefix=prefix,
            env_variables=find_prefix_env_variables(prefix) + find_executable_env_variables(executable)
        )
    except Exception as e:
        print("ERROR: {}".format(e))
        exit(code=-1)


def find_wine_prefix(executable, max_search_depth: int) -> str:
    if max_search_depth < 1:
        raise ValueError("Can't use a search depth less than 1, {} was passed".format(max_search_depth))

    directory = get_directory(get_real_path(executable))
    current_depth = 0
    while current_depth < max_search_depth and not is_home_directory(directory):
        if is_prefix_directory(directory):
            break
        current_depth += 1
        directory = get_directory(directory)
    else:
        raise LookupError("Could not find a wine prefix, tried with a {} depth".format(max_search_depth))

    return directory


def is_prefix_directory(directory):
    files = [
        each_file
        for each_file in get_files_in_directory(directory)
        if is_file(join_file_path(directory, each_file))
    ]
    directories = [
        each_directory
        for each_directory in get_files_in_directory(directory)
        if is_directory(join_file_path(directory, each_directory))
    ]
    return "drive_c" in directories and ".update-timestamp" in files


def find_prefix_env_variables(prefix: str) -> list:
    try:
        return _find_env_variables(
            prefix,
            INI_BASENAME,
        )
    except LookupError:
        print("INFO: No env variables found in prefix: " + prefix)
        return []


def find_executable_env_variables(filename: str) -> list:
    try:
        return _find_env_variables(
            get_directory(filename),
            filename + INI_SUFFIX,
        )
    except LookupError:
        print("INFO: No env variables found for file: " + filename)
        return []


def _find_env_variables(directory: str, env_filename: str) -> list:
    files = [
        get_basename(file)
        for file in get_files_in_directory(directory)
    ]
    if get_basename(env_filename) not in files:
        raise LookupError
    with open(join_file_path(directory, env_filename)) as file:
        return read_env_variables(file)


def read_env_variables(file) -> list:
    config = configparser.RawConfigParser()
    config.read(file.name)
    try:
        items = [
            "{key}={value}".format(key=key.upper(), value=value)
            for (key, value) in config.items("ENV")
        ]
        return items
    except configparser.NoSectionError:
        return []


def execute(executable: str, prefix: str, env_variables: list):
    command = "env WINEPREFIX=\"{prefix}\" {env} wine start /unix \"{executable}\"" \
        .format(prefix=prefix,
                executable=executable,
                env=str.join(" ", env_variables))
    # os.system(command)
    print(command)


def get_real_path(executable):
    return os.path.realpath(executable)


def get_directory(file_path: str) -> str:
    return os.path.dirname(file_path)


def get_basename(file_path: str) -> str:
    return os.path.basename(file_path)


def get_files_in_directory(directory: str) -> list:
    return os.listdir(directory)


def is_file(path: str) -> bool:
    return os.path.isfile(path)


def is_directory(path: str) -> bool:
    return os.path.isdir(path)


def is_home_directory(directory):
    return directory == os.path.expanduser("~")


def join_file_path(prefix, filename):
    return os.path.join(prefix, filename)


if __name__ == '__main__':
    main(sys.argv)
