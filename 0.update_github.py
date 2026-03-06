# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple GitHub updater
Runs:
    git add .
    git commit
    git push

Prompts user for commit message.
"""

import subprocess
import sys


def run(cmd):
    """Run shell command and print output"""
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("Error running:", cmd)
        sys.exit(1)


def main():

    print("🔄 GitHub Update Tool")

    # ask commit message
    msg = input("Enter commit message: ").strip()

    if msg == "":
        msg = "update"

    print("\nUpdating repository...")

    # stage files
    run("git add .")

    # commit
    run(f'git commit -m "{msg}"')

    # push
    run("git push")

    print("\n✅ GitHub updated successfully.")


if __name__ == "__main__":
    main()