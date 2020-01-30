from jinja2 import Template


def render_template(input_list):
    [name, endpoint, master_auth, config] = input_list
    context = "{}_{}_{}".format(config.project, config.zone, name)
    rendered = CONTEXT_TEMPLATE.render(
        {
            "endpoint": endpoint,
            "cluster_ca_certificate": master_auth["clusterCaCertificate"],
            "context": context,
        }
    )
    return rendered


CONTEXT_TEMPLATE = Template(
    """
        apiVersion: v1
        clusters:
        - cluster:
            certificate-authority-data: {{cluster_ca_certificate}}
            server: https://{{endpoint}}
          name: {{context}}
        contexts:
        - context:
            cluster: {{context}}
            user: {{context}}
          name: {{context}}
        current-context: {{context}}
        kind: Config
        preferences: {}
        users:
        - name: {{context}}
          user:
            auth-provider:
              config:
                cmd-args: config config-helper --format=json
                cmd-path: gcloud
                expiry-key: '{.credential.token_expiry}'
                token-key: '{.credential.access_token}'
              name: gcp
    """,
    trim_blocks=True,
    lstrip_blocks=True,
)
