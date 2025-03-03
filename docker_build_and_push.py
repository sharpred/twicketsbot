import yaml
import argparse
import subprocess
import re

def run_command(command):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(command)}")
        print(e.stderr)
        exit(1)

def extract_image_tag(deployment_file):
    """Extract the image tag from a Kubernetes deployment file."""
    with open(deployment_file, "r") as file:
        deployment = yaml.safe_load(file)
    
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for container in containers:
        if "image" in container:
            return container["image"]

    raise ValueError("No image tag found in the deployment file")

def generate_latest_tag(image_tag):
    """Replace the build number in the image tag with 'latest'."""
    return re.sub(r":\d+(\.\d+)*$", ":latest", image_tag)

def main(deployment_file):
    # Extract image tag from deployment file
    tag = extract_image_tag(deployment_file)
    latest_tag = generate_latest_tag(tag)

    print(f"Building Docker image: {tag}")
    run_command(["docker", "build", ".", "-t", tag])

    print(f"Tagging image as latest: {latest_tag}")
    run_command(["docker", "tag", tag, latest_tag])

    print(f"Pushing Docker images: {tag} and {latest_tag}")
    run_command(["docker", "push", tag])
    run_command(["docker", "push", latest_tag])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and push Docker image based on a Kubernetes deployment file.")
    parser.add_argument("deployment_file", help="Path to the Kubernetes deployment YAML file")

    args = parser.parse_args()
    main(args.deployment_file)
