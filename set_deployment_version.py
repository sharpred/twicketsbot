import yaml
import argparse

VERSION_FILE = ".version"

def update_version(deployment_file: str, version_file: str):
    try:
        # Read the version from the .version file
        with open(version_file, "r") as vf:
            new_version = vf.read().strip()

        if not new_version:
            print("Error: .version file is empty.")
            return

        # Read the deployment YAML while preserving formatting
        with open(deployment_file, "r") as file:
            deployment_data = yaml.safe_load(file)

        # Navigate to the containers section
        containers = deployment_data.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

        if not containers:
            print("Error: No containers found in the deployment file.")
            return
        
        # Update the image version for the first container (assuming one container)
        for container in containers:
            if "image" in container:
                image_parts = container["image"].split(":")
                if len(image_parts) == 2:
                    container["image"] = f"{image_parts[0]}:{new_version}"
                    print(f"Updated image version to {new_version} for container {container.get('name', 'unknown')}")
                else:
                    print("Error: Image format does not match expected pattern (registry/image:version)")

        # Write the updated deployment file, preserving formatting
        with open(deployment_file, "w") as file:
            yaml.dump(deployment_data, file, default_flow_style=False, sort_keys=False)

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update image version in a Kubernetes deployment file based on .version.")
    parser.add_argument("deployment_file", nargs="?", default="deployment.yaml", help="Path to the Kubernetes deployment file")
    
    args = parser.parse_args()
    update_version(args.deployment_file, VERSION_FILE)
