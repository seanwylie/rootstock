# Security

## Reporting a vulnerability

Please report privately, so a fix can exist before details are public.

Use GitHub's private vulnerability reporting:
**[open a draft advisory](https://github.com/seanwylie/rootstock/security/advisories/new)**.
That route is preferred over email; there is no published address for this project.

The draft-advisory form only works when
[private vulnerability reporting](https://docs.github.com/code-security/security-advisories/working-with-repository-security-advisories/configuring-private-vulnerability-reporting-for-a-repository)
is enabled on the repository. If the form is missing, do not open a public issue.

Please do not open a public issue for a vulnerability, and please do not post exploit material
in public threads.

**Expect a slow response.** This project is maintained as time permits and carries no
production-support commitment. There is no service-level agreement on triage or fixes.

## What is in scope

- The AWS context guard (`scripts/check_aws_context.py`) refusing the wrong account, the
  `default` profile, ambient static keys, or a non-SSO principal
- A path that lets Terraform or the broker act without that guard
- A default or example configuration that targets a real cloud account
- Accidental persistence of account ids, notification addresses, or credentials in the
  public tree

## What is out of scope

- An operator who copied real account ids into `infra/accounts.json` and then applied
- IAM or organization settings in an account you control
- Model output that is merely surprising
- Live and destructive tests (`-m live`, `-m destructive`) when you chose to run them

## Secrets

Never commit `infra/accounts.json`, `*.tfvars`, `*.tfstate`, or `.env`. The repository
ships `infra/accounts.example.json` and `infra/v0/terraform.tfvars.example` so the suite
and a first `terraform validate` do not need yours.
