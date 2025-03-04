import subprocess
import argparse

VERSION_FILE = ".version"

def run_git_command(command):
    """ Run a shell command and handle errors """
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(command)}")
        print(e.stderr)

def commit_and_tag(commit_message):
    """ Add all changes, commit with message, and tag with version """
    # Read version from .version file
    try:
        with open(VERSION_FILE, "r") as vf:
            version = vf.read().strip()
        
        if not version:
            print("Error: .version file is empty.")
            return

        # Run git commands
        run_git_command(["git", "add", "--all"])
        run_git_command(["git", "commit", "-m", commit_message])
        run_git_command(["git", "tag", version])
        run_git_command(["git", "push", "--tags"])

        print(f"Successfully committed and tagged version: {version}")

    except FileNotFoundError:
        print(f"Error: {VERSION_FILE} not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Commit changes and tag with version from .version file.")
    parser.add_argument("commit_message", help="Commit message for the git commit")

    args = parser.parse_args()
    commit_and_tag(args.commit_message)
