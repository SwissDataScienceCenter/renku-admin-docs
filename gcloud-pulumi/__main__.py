import os
import pulumi
import pulumi_kubernetes as k8s
from pulumi_gcp import storage, container, config, compute

from resources import gcp_k8s_context, tiller, renku_helm, gke_cluster, certificate, db

CLUSTER_NAME = "andreas-test-cluster"
MAX_NODE_COUNT = 5
RENKU_NAMESPACE = "andreas-renku"
# Pulumi bypasses tiller, so for a pulumi based
# deployment there is no need for tiller. Enable
# tiller if you want to use helm manually.
DEPLOY_TILLER = True
VALUES_FILE = "./gcloud-values.yaml"
RENKU_DOMAIN = "renku.bleuler.com"


cluster = gke_cluster.deploy_cluster(CLUSTER_NAME, MAX_NODE_COUNT)

db = db.deploy_db()

# Manufacture a GKE-style kubeconfig for the cluster. Note that this is unusual
# because of the way GKE requires gcloud to be in the picture for cluster
# authentication (rather than using the client cert/key directly).
kubeconfig = pulumi.Output.all(
    cluster.name, cluster.endpoint, cluster.master_auth, config
).apply(gcp_k8s_context.render_template)


# Create a Kubernetes provider instance that uses the created kubeconfig.
k8s_provider = k8s.Provider("{}_provider".format(CLUSTER_NAME), kubeconfig=kubeconfig)
provider_opt = pulumi.ResourceOptions(provider=k8s_provider)

# Register a static IP from Google
static_ip = compute.GlobalAddress("globalip")

# Register a Google managed certificate
cert = certificate.create_managed_cert(
    provider_opt, RENKU_NAMESPACE, RENKU_DOMAIN
)

if DEPLOY_TILLER:
    tiller_sa, tiller_crb = tiller.deploy_tiller(provider_opt)


# NOTE: A pulumi based deployment of the Renku helm chart fails because
# of the lack of support for helm hooks: https://github.com/pulumi/pulumi-kubernetes/issues/555
# https://github.com/SwissDataScienceCenter/renku/pull/733 is the way to go...

# values_path = os.path.abspath(VALUES_FILE)
# renku_helm.deploy_renku(provider_opt, static_ip, values_path)
