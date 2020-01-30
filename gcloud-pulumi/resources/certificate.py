import pulumi_kubernetes as k8s


def create_managed_cert(provider_opt, namespace, domain):
    """Get a mangaged certificate from Google."""

    # Google doesn't support wildcard domains yet and there can be only
    # one domain per certificate :-(
    domains = [domain]

    cert = k8s.apiextensions.CustomResource(
        "renku-certificate",
        api_version="networking.gke.io/v1beta1",
        kind="ManagedCertificate",
        opts=provider_opt,
        metadata={"namespace": namespace, "name": "renku-certificate"},
        spec={"domains": domains},
    )

    return cert
