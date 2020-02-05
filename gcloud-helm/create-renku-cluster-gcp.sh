#!/bin/bash

#echo "Please make sure you ran: gcloud init --console-only"
echo "*** Activating service account"
gcloud auth activate-service-account  --key-file bash-optical-caldron-265813-23a530269ce6.json

# create the cluster
CLUSTER_NAME="renku-test"
echo "*** Checking if cluster exists"
CLUSTERS=`gcloud container clusters list`
if [[ $CLUSTERS != *$CLUSTER_NAME* ]]; then
  echo "*** Creating cluster, this will take a while..."
  gcloud container clusters create $CLUSTER_NAME --project "optical-caldron-265813" \
   --cluster-version "1.15.7-gke.23" --zone "europe-west4-a" --machine-type "n1-standard-2" \
   --no-enable-autoupgrade --enable-autorepair --no-shielded-integrity-monitoring \
    --num-nodes "2"
   #--enable-autoscaling --min-nodes "1" --max-nodes "3"
  sleep 10
fi

echo "*** Checking if helm is installed"

CHECK=`helm version | tail -1`
if [[ $CHECK != *"Server:"* ]]; then
  # deploy tiller
  echo "*** Tiller not found, deploying helm in the server"
  kubectl apply -f helm-installs/tiller-rbac-config.yaml
  helm init --override 'spec.template.spec.containers[0].command'='{/tiller,--storage=secret,--listen=localhost:44134}' --service-account tiller --upgrade
  CHECK=`helm version | tail -1`
  while [[ $CHECK != *"Server:"*  ]]; do
    echo "*** Waiting for Tiller to be initialized"
    sleep 5
    CHECK=`helm version`
  done
  echo "*** Tiller initialized $CHECK"
fi

echo "*** Checking if letsencrypt is installed"
CHECK=`helm list cert-manager`
if [[ -z $CHECK ]]; then
  # deploy letsencrypt
  echo "*** Deploying letsencrypt"
  kubectl apply -f https://raw.githubusercontent.com/jetstack/cert-manager/release-0.12/deploy/manifests/00-crds.yaml
  #kubectl label namespace kube-system certmanager.k8s.io/disable-validation=true
  kubectl create namespace cert-manager
  helm repo add jetstack https://charts.jetstack.io
  helm repo update
  helm install --name cert-manager --namespace cert-manager jetstack/cert-manager  --version 0.12.0 -f helm-installs/cert-manager-values.yaml
  sleep 10
  echo "*** Creating a cluster issuer"
  kubectl apply -f helm-installs/cert-manager-issuer.yaml
  kubectl get clusterissuer.cert-manager.io
fi

echo "*** Checking if nginx-ingress is installed"
CHECK=`helm list nginx-ingress`
if [[ -z $CHECK ]]; then
  # deploy nginx ingress
  echo "*** Deploying nginx-ingress"
  kubectl create namespace nginx-ingress
  helm install --name nginx-ingress stable/nginx-ingress --namespace nginx-ingress --version 1.29.3 --set rbac.create=true --set controller.publishService.enabled=true
  echo "*** Waiting for nginx-ingress to be initialized and an external IP to be assigned"
  sleep 10
  IP=`kubectl get service nginx-ingress-controller -n nginx-ingress | awk '{print $4}' | tail -1`
  while [[  -z $IP || $IP == *"pending"* ]]; do
    sleep 10
    IP=`kubectl get service nginx-ingress-controller -n nginx-ingress | awk '{print $4}' | tail -1`
  done
else
  IP=`kubectl get service nginx-ingress-controller -n nginx-ingress | awk '{print $4}' | tail -1`
fi

# get IP
echo "*** IP to be used: ${IP}. Please asociate this IP to your domain and enter the domain name (example.com): "
read -ep 'Domain: ' DOMAIN

#DOMAIN=${IP}
#DOMAIN="gcp-renku.get-renga.io"
#INGRESSTLS="gcp-renku-get-renga-io-tls"

INGRESSTLS=`echo ${DOMAIN}-tls | tr . -`
echo "*** Going to use $DOMAIN for Renku configuration and $INGRESSTLS for the Renku ingress."

# deploy renku
echo "*** Deploying Renku"
cp basic-renku-values.yaml renku-values.yaml
sed -i "s/\[domain\]/$DOMAIN/g" renku-values.yaml
sed -i "s/\[ingress-tls\]/$INGRESSTLS/g" renku-values.yaml

helm upgrade --install  renku renku/renku --namespace renku --version 0.5.2 \
 -f renku-values.yaml -f renkulab-gitlab.yaml \
 --timeout 1800 --cleanup-on-fail

echo "*** Congrats! Renku is deployed. To get the keycloak admin password run: kubectl get secrets -n renku keycloak-password-secret -ojsonpath=\"{.data.keycloak-password}\" | base64 --decode"
