import subprocess
import sys

def run_git(args):
    print(f"Running: git {' '.join(args)}")
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing git {' '.join(args)}:")
        print(result.stdout)
        print(result.stderr)
        return False
    print(result.stdout)
    return True

def main():
    if not run_git(["add", "jaros/", ".jarify/", "tests/", "scripts/", "Dockerfile", "pyproject.toml", "README.md", ".gitignore", "docs/"]):
        sys.exit(1)
    if not run_git(["commit", "-m", "feat: contain status write exceptions to prevent daemon crashes"]):
        sys.exit(1)
    print("Success: Committed all updates successfully.")

if __name__ == "__main__":
    main()
