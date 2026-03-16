# -*- coding: utf-8 -*-
#!/usr/bin/env python3

"""
Simple GitHub updater

Shows changed files before committing.

Runs:
    git add .
    git commit
    git push
"""

import subprocess
import sys


def run(cmd):
    """Run shell command"""
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("Error running:", cmd)
        sys.exit(1)


def get_changed_files():
    """Return list of changed files"""
    result = subprocess.run(
        "git status --porcelain",
        shell=True,
        capture_output=True,
        text=True
    )

    files = result.stdout.strip().split("\n")

    if files == [''] or len(files) == 0:
        return []

    return files


def main():

    print("\n🔄 GitHub Update Tool")

    changed = get_changed_files()

    if not changed:
        print("\nNo changes detected. Nothing to commit.")
        return

    print("\nFiles changed:\n")

    for f in changed:
        print("   ", f)

    print("\n----------------------------------")

    msg = input("\nEnter commit message: ").strip()

    if msg == "":
        msg = "update"

    confirm = input("\nProceed with commit and push? (y/n): ")

    if confirm.lower() != "y":
        print("\nCancelled.")
        return

    run("git add .")
    run(f'git commit -m "{msg}"')
    run("git push")

    print("\n✅ GitHub updated successfully.")


if __name__ == "__main__":
    main()