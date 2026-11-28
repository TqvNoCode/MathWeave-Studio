"""Windows PE Version Info Resource Generator for MathWeave Studio.

Generates PyInstaller-compatible VSVersionInfo text definitions for both
Standard Onedir and Standalone Portable executables, synchronizing versions
with pyproject.toml.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT_DIR / "pyproject.toml"
BUILD_TOOLS_DIR = ROOT_DIR / "build_tools"


def get_project_version() -> str:
    """Extract project version from pyproject.toml."""
    if not PYPROJECT_PATH.is_file():
        return "0.3.1"
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else "0.3.1"


def get_project_author() -> str:
    """Extract project author from pyproject.toml."""
    if not PYPROJECT_PATH.is_file():
        return "TqvNoCode"
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    authors_match = re.search(r'authors\s*=\s*\[\s*\{\s*name\s*=\s*"([^"]+)"', content)
    if authors_match:
        return authors_match.group(1)
    return "TqvNoCode"


def parse_version_tuple(version_str: str) -> tuple[int, int, int, int]:
    """Convert semver string into 4-integer tuple for Windows FixedFileInfo."""
    parts = re.findall(r"\d+", version_str)
    integers = [int(p) for p in parts[:4]]
    while len(integers) < 4:
        integers.append(0)
    return (integers[0], integers[1], integers[2], integers[3])


def generate_version_text(
    file_version_tuple: tuple[int, int, int, int],
    product_version_tuple: tuple[int, int, int, int],
    file_description: str,
    internal_name: str,
    original_filename: str,
    product_name: str = "MathWeave Studio",
    company_name: str | None = None,
    copyright_str: str | None = None,
) -> str:
    author = get_project_author()
    if company_name is None:
        company_name = author
    if copyright_str is None:
        copyright_str = f"Copyright (C) 2026 {author}. All rights reserved."

    ver_str = ".".join(str(x) for x in file_version_tuple)
    prod_ver_str = ".".join(str(x) for x in product_version_tuple)

    return f"""# UTF-8
# Windows Version Info resource definition for PyInstaller
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={file_version_tuple},
    prodvers={product_version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{company_name}'),
            StringStruct('FileDescription', '{file_description}'),
            StringStruct('FileVersion', '{ver_str}'),
            StringStruct('InternalName', '{internal_name}'),
            StringStruct('LegalCopyright', '{copyright_str}'),
            StringStruct('OriginalFilename', '{original_filename}'),
            StringStruct('ProductName', '{product_name}'),
            StringStruct('ProductVersion', '{prod_ver_str}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    version_str = get_project_version()
    ver_tuple = parse_version_tuple(version_str)

    BUILD_TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    onedir_info = generate_version_text(
        file_version_tuple=ver_tuple,
        product_version_tuple=ver_tuple,
        file_description="MathWeave Studio - Mathematics Learning & Research Application",
        internal_name="mathweave-studio",
        original_filename="mathweave-studio.exe",
    )
    onedir_path = BUILD_TOOLS_DIR / "version_info_onedir.txt"
    onedir_path.write_text(onedir_info, encoding="utf-8")
    print(f"Generated onedir version info: {onedir_path}")

    portable_info = generate_version_text(
        file_version_tuple=ver_tuple,
        product_version_tuple=ver_tuple,
        file_description="MathWeave Studio - Standalone Portable Mathematics Application",
        internal_name="MathWeave-Studio-Portable",
        original_filename="MathWeave-Studio-Portable.exe",
    )
    portable_path = BUILD_TOOLS_DIR / "version_info_portable.txt"
    portable_path.write_text(portable_info, encoding="utf-8")
    print(f"Generated portable version info: {portable_path}")


if __name__ == "__main__":
    main()
