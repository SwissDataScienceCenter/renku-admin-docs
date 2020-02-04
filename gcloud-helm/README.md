## Create a test deployment of Renku on GCP

The  `create-renku-cluster-gcp.sh` is a script that will create a test cluster and deploy nginx-ingress, cert-manager and Renku using helm.
Note: Currently this deployment is done against renkulab/gitlab, this will be configurable in the future.

### Prerequisites:

* Have `kubectl`, `gcloud` and `helm` installed locally
* Have a domain ready to be configured
* Have a service account keyfile for the script to use
* Create an application on renkulab gitlab. Follow the instructions in [here](https://renku.readthedocs.io/en/latest/developer/example-configurations/renkulab.html), replace the <your-minikube-ip> bits with the domain and use https for the redirect URLs. Copy the application ID and secret and paste them in renkulab-gitlab.yaml

### Further configuration:

* If needed, replace the keyfile name in line 5 of the script
* The cluster name and details can be changed at will
* Make sure there's a `basic-renku-values.yaml` file, you can use `basic-renku-values.tmpl` and replace the secrets (delimited with brackets, e.g. `{global_gitlab_clientSecret}`) either using sops (see Makefile) or manually.

### Deploy Renku in a test cluster

Clone this repo, cd into this directory and run the script:

```
$ ./create-renku-cluster-gcp.sh
```

Right before deploying Renku the script will give you the IP to configure the domain name against and will ask for the domain.

### Post-install configurations

Configure the identity provider according to the [Configure the identity provider section](https://renku.readthedocs.io/en/latest/developer/example-configurations/renkulab.html).
