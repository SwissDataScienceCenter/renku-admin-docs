from pulumi_gcp import container


def deploy_cluster(cluster_name, max_node_count):
    """Create an autoscaled gke cluster with a given max size"""

    cluster = container.Cluster(
        cluster_name,
        initial_node_count=1,
        addons_config={"httpLoadBalancing": {"disabled": False}},
        remove_default_node_pool=True,
    )

    container.NodePool(
        "default-autoscaled-pool",
        cluster=cluster.name,
        initial_node_count=1,
        autoscaling={"minNodeCount": 1, "maxNodeCount": 5},
    )

    return cluster
