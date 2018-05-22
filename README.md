# k8s-switch
Ansible playbook for deploying kubernetes on SWITCHengines

The content of this repository is heavily inspired by
the work from:
- https://cloudblog.switch.ch/2017/06/26/deploy-kubernetes-on-the-switchengines-openstack-cloud/
- https://github.com/infraly/k8s-on-openstack

# Requirements

## Python Requirements
- python (3.6)
- `pip install -r requirements.txt`

## OpenStack Requirements

Access to an OpenStack cluster with enough resources to spawn a handful of VMs (minimum 2), at least two available floating IPs,
the cluster implements LBaaSv2.

It is strongly recommended to use a machine user on OpenStack.
To set this up on SWITCHengines, contact their support (see email: https://help.switch.ch/engines/).

Note: LBaaSv2 is supported on SWITCHengines -> https://cloudblog.switch.ch/2017/06/26/deploy-kubernetes-on-the-switchengines-openstack-cloud/

The last part requires the registration of a domain name.
Without it, we cannot properly set up HTTPS entry points.

# Usage

## A. Prepare OpenStack

Get then credentials file (v3) from the openstack console.
Also, setup an SSH key pair on openstack.

Install openstack client (from `requirements.txt`, or via `pip install python-openstackclient`) and
neutron client `pip install python-openstackclient`.

```bash
$ source ./<project>-openrc.sh
$ openstack
```

```bash
(openstack) network create --enable --internal --description "Network for Kubernetes" kubenet
(openstack) create --subnet-range 192.168.0.0/24 --gateway 192.168.0.254 --ip-version 4 --network kubenet kubesubnet
(openstack) router create --description "Router for Kubernetes" kuberouter
(openstack) router add subnet kuberouter kubesubnet
(openstack) router set --external-gateway public kuberouter
```

We can now populate env.sh:
```
(openstack) image list # select centos
(openstack) floating ip list
(openstack) network list
(openstack) router list
```

## B. Prepare variables
- `source ./env.sh`
- `source ./<project>-openrc.sh`

## C. Run the playbook

The playbook may stop when the VMs have to reboot (timeout).
In that case, simply continue or restart the playbook.

```bash
# Redo this if it fails on VM spawn/reboot
ansible-playbook site-up.yml
```

Edit `admin.conf` to use the master node floating IP in place of something like `server: https://192.168.20.7:6443`.

## D. Create default k8s storage class

```bash
$ export KUBECONFIG=`pwd`/admin.conf
$ kubectl apply -f manifests/storage-class.yml
$ kubectl get sc
NAME                PROVISIONER            AGE
default             kubernetes.io/cinder   6s
```

Set the default StorageClass annotation (https://kubernetes.io/docs/tasks/administer-cluster/change-default-storage-class/):

```bash
$ kubectl edit sc
$ kubectl get sc
NAME                PROVISIONER            AGE
default (default)   kubernetes.io/cinder   47s
```

## E. Setup helm and the ingress controller

Setup helm/tiller (see also:  https://docs.helm.sh/using_helm/#role-based-access-control).
```bash
$ kubectl create -f helm-installs/tiller-rbac-config.yaml
$ helm init --override 'spec.template.spec.containers[0].command'='{/tiller,--storage=secret,--listen=localhost:44134}' --service-account tiller --upgrade
```

Setup the nodes which will run the ingress controller:
```bash
$ kubectl edit node k8s-node-1 # Set a label like `ingress-node="true"`
$ kubectl edit node k8s-node-2 # Set a label like `ingress-node="true"`
```

Install the `nginx-ingress`:
```bash
$ helm upgrade nginx-ingress --namespace kube-system --install stable/nginx-ingress -f helm-installs/nginx-values.yaml
```

Make an OpenStack load balancer:
```bash
$ neutron
(neutron) lbaas-loadbalancer-create --name kubebalancer kubesubnet

# listen on port 80
(neutron) lbaas-listener-create --name kubebalancer-http --loadbalancer kubebalancer --protocol HTTP --protocol-port 80
(neutron) lbaas-pool-create --name kubebalancer-pool-http --lb-algorithm ROUND_ROBIN --listener kubebalancer-http --protocol HTTP
(neutron) lbaas-member-create --subnet kubesubnet --address 192.168.0.5 --protocol-port 32080 kubebalancer-pool-http # use node IPs we labelled
(neutron) lbaas-member-create --subnet kubesubnet --address 192.168.0.9 --protocol-port 32080 kubebalancer-pool-http
(neutron) lbaas-healthmonitor-create --delay 5 --max-retries 2 --timeout 10 --type HTTP --url-path /healthz --pool kubebalancer-pool-http

# listen on port 443
(neutron) lbaas-listener-create --name kubebalancer-https --loadbalancer kubebalancer --protocol HTTPS --protocol-port 443
(neutron) lbaas-pool-create --name kubebalancer-pool-https --lb-algorithm ROUND_ROBIN --listener kubebalancer-https --protocol HTTPS
(neutron) lbaas-member-create --subnet kubesubnet --address 192.168.0.5 --protocol-port 32443 kubebalancer-pool-https # use node IPs we labelled
(neutron) lbaas-member-create --subnet kubesubnet --address 192.168.0.9 --protocol-port 32443 kubebalancer-pool-https
(neutron) lbaas-healthmonitor-create --delay 5 --max-retries 2 --timeout 10 --type HTTPS --url-path /healthz --pool kubebalancer-pool-https

# listen on port 22 - will be used by gitlab
(neutron) lbaas-listener-create --name kubebalancer-ssh --loadbalancer kubebalancer --protocol TCP --protocol-port 22
(neutron) lbaas-pool-create --name kubebalancer-pool-ssh --lb-algorithm ROUND_ROBIN --listener kubebalancer-ssh --protocol TCP
(neutron) lbaas-member-create --subnet kubesubnet --address 192.168.0.5 --protocol-port 32022 kubebalancer-pool-ssh # use node IPs we labelled
(neutron) lbaas-member-create --subnet kubesubnet --address 192.168.0.9 --protocol-port 32022 kubebalancer-pool-ssh
(neutron) lbaas-healthmonitor-create --delay 5 --max-retries 2 --timeout 10 --type TCP --pool kubebalancer-pool-ssh

(neutron) lbaas-loadbalancer-show kubebalancer # Note the port id
```

Let's make the load balancer accessible:
```bash
openstack
(openstack) port set --security-group k8s-balancer <lb-port-uuid> # from field vip_port_id
(openstack) floating ip list # look for a free floating ip
(openstack) floating ip set --port <lb-port-uuid> <available-floating-ip>
```

Let's check we can contact the ingress:
```bash
$ curl -v http://<floating-ip>/
default backend - 404
```

## F. DNS and HTTPS setup

Get a domain name, e.g. `renku.ch` from a registrar.

Create an `A` record pointing to the load balancer and
a wildcard `CNAME` (86.119.40.77 is the floating ip of the load balancer):

| NAME | TYPE | TARGET | TTL |
| ----- | -------- | ----- | -------- |
| internal.renku.ch | A | 86.119.40.77 | 15 min. |
| *.internal.renku.ch | CNAME | internal.renku.ch | 15 min. |

Another example could be:

| NAME | TYPE | TARGET | TTL |
| ----- | -------- | ----- | -------- |
| example.com | A | 86.119.40.77 | 5 min. |
| *.example.com | CNAME | example.com | 5 min. |

Now, we can check the DNS setup:
```bash
$ curl -v http://internal.renku.ch/
default backend - 404
```

Install `cert-manager`:
```bash
$ helm upgrade cert-manager --namespace kube-system --install stable/cert-manager -f helm-installs/cert-manager-values.yaml
$ kubectl apply -f helm-installs/cert-manager-issuer.yaml
```

Check that we can issue certificates automatically, by installing grafana:
```bash
# Replace `grafana.internal.renku.ch` with appropriate value
$ helm upgrade grafana-test --namespace test --install stable/grafana \
--set 'ingress.enabled=true' \
--set 'ingress.hosts[0]=grafana.internal.renku.ch' \
--set 'ingress.tls[0].hosts[0]=grafana.internal.renku.ch' \
--set 'ingress.tls[0].secretName=grafana-test-tls' \
--set 'ingress.annotations.kubernetes\.io/ingress\.class=nginx' \
--set 'ingress.annotations.kubernetes\.io/tls-acme="true"'
```

After a few minutes, you should be able to open  `https://grafana.<domain>` (`https://grafana.internal.renku.ch` in my case).
You can check that the certificate is valid and issued by Let's Encrypt.

We can now remove that deployment:
```bash
$ helm del --purge grafana-test
$ kubectl delete ns test
```
