#!/usr/bin/env python3

"""
This script intended to fill the local conan cache with the packages required
for building the project. Clean build scenario requires running this script
before running the cmake command. Besides that, it may be also required after
the dependencies updates.

Usage:
    bootstrap_conan_deps.py [nlc_url]

`nlc_url` is the URL of AdGuard's NativeLibsCommon repository
(defaults to https://github.com/AdguardTeam/NativeLibsCommon.git).
"""

import os
import shutil
import stat
import subprocess
import sys

work_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.dirname(work_dir)
nlc_url = sys.argv[1] if len(sys.argv) > 1 else 'https://github.com/AdguardTeam/NativeLibsCommon.git'
nlc_dir_name = "native-libs-common"
dns_libs_url = 'https://github.com/AdguardTeam/DnsLibs.git'
dns_libs_dir_name = "dns-libs"
nlc_versions = []


def on_rm_tree_error(func, path, _):
    """
    Workaround for Windows behavior, where `shutil.rmtree`
    fails with an access error (read only file).
    So, attempt to add write permission and try again.
    """
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


def remove_dir_if_exists(dir_path):
    """Remove a directory if it exists, handling read-only files on Windows."""
    if os.path.exists(dir_path):
        os.chdir(work_dir)
        shutil.rmtree(dir_path, onerror=on_rm_tree_error)


# Extract version requirements from conanfile.py
with open(os.path.join(project_dir, "conanfile.py"), "r") as file:
    for line in map(str.strip, file.readlines()):
        if line.startswith('self.requires("native_libs_common/') \
                and ('@adguard/oss"' in line):
            nlc_versions.append(line.split('@')[0].split('/')[1])
        elif line.startswith('self.requires("dns-libs/') \
                and ('@adguard/oss"' in line):
            dns_libs_version = line.split('@')[0].split('/')[1]

# Export dns-libs
dns_libs_dir = os.path.join(work_dir, dns_libs_dir_name)
remove_dir_if_exists(dns_libs_dir)
try:
    subprocess.run(["git", "clone", dns_libs_url, dns_libs_dir], check=True)
    os.chdir(dns_libs_dir)

    # Extract NLC versions from dns-libs conanfile.py too
    with open("conanfile.py", "r") as file:
        for line in map(str.strip, file.readlines()):
            if line.startswith('self.requires("native_libs_common/') \
                    and ('@adguard/oss"' in line):
                nlc_versions.append(line.split('@')[0].split('/')[1])

    # Export dns-libs using shell script
    subprocess.run(["bash", os.path.join(dns_libs_dir, "scripts", "export_conan.sh")], check=True)
finally:
    remove_dir_if_exists(dns_libs_dir)

# Export native_libs_common
os.chdir(work_dir)
nlc_dir = os.path.join(work_dir, nlc_dir_name)
remove_dir_if_exists(nlc_dir)
try:
    subprocess.run(["git", "clone", nlc_url, nlc_dir], check=True)
    os.chdir(nlc_dir)

    # Remove duplicates and sort versions
    nlc_versions = sorted(set(nlc_versions))

    for v in nlc_versions:
        subprocess.run(["git", "checkout", "master"], check=True)
        try:
            # Export native_libs_common using shell script
            subprocess.run(["bash", os.path.join(nlc_dir, "scripts", "export_conan.sh")], check=True)
        except Exception as e:
            print(f"Warning: Failed to export version {v}: {e}")
            continue
finally:
    remove_dir_if_exists(nlc_dir)

print("Successfully exported all Conan dependencies")