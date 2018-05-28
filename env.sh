#!/usr/bin/env bash

# SSH Key (name or uuid on OpenStack)
export KEY=

# Deployment name (prefix for VMs)
export NAME=k8s

# VM image uuid
export IMAGE=

# Network uuid (! not the subnet)
export NETWORK=

# Router uuid
export ROUTER_UUID=

# Floating ip uuid
export FLOATING_IP=
# Floating IP address (the IPv4 address of the above)
export MASTER_FLOATING_IP=

# Worker nodes count
export NODE_COUNT=2

# Worker node flavor
export NODE_FLAVOR=n1.large

# Master node flavor
export MASTER_FLAVOR=c1.large

# Set to true to have the master node Hard Drive persisted (openstack volume)
export MASTER_BOOT_FROM_VOLUME=True

# Set to false to keep the master node data even if the VM is deleted
export MASTER_TERMINATE_VOLUME=False

# Size of the master node volume (in GB) when MASTER_BOOT_FROM_VOLUME=True
export MASTER_VOLUME_SIZE=40
