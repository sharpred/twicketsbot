import yaml
import re
import argparse

VERSION_FILE = ".version"

def extract_version(deployment_file: str, version_file: str):
    try:
        with open(deployment_file, "r") as file:
            data = yaml.safe_load(file)
        
        # Navigate to the image field
        containers = data.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        for container in containers:
            image = container.get("image", "")
            match = re.search(r":([\d\.]+)$", image)  # Extract version from image tag
            if match:
                version = match.group(1)
                with open(version_file, "w") as vf:
                    vf.write(version + "\n")
                print(f"Version {version} saved to {version_file}")
                return
        
        print("Version not found in deployment file.")
    
    except FileNotFoundError:
        print(f"Error: File '{deployment_file}' not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract build version from a Kubernetes deployment file.")
    parser.add_argument("deployment_file", nargs="?", default="deployment.yaml", help="Path to the Kubernetes deployment file")
    
    args = parser.parse_args()
    extract_version(args.deployment_file, VERSION_FILE)
