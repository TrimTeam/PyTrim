"""Utility functions for line-by-line package removal."""

import re
from typing import Set


def remove_package_from_line(
    line: str, unused: Set[str], preserve_trailing_comma: bool = False
) -> str:
    """Remove unused packages from a line while preserving structure."""
    # Check if this line contains a package from unused set (individual
    # package per line)
    for pkg in unused:
        # Create variants of the package name (with hyphens and underscores)
        pkg_variants = {pkg, pkg.replace("-", "_"), pkg.replace("_", "-")}

        for pkg_variant in pkg_variants:
            # Handle individual package lines like: "deepdiff",  or just "deepdiff"
            # (without commas)
            stripped_line = line.strip()

            # If the unused package has extras, match exactly
            if "[" in pkg_variant and "]" in pkg_variant:
                # Exact match for packages with extras
                individual_patterns = [
                    rf'^\s*"{re.escape(pkg_variant)}"\s*,?\s*$',
                    rf"^\s*'{re.escape(pkg_variant)}'\s*,?\s*$",
                    rf"^\s*{re.escape(pkg_variant)}\s*,?\s*$",
                ]
            else:
                # Match lines that are just the package name with optional quotes and
                # trailing comma, including extras and version constraints
                individual_patterns = [
                    # "deepdiff", "deepdiff[extra]", "deepdiff==1.0", or "deepdiff[extra]==1.0"
                    rf'^\s*"{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^"]*"\s*,?\s*$',
                    # 'deepdiff', 'deepdiff[extra]', 'deepdiff==1.0', or 'deepdiff[extra]==1.0'
                    rf"^\s*'{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^']*'\s*,?\s*$",
                    rf"^\s*{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^,\s]*\s*,?\s*$",  # deepdiff, deepdiff[extra], deepdiff==1.0
                ]

            for pattern in individual_patterns:
                if re.match(pattern, stripped_line, re.IGNORECASE):
                    return ""  # Remove the entire line for individual package entries

    if "[" in line and "]" in line:
        # Find the list content
        start = line.find("[")
        end = line.rfind("]") + 1
        prefix = line[:start]
        suffix = line[end:]
        list_content = line[start:end]

        # Process each package in the list
        modified = list_content
        for pkg in unused:
            # Create variants of the package name (with hyphens and underscores)
            pkg_variants = {pkg, pkg.replace("-", "_"), pkg.replace("_", "-")}

            for pkg_variant in pkg_variants:
                # If the unused package has extras, match exactly
                if "[" in pkg_variant and "]" in pkg_variant:
                    # Exact match for packages with extras
                    patterns = [
                        rf'"{re.escape(pkg_variant)}[^"]*"',  # "pkg[extra]" or "pkg[extra]==1.0" etc
                        rf"'{re.escape(pkg_variant)}[^']*'",  # 'pkg[extra]' or 'pkg[extra]==1.0' etc
                        rf"\b{re.escape(pkg_variant)}[^,\]]*",  # pkg[extra] without quotes
                    ]
                else:
                    # Remove variations like "pkg", 'pkg', pkg==1.0, pkg>=2.0, pkg[extras], etc.
                    patterns = [
                        rf'"{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^"]*"',  # "pkg" or "pkg[extras]" or "pkg==1.0" etc
                        rf"'{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^']*'",  # 'pkg' or 'pkg[extras]' or 'pkg==1.0' etc
                        rf"\b{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^,\]]*",  # pkg or pkg[extras] without quotes
                    ]
                for pattern in patterns:
                    # Remove the package and clean up commas
                    modified = re.sub(rf",\s*{pattern}", "", modified, flags=re.IGNORECASE)
                    modified = re.sub(rf"{pattern}\s*,", "", modified, flags=re.IGNORECASE)
                    modified = re.sub(rf"{pattern}", "", modified, flags=re.IGNORECASE)

        # Clean up any double commas or trailing commas
        modified = re.sub(r",\s*,", ",", modified)
        modified = re.sub(r",\s*]", "]", modified)
        modified = re.sub(r"\[\s*,", "[", modified)
        # Clean up extra spaces after opening bracket
        modified = re.sub(r"\[\s+", "[", modified)

        return prefix + modified + suffix

    # Handle key = value assignments like "install_requires = six >= 1.6"
    elif "=" in line and any(pkg in line for pkg in unused):
        original_line = line
        line_modified = False

        # Check if this is a simple key = value assignment
        if "=" in line and not ("[" in line and "]" in line):
            # Look for patterns like "key = package" or "key = package >= version"
            for pkg in unused:
                pkg_variants = {pkg, pkg.replace("-", "_"), pkg.replace("_", "-")}

                for pkg_variant in pkg_variants:
                    if pkg_variant in line:
                        # Pattern for key = package [version constraints]
                        key_value_pattern = (
                            rf"^(\s*[^=]+=\s*){re.escape(pkg_variant)}[^,\s]*(.*)$"
                        )
                        match = re.match(key_value_pattern, line, re.IGNORECASE)
                        if match:
                            # Clear the value part, keeping only the key
                            line = match.group(1).rstrip() + " "
                            line_modified = True
                            break

                if line_modified:
                    break

        # If not modified by the key=value pattern, continue with original comma logic
        if not line_modified:
            for pkg in unused:
                # Create variants of the package name (with hyphens and underscores)
                pkg_variants = {pkg, pkg.replace("-", "_"), pkg.replace("_", "-")}

                for pkg_variant in pkg_variants:
                    line_before = line
                    if pkg_variant.lower() in line.lower():
                        

                        # If the unused package has extras, match exactly
                        if "[" in pkg_variant and "]" in pkg_variant:
                            # Exact match for packages with extras
                            # More precise removal patterns
                            # Handle package with trailing comma (but preserve comma if it's at
                            # end and preserve_trailing_comma is True)
                            if preserve_trailing_comma and line.rstrip().endswith(
                                f"'{pkg_variant}',"
                            ):
                                # Special case: preserve the comma by just removing the package
                                line = re.sub(
                                    rf"'{re.escape(pkg_variant)}[^']*'\s*", "", line, flags=re.IGNORECASE
                                )
                        elif preserve_trailing_comma and line.rstrip().endswith(
                            f'"{pkg_variant}",'
                        ):
                            # Special case: preserve the comma by just removing the package
                            line = re.sub(
                                rf'"{re.escape(pkg_variant)}[^"]*"\s*', "", line, flags=re.IGNORECASE
                            )
                        else:
                            # Standard removal patterns - exact match for extras
                            line = re.sub(
                                rf'"{re.escape(pkg_variant)}[^"]*"\s*,\s*', "", line, flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf"'{re.escape(pkg_variant)}[^']*'\s*,\s*", "", line, flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf',\s*"{re.escape(pkg_variant)}[^"]*"', "", line, flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf",\s*'{re.escape(pkg_variant)}[^']*'", "", line, flags=re.IGNORECASE
                            )

                            # Handle packages without quotes but with commas
                            line = re.sub(
                                rf"\b{re.escape(pkg_variant)}[^,\s\)]*\s*,\s*", "", line, flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf",\s*\b{re.escape(pkg_variant)}[^,\s\)]*", "", line, flags=re.IGNORECASE
                            )

                            # Handle packages at end of line without trailing comma
                            line = re.sub(
                                rf'"{re.escape(pkg_variant)}[^"]*"\s*$', "", line, flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf"'{re.escape(pkg_variant)}[^']*'\s*$", "", line, flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf"\b{re.escape(pkg_variant)}[^,\s\)]*\s*$", "", line, flags=re.IGNORECASE
                            )
                    else:
                        # More precise removal patterns - handle extras like [http2]
                        # Handle package with trailing comma (but preserve comma if it's at
                        # end and preserve_trailing_comma is True)
                        if preserve_trailing_comma and line.rstrip().endswith(
                            f"'{pkg_variant}',"
                        ):
                            # Special case: preserve the comma by just removing the package
                            line = re.sub(
                                rf"'{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^']*'\s*",
                                "",
                                line,
                                flags=re.IGNORECASE
                            )
                        elif preserve_trailing_comma and line.rstrip().endswith(
                            f'"{pkg_variant}",'
                        ):
                            # Special case: preserve the comma by just removing the package
                            line = re.sub(
                                rf'"{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^"]*"\s*',
                                "",
                                line,
                                flags=re.IGNORECASE
                            )
                        else:
                            # Standard removal patterns - handle extras like [http2]
                            line = re.sub(
                                rf'"{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^"]*"\s*,\s*',
                                "",
                                line,
                                flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf"'{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^']*'\s*,\s*",
                                "",
                                line,
                                flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf',\s*"{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^"]*"',
                                "",
                                line,
                                flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf",\s*'{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^']*'",
                                "",
                                line,
                                flags=re.IGNORECASE
                            )

                            # Handle packages without quotes but with commas
                            line = re.sub(
                                rf"\b{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^,\s\)]*\s*,\s*",
                                "",
                                line,
                                flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf",\s*\b{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^,\s\)]*",
                                "",
                                line,
                                flags=re.IGNORECASE
                            )

                            # Handle packages at end of line without trailing comma
                            line = re.sub(
                                rf'"{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^"]*"\s*$',
                                "",
                                line,
                                flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf"'{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^']*'\s*$",
                                "",
                                line,
                                flags=re.IGNORECASE
                            )
                            line = re.sub(
                                rf"\b{re.escape(pkg_variant)}(?:\[[^\]]*\])?[^,\s\)]*\s*$",
                                "",
                                line,
                                flags=re.IGNORECASE
                            )

                    if line != line_before:
                        line_modified = True

        if line_modified:
            # Clean up any leftover double commas, leading/trailing commas
            line = re.sub(r",\s*,", ",", line)
            line = re.sub(r"^\s*,", "", line)  # Remove leading comma

            # Only remove trailing comma if we're not trying to preserve it
            if not preserve_trailing_comma:
                line = re.sub(r",\s*$", "", line)  # Remove trailing comma

            line = re.sub(r",\s*\)", ")", line)
            line = re.sub(r"=\s*\[\s*\]", "= []", line)  # Clean empty lists

            # Special handling for multiline situations - if the line only contains
            # whitespace after package removal, keep original structure
            if line.strip() == "" and original_line.strip() != "":
                return ""  # Remove empty lines

            # If preserve_trailing_comma is requested and we don't have a comma, add one
            if (
                preserve_trailing_comma
                and line.strip()
                and not line.rstrip().endswith(",")
            ):
                line = line.rstrip() + ","

    return line
