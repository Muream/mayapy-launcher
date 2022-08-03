"""A Launcher for mayapy letting you easily"""
from __future__ import annotations

import itertools
import logging
import os
import platform
import re
import subprocess
import sys
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ClassVar, Iterator

logging.basicConfig()

logger = logging.getLogger(__name__)

__version__ = "0.1.0"

py_to_maya_map = {
    "2.7.11": 2019,
    "2.7.18": 2020,
    "3.7.9": 2022,
    "3.9.7": 2023,
}


@dataclass(order=True)
class Version:
    major: int = 0
    minor: int = 0
    patch: int = 0

    regex: ClassVar[re.Pattern] = re.compile(
        r"(?P<major>\d+)(.(?P<minor>\d+))?(.(?P<patch>\d+))?"
    )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version_str: str) -> Version:
        match = cls.regex.match(version_str)
        version_str.format

        if not match:
            raise ValueError(f"Invalid version string: {version_str}")

        group_dict = match.groupdict()

        major = int(group_dict["major"]) or 0
        minor = int(group_dict["minor"]) or 0
        patch = int(group_dict["patch"]) or 0

        return cls(major, minor, patch)

    @staticmethod
    def distance(version_a: Version, version_b: Version) -> Version:
        """Return a new Version representing the distance between two versions."""
        major = abs(version_a.major - version_b.major)
        minor = abs(version_a.minor - version_b.minor)
        patch = abs(version_a.patch - version_b.patch)

        return Version(major, minor, patch)


def ensure_installed(maya_version: int | None) -> int | None:
    """Returns the maya_version if it is installed, otherwise return None."""
    if maya_version in installed_maya_versions():
        return maya_version
    return None


def parent_dirs(path: str | os.PathLike) -> Iterator[Path]:
    """Generator that yields all the parent paths of this path, including this path."""
    path = Path(path).resolve()
    while True:
        yield path

        if path.parent is path:
            break
        path = path.parent


def maya_install_path(version: int) -> Path | None:
    """Return the path to the maya installation.

    Args:
        version: The Version of maya.

    Returns:
        The path to the maya installation.
    """
    try:
        maya_install_path_key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            f"SOFTWARE\\Autodesk\\Maya\\{version}\\Setup\\InstallPath",
        )
    except FileNotFoundError:
        # Maya version is not installed.
        return None

    maya_install_dir, _ = winreg.QueryValueEx(
        maya_install_path_key,
        "MAYA_INSTALL_LOCATION",
    )

    return Path(maya_install_dir)


def installed_maya_versions() -> list[int]:
    """List all the installed maya versions."""

    maya_versions = []

    # The subkeys of this key are for the most part maya version numbers.
    key = winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        R"SOFTWARE\Autodesk\Maya",
        0,
        winreg.KEY_READ,
    )

    for i in itertools.count():
        try:
            try:
                subkey = winreg.EnumKey(key, i)
                maya_versions.append(int(subkey))
            except ValueError:
                # The subkey exist but is not a maya version
                continue
        except OSError:
            # the subkey doesn't exist, we've reached the end
            break

    return maya_versions


def latest_maya_version() -> int:
    """The latest maya version."""
    return max(installed_maya_versions())


def py_version_from_shebang() -> Version | None:
    """Return the python version from the script's shebang line"""
    return


def py_version_from_virtualenv() -> Version | None:
    """Return the python version of the currently activated virtualenv."""

    virtualenv = os.environ.get("VIRTUAL_ENV")

    if virtualenv is not None:
        logger.debug("Found Virtualenv")
        version = platform.python_version()
        return Version.parse(version)

    return None


def py_version_from_python_version() -> Version | None:
    """Return the first python version from the closest upstream .python-version file."""
    for path in parent_dirs("."):
        for child in path.iterdir():
            if child.name == ".python-version" and child.is_file():
                logger.debug(f"Found .python-version: {child.resolve()}")
                versions = child.read_text().splitlines() or []
                return Version.parse(versions[0])
    return None


def maya_version_from_maya_version() -> int | None:
    """Return the first maya version from the closest upstream .maya-version file."""
    for path in parent_dirs("."):
        for child in path.iterdir():
            if child.name == ".maya-version" and child.is_file():
                logger.debug(f"Found .maya-version: {child.resolve()}")
                versions = child.read_text().splitlines()
                return int(versions[0])
    return None


def pyver_to_mayaver(python_version: Version) -> int | None:
    """Return the most relevant maya version based on the given python version."""
    closest_version = None
    closest_distance = None
    for mayapy_version in py_to_maya_map.keys():
        mayapy_version = Version.parse(mayapy_version)
        distance = Version.distance(python_version, mayapy_version)

        if closest_version is None or closest_distance is None:
            closest_version = mayapy_version
            closest_distance = distance
            continue

        elif distance < closest_distance:
            closest_version = mayapy_version
            closest_distance = distance

    if closest_version is not None:
        same_major = python_version.major == closest_version.major
        same_minor = python_version.minor == closest_version.minor

        if same_major and same_minor:
            maya_version = py_to_maya_map.get(str(python_version))
            maya_version = ensure_installed(maya_version)
            if maya_version is not None:
                return maya_version

    return None


def resolve_version() -> int | None:
    maya_version = None

    py_version_resolvers: list[Callable[[], Version | None]] = [
        py_version_from_shebang,
        py_version_from_virtualenv,
        py_version_from_python_version,
    ]

    for resolver in py_version_resolvers:
        python_version = resolver()
        if python_version is not None:
            maya_version = pyver_to_mayaver(python_version)
            if maya_version is not None:
                logger.debug(f"Starting mayapy from resolver: {resolver.__name__!r}")
                return maya_version

    maya_version_resolvers: list[Callable[[], int | None]] = [
        maya_version_from_maya_version,
        latest_maya_version,
    ]

    for resolver in maya_version_resolvers:
        logger.debug(f"{resolver.__name__!r}")
        maya_version = resolver()
        if maya_version is not None:
            return maya_version

    return None


def mayapy(version: int) -> Path | None:
    """Return the path to the mayapy interpreter.

    Args:
        version: The Maya version.

    Returns:
        The path to the mayapy interpreter
    """
    maya_install_dir = maya_install_path(version)
    if maya_install_dir:
        return maya_install_dir / "bin" / "mayapy.exe"

    return None


def start_mayapy(version: int, args: list[str]) -> None:
    args.insert(0, str(mayapy(version)))
    subprocess.run(args, shell=True, check=True)


def main():
    if os.environ.get("MAYAPY_LAUNCHER_VERBOSE", "False").lower() in ("true", "1", "t"):
        logger.setLevel(logging.DEBUG)

    args = sys.argv[1:]

    version = resolve_version()

    if len(args) > 0:
        try:
            # the version is specified as `-2023` so taking the absolute value
            # of the converted int gives us the expected maya version
            version = abs(int(args[0]))
        except ValueError:
            pass
        else:
            args.pop(0)

    if version is None:
        raise RuntimeError("No valid mayapy version were found.")

    start_mayapy(version, args)


if __name__ == "__main__":
    main()
