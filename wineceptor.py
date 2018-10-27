#!/bin/env python

import configparser
import os
import sys
from typing import Optional

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
        prefix_config = find_prefix_config(prefix)
        executable_config = find_executable_config(executable)

        commands = read_before_commands(executable_config)
        commands += [get_executable_command(
            executable=executable,
            prefix=prefix,
            wine_path=read_wine_path(prefix_config),
            env_variables=read_env_variables(prefix_config) + read_env_variables(executable_config),
            execution_parameters=read_execution_parameters(executable_config),
        )]
        commands += ['env WINEPREFIX="{prefix}" wineserver -w'.format(prefix=prefix)]
        commands += read_after_commands(executable_config)

        command = str.join(" && ", commands)
        print(command)
        # os.system(command)
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


def find_prefix_config(prefix: str) -> Optional[configparser.RawConfigParser]:
    if INI_BASENAME in get_files_in_directory(prefix):
        return read_config(join_file_path(prefix, INI_BASENAME))
    return None


def read_config(config_filename: str) -> configparser.RawConfigParser:
    with open(config_filename) as file:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read_file(file)
        return config


def find_executable_config(executable: str) -> Optional[configparser.RawConfigParser]:
    ini_filename = executable + INI_SUFFIX
    if get_basename(ini_filename) in get_files_in_directory(get_directory(executable)):
        return read_config(ini_filename)
    return None


def read_wine_path(config: configparser.RawConfigParser) -> str:
    if config is None:
        return DEFAULT_WINE_PATH
    try:
        return config.get("WINE", "path")
    except configparser.Error:
        return DEFAULT_WINE_PATH


def read_env_variables(config: configparser.RawConfigParser) -> list:
    if config is None:
        return []
    try:
        items = [
            "{key}={value}".format(key=key, value=value)
            for (key, value) in config.items("ENV")
        ]
        return items
    except configparser.NoSectionError:
        return []


def read_execution_parameters(config: configparser.RawConfigParser) -> str:
    if config is None:
        return ""
    try:
        params = [
            param
            for (_, param) in config.items("EXEC_PARAMS")
        ]
        return str.join(" ", params)
    except configparser.Error:
        return ""


def read_before_commands(config: configparser.RawConfigParser) -> list:
    if config is None:
        return []
    try:
        commands = [
            command
            for (_, command) in config.items("BEFORE")
        ]
        return commands
    except configparser.Error:
        return []


def read_after_commands(config: configparser.RawConfigParser) -> list:
    if config is None:
        return []
    try:
        commands = [
            command
            for (_, command) in config.items("AFTER")
        ]
        return commands
    except configparser.Error:
        return []


def get_executable_command(*,
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
    return command


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
