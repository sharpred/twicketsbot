#!/bin/bash
python set_deployment_version.py k8s/deploymentmain.yaml
python set_deployment_version.py k8s/deploymentcamping.yaml
python git_commit_and_tag.py "updated deployment"