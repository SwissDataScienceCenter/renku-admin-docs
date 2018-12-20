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

Access to an OpenStack cluster with enough resources to spawn a handful of VMs (minimum 3), 3x 100GBs and at least two available floating IPs.

It is strongly recommended to use a machine user on OpenStack.
To set this up on SWITCHengines, contact their support (see email: https://help.switch.ch/engines/).

Note: LBaaSv2 is supported on SWITCHengines -> https://cloudblog.switch.ch/2017/06/26/deploy-kubernetes-on-the-switchengines-openstack-cloud/

The last part requires the registration of a domain name.
Without it, we cannot properly set up HTTPS entry points.

As minimum resources, we propose:
* 3x nodes (4 cores, 16GBs, 40GBs)
* 3x PVs of 100GB (pv-renku-gitlab, pv-renku-postgresql, pv-renku-tier2)

# Usage

## A. Prepare OpenStack

Get then credentials file (v3) from the openstack console.
Also, setup an SSH key pair on openstack.

Install openstack client (from `requirements.txt`, or via `pip install python-openstackclient`) and
neutron client `pip install python-openstackclient`.

```bash
$ source ./<project>-openrc.sh ## the downloaded version, as explained above
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

## C. Use Rancher to deploy kubernetes, tune machines

Regardless if the resources are raw metal or VMs, the procedure is quite similar;
in the below instructions, k8s is deployed via `rancher`; however any other similar tool would work:
* Bring up the VMs, using centos7. Inspect if they are ready:
   * Ensure `yum upgrade ; yum upgrade kernel` and related commands have been applied and rebooted as needed
   * Ensure kernels across VMs match each other and the output of `rpm -qa` is consistent
   * Ensure /etc/resolv.conf does not have a `search` value, only nameservers listed
   * NTP/DNS should be functional and correct; DO this check NOW.
* Deploy `rancher/2.0` per its installation instructions, on your `master` node
   * single node install is fine for now.
   * familiarize yourself with the rancher interface
* Add k8s cluster via `rancher`, tune `sasl` values and use for network `weave`
   * Save in git repo your rancher yaml file, like in: `20181126-k8s-site-XYZ-prod-rancher-config.yaml`
   * Spin up sufficient number of worker nodes for your cluster.
* Make sure you download the k8s config file and save it as the `admin.conf` in your git repo.
   * T.B.D: Edit `admin.conf` to use the master node floating IP in place of something like `server: https://192.168.20.7:6443`.
* `kubectl get nodes` should return the list of nodes ; Do NOT proceed until this is working fine.

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
# one node at least, more is possible. Not sure if would help scale the network though.
```

Install the `nginx-ingress`:
```bash
$ helm upgrade nginx-ingress --namespace kube-system --install stable/nginx-ingress -f helm-installs/nginx-values.yaml
$ helm upgrade nginx-ingress --namespace kube-system --install stable/nginx-ingress --set controller.hostNetwork=true 
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

Open and edit `helm-installs/cert-manager-issuer.yaml` to fill in the `email` field.
```bash
$ kubectl apply -f helm-installs/cert-manager-issuer.yaml
```

Install `cert-manager`:
```bash
$ helm upgrade cert-manager --namespace kube-system --install stable/cert-manager -f helm-installs/cert-manager-values.yaml
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

## G. Deploy cert-manager

To prevent a potential failure, ensure that the contents of the file `cert-manager-values.yaml` has as follows:
```
---
apiVersion: certmanager.k8s.io/v1alpha1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    # Fill in the admin email for the domain names
    email: your.email@yourdomain.example.com
    http01: {}
    privateKeySecretRef:
      name: letsencrypt-prod
```

It appears that recent cert-manager versions require a trick to get deployed, due to upstream changes:
```bash
$ kubectl apply -f manifests/cert-manager-issuer.yaml
$ helm upgrade --version 0.4.1 --install cert-manager stable/cert-manager -f helm-installs/cert-manager-values.yaml --namespace kube-system
$ helm upgrade --install cert-manager stable/cert-manager -f helm-installs/cert-manager-values.yaml --namespace kube-system
``` 

## H. Setup the PVs & PVCs

```bash
$ ## kubectl apply -f manifests/storage-class.yml ## This is redundant if you have done step D. above.
$ kubectl apply -f renku-pv.yaml
$ kubectl create ns renku
$ kubectl -n renku apply -f renku-pvc.yaml
$ kubectl get pv
$ kubectl get pvc -n renku
$ kubectl describe persistentvolumeclaim -n renku  ## this should not show any error, just PVs ready to be used
```

So, `kubectl describe pvc -n renku` should not give any fault; Do NOT proceed until this is working fine.

## I. Edit file renku-values.yaml

Ensure that inside file `renku-values.yaml` the following are being taken care of:
* `variables_switchboard` section has URLs and DNS names that correspond to your configuration
* `credentials` has its values populated via command `openssl rand -hex 32`, noting that:
   * Use value from `global_jupyterhub_postgresPassword`:  to populate `nb_jupyterhub_hub_db_url`, between `-` and `@` 
   * use `uuidgen` (i.e. a random UUID) for poulating `global_gateway_clientSecret`
*  if you face later on pod scheduling problems (f.i. not enough mem) you may wish to tone down `resources.requests.memory`
* `lfsObjects` & `registry` require to setup your S3 back-ends, so have that configuration handy and in place

## J. Spawn Renku

For convenience, you might wish to monitor the below activity via `watch -d kubectl get po --all-namespaces` (hint: ctrl-Z)

```bash
$ helm init
$ helm repo add renku https://swissdatasciencecenter.github.io/helm-charts/
$ helm fetch --devel renku/renku ## t.b.d.
$ time helm upgrade --install renku renku/renku \
    --namespace renku \
    --version $(cat renku-version.txt) \
    -f renku-values.yaml \
    --timeout 1800    
```

## K. Basic functionality checks

* Create an account via keycloak (/auth), set a password
* Login with said account and verify:
   * You can setup a project (add both title & decsription) ; star it for convenience
   * You can spin up a notebook server and launch a notebook or a terminal
   * You can visit said project under gitlab and kick a pipeline ; if latter fails, some work is missing with `gitlab-runner`
* You should be ready to follow "First Steps" from Renku documentation => Let's do it.

## L. Customizations

You could now consider tuning the following:
* You could now enable 2FA authentication, google recaptcha, login themes etc; see keycloak instructions about these
* You could setup logging & monitoring - via rancher or without ; we are actively checking solutions in this space
* You could attempt integration with nearby resources (HPC sites, other cloud resources, your telescopes etc)
