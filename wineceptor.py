#!/bin/env python

import configparser
import os
import sys

INI_SUFFIX = ".wineceptor.ini"
INI_BASENAME = "wineceptor.ini"
DEFAULT_WINE_PATH = "wine"


def main(args):
    if len(args) < 2:
        print("Usage: {} file.exe".format(args[0]))
        exit(code=0)

    executable = args[1]

    try:
        prefix = find_wine_prefix(executable, max_search_depth=15)

        run_commands_before_executable(executable)
        run_executable(
            executable=executable,
            prefix=prefix,
            wine_path=find_wine_path(prefix),
            env_variables=find_prefix_env_variables(prefix) + find_executable_env_variables(executable),
            execution_parameters=find_execution_parameters(executable),
        )
        run_commands_after_executable(executable)
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
            return directory
        current_depth += 1
        # a directory's directory is same as it's parent directory = go up one level
        directory = get_directory(directory)
    else:
        raise LookupError("Could not find a wine prefix, tried with a {} depth".format(max_search_depth))


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


def find_wine_path(prefix: str) -> str:
    files = [
        get_basename(file)
        for file in get_files_in_directory(prefix)
    ]
    if INI_BASENAME not in files:
        return DEFAULT_WINE_PATH
    with open(join_file_path(prefix, INI_BASENAME)) as file:
        return read_wine_path(file)


def read_wine_path(file) -> str:
    config = configparser.RawConfigParser()
    config.read_file(file)
    try:
        return config.get("WINE", "path")
    except configparser.Error:
        return DEFAULT_WINE_PATH


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
    config.optionxform = str
    config.read_file(file)
    try:
        items = [
            "{key}={value}".format(key=key, value=value)
            for (key, value) in config.items("ENV")
        ]
        return items
    except configparser.NoSectionError:
        return []


def find_execution_parameters(executable: str) -> str:
    directory = get_directory(executable)
    ini_filename = executable + INI_SUFFIX

    files = [
        get_basename(file)
        for file in get_files_in_directory(directory)
    ]
    if get_basename(ini_filename) not in files:
        return ""
    with open(ini_filename) as file:
        return read_execution_parameters(file)


def read_execution_parameters(file) -> str:
    config = configparser.RawConfigParser()
    config.read_file(file)
    try:
        params = [
            param
            for (_, param) in config.items("EXEC_PARAMS")
        ]
        return str.join(" ", params)
    except configparser.Error:
        return ""


def run_commands_before_executable(executable: str):
    directory = get_directory(executable)
    ini_filename = executable + INI_SUFFIX
    files = [
        get_basename(file)
        for file in get_files_in_directory(directory)
    ]
    if get_basename(ini_filename) not in files:
        return
    with open(ini_filename) as file:
        config = configparser.RawConfigParser()
        config.read_file(file)
        try:
            commands = [
                command
                for (_, command) in config.items("BEFORE")
            ]
            for command in commands:
                print("BEFORE:", command)
                os.system(command)
        except configparser.Error:
            pass


def run_executable(*,
                   executable: str,
                   prefix: str,
                   env_variables: list,
                   wine_path: str,
                   execution_parameters: str):
    command = "env WINEPREFIX=\"{prefix}\" {env} {wine} start /unix \"{exe}\" {params}" \
        .format(prefix=prefix,
                exe=executable,
                wine=wine_path,
                env=str.join(" ", env_variables),
                params=execution_parameters)
    print(command)
    os.system(command)


def run_commands_after_executable(executable: str):
    directory = get_directory(executable)
    ini_filename = executable + INI_SUFFIX
    files = [
        get_basename(file)
        for file in get_files_in_directory(directory)
    ]
    if get_basename(ini_filename) not in files:
        return
    with open(ini_filename) as file:
        config = configparser.RawConfigParser()
        config.read_file(file)
        try:
            commands = [
                command
                for (_, command) in config.items("AFTER")
            ]
            for command in commands:
                print("AFTER:", command)
                os.system(command)
        except configparser.Error:
            pass


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
