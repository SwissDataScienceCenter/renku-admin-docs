# os command to helm repo add here
import os
import yaml
import pulumi_kubernetes.helm.v2 as helm


# NOTE: This does currently not work, keep for later reference of how to modify certain
# resources for usage with GKE ingress, managed certs, etc.


def deploy_renku(provider_opt, static_ip, values_path):
    """Deploy the renku helm chart through pulumi"""

    os.system(
        "helm repo add renku https://swissdatasciencecenter.github.io/helm-charts/"
    )

    def remove_type_from_ConfigMap(obj, opts):
        """Remove errounous type from ConfigMap"""
        if obj["kind"] == "ConfigMap" and "type" in obj:
            del obj["type"]

    def ClusterIP_to_NodePort(obj, opts):
        """Turn all services to NodePort"""
        if obj["kind"] == "Service" and obj["spec"].get("type", "") == "ClusterIP":
            obj["spec"]["type"] = "NodePort"

    def remove_nginx_ingress_annotations(obj, opts):
        if obj["kind"] == "Ingress":
            try:
                annotations = obj["metadata"]["annotations"]
                for key in annotations:
                    if "nginx.ingress.kubernetes.io" in key:
                        del annotations[key]

                annotations["kubernetes.io/ingress.global-static-ip-name"] = static_ip
            except KeyError:
                print("Found ingress without annotations...")
                print(obj)

    with open("./gcloud-values.json", "r") as values_file:
        values = yaml.load(values_file, Loader=yaml.FullLoader)
        chartOpts = helm.ChartOpts(
            "renku/renku",
            version="0.5.2",
            namespace="andreas-renku",
            values=values,
            transformations=[
                remove_type_from_ConfigMap,
                ClusterIP_to_NodePort,
                remove_nginx_ingress_annotations,
            ],
        )

    return helm.Chart("renku", chartOpts, opts=provider_opt)
