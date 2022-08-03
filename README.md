# Mayapy Launcher

Mayapy Launcher is a launcher similar to the Py Launcher on windows but for mayapy.  
It lets you easily launch any version of mayapy without having any of them in your PATH.

## Installation

### Using pipx

```console
pipx install mayapy-launcher
```

### Or just pip

```console
pip install mayapy-launcher
```


## Usage

### Just run it

Simply run mayapy in your terminal.

```console
mayapy
```

When called without a specific version number the version is resolved in this order:

1. If a virtualenv is currently active, the Launcher will check `python --version` and use the most relevant interpreter [^1].

2. The Launcher will look for a `.maya-version` file in all parent directories and use the first version it specifies

    ```plaintext
    # .mayapy-version
    2023
    ```

3. The Launcher will look for a `.python-version` file in all parent directories and match the first python version with the most relevant mayapy version[^1].  

    ```plaintext
    # .python-version
    3.9.7
    ```

    The Interpreter **MUST** share the same major version.
    Only interpreters with the same or greater minor version are considered.  
    This means that python2 interpreters will never be run

4. latest installed version will automatically be used.


### Run a specific version

You can run any version of mayapy by passing the version as the first parameter

```console
mayapy -2023
```

### Passing parameters to the interpreter

All parameters that don't match a version number are passed directly to the interpreter that gets spawned.

```console
mayapy -2023 my_file.py
```

[^1]: The most relevant mayapy interpreter is resolved with a few rules:
    1. It **must** share the same Major version as the python version.
        This means no Python 3 interpreter can be used to run python 2 code [et vice et versa](https://youtu.be/ZTeqM5gciH8).
    2. If specified, the minor version must match the python version as well.
    3. Since we don't have a release for every python version, the closest patch version will be used.
