#!/bin/bash
set -e

echo "Deploying in-cluster Git server..."
kubectl apply -f k8s/infrastructure/git-server.yaml

echo "Adding ArgoCD Helm repository..."
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

echo "Installing ArgoCD..."
helm upgrade --install argocd argo/argo-cd \
  --namespace default \
  --set server.extraArgs="{--insecure}"

echo "Waiting for ArgoCD server to be ready..."
kubectl wait --for=condition=available deployment/argocd-server -n default --timeout=300s

echo "Applying ArgoCD application manifest..."
kubectl apply -f k8s/infrastructure/argocd-app.yaml

echo -e "\nGitOps infrastructure deployed successfully!"
echo "You can access ArgoCD UI by port-forwarding:"
echo "kubectl port-forward svc/argocd-server -n default 8080:80"
