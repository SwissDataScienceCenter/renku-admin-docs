.EXPORT_ALL_VARIABLES:
ROK_PGP_FP=2E8E3E6447725A15025BD90E859123913F532F3E
ANDREAS_PGP_FP=E05F8E490B6D5305E7D23051B880C4C4CDEB85CF
PAMELA_PGP_FP=FE818AFB977D00CECC07E3A097253E0453A2EA8A
SOPS_PGP_FP=${ROK_PGP_FP},${ANDREAS_PGP_FP},${PAMELA_PGP_FP}

.PHONY: encrypt decrypt values clean

default: decrypt values

encrypt:
	@echo 'Encrypting values for: ${SOPS_PGP_FP}'
	@sops -e unsecured.yaml > secured.yaml
	@echo 'Generated: secured.yaml'

decrypt:
	@echo 'Decrypting values'
	@sops -d secured.yaml > unsecured.yaml
	@echo 'Generated: unsecured.yaml'

values:
	@echo 'Preparing basic-renku-values.yaml and renkulab-gitlab.yaml'
	@scripts/render-values.py --template basic-renku-values.tmpl --values unsecured.yaml --key credentials --output basic-renku-values.yaml
	@scripts/render-values.py --template renkulab-gitlab.tmpl --values unsecured.yaml --key credentials --output renkulab-gitlab.yaml
	@echo 'Generated basic-renku-values.yaml and renkulab-gitlab.yaml'

clean:
	@rm unsecured.yaml basic-renku-values.yaml renkulab-gitlab.yaml
