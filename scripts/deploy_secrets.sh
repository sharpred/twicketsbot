#!/bin/bash
kubectl apply -f /secrets/prowl_api_key.yaml
kubectl apply -f secrets/twickets_api_key.yaml
kubectl apply -f secrets/twickets_email.yaml
kubectl apply -f secrets/twickets_password.yaml
