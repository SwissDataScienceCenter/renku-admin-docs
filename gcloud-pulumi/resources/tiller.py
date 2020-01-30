import pulumi_kubernetes.core.v1 as core
import pulumi_kubernetes.rbac.v1 as rbac


def deploy_tiller(provider_opt):
    """Deploy tiller in the kube-system namespace of the cluster specified through the
    provider options."""

    tiller_sa = core.ServiceAccount(
        "tiller",
        opts=provider_opt,
        metadata={"namespace": "kube-system", "name": "tiller"},
    )

    tiller_crb = rbac.ClusterRoleBinding(
        "tiller",
        opts=provider_opt,
        role_ref={
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": "cluster-admin",
        },
        subjects=[
            {"kind": "ServiceAccount", "name": "tiller", "namespace": "kube-system"}
        ],
        metadata={"namespace": "kube-system", "name": "tiller"},
    )

    return tiller_sa, tiller_crb
