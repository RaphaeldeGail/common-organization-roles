# common-organization-roles

Scripts to initialize roles and IAM policies for a Google Cloud Organization.

## Roles and IAM policy for Google Cloud

this repository will create the following organization roles and IAM policy for
a given Google Cloud Organization.

### Roles

The following roles will be created:

- Organization Executive (*orgExecutive*)
- Workspace Builder (*workspaceBuilder*)

The *orgExecutive* role will be bound to the *Executive* Google group and
allow high level manipulation of resources, for instance projects, folders, etc.
The *orgExecutive* role nevertheless lacks the permissions to modify the
Organization IAM, as well as to modify or create IAM roles at the
organization scope.
The *workspaceBuilder* grants manipulation for basic resources, for instance
DNS, cryptographic keys, etc.
The *workspaceBuilder* grants permissions to set IAM policies on
resources, unlike the *orgExecutive* role.
The *workspaceBuilder* role is intended to bind to a service account
at the *Workspaces* folder scope, both created by latter script. It will be used
to create, update or delete *Workspaces*.

### IAM policy

In order to define the IAM policy, we declare four groups:

- **admins_group**, a group of administrators,
- **finops_group**, a group of financial operators,
- **policy_group**, a group of policy administrators,
- **executive_group**, a group of executives.

and a backup user:

- **ext_adm_user**, an external user account not belonging to the organization
and used as a backup account.

The following IAM policy will be applied to the organization:

- Administrators group are *organizationAdmin* to administer the organization.
It can specifically change the IAM policy for the whole organization. It also
bears the *organizationRoleAdmin* role to create, update and delete organization
roles,
- FinOps group have full access to all billing accounts used for
the organization, with the *billing.admin* and *organizationViewer* role,
- Policy administrator group can enforce policies at the organization level
with *policyAdmin* and *organizationViewer* roles,
- Executive group can create base resources, projects and folders, ...
at the organization level with the *orgExecutive* role
- the backup account is a backup administrator with the *organizationAdmin* role
and also a contact for the organization with the *essentialcontacts.admin* role.

## Usage of this repository

This repository relies on a python script to create and/or update the roles
and IAM policies described above.

### Pre-requisites

The google groups:

- *Administrators*
- *Policy Administrators*
- *FinOps*
- *Executives*

should already exist before executing the script and should not be empty either.

the Google SDK is necessary for the scripts to authenticate to
the Google API. You can rely on Google Cloud Shell for simplicity.

The setup file *setup.yaml*, containing all the specific data from
the organization should be set at the root of this project and fill with
the following schema:

```yaml
# google part
google:
    organization: string, the organization number
    billing_account: string, the ID of an available billing account
    ext_admin_user: string, the email of a backup account
    groups:
        finops_group: string, the email of the group of FinOps
        admins_group: string, the email of the group of Admins
        policy_group: string, the email of the group of Policy admins
        executive_group: string, the email of the group of Executives
# terraform part
terraform:
    organization: string, the name of the Terraform Cloud organization
    workspace_project: string, the ID of the terraform project for workspaces
```

### The data file

The roles created and IAM policies enforced are both described in the
[*orgData.yaml.j2*](orgData.yaml.j2) Jinja2 template. The file is presented as
a YAML with a list of bindings:

```yaml
  - role: string, the name of the role. if custom role organizations/{org_id}/roles/{role_name}
    title: string, humane readable title for the role.
    description: string, a description for the role.
    stage: string, whether the role is in alpha, beta or GA stage.
    includedPermissions: list, a list of included permissions for the role.
    members: list, a list of principals with access to the role.
```

A binding both describe a role that will be created if it is custom, and
members bound to the role. If the list of members for a role is empty it will
be skipped for the IAM part but the role will still be created if it is custom.

The data file also declares Jinja2 variables as:

- **parent**, the organization name in the form 'organizations/{org_id}'
- **finops_group**, the email of the group of FinOps
- **admins_group**, the email of the group of Admins
- **policy_group**, the email of the group of Policy admins
- **executive_group**, the email of the group of Executives
- **ext_adm_user**, the email of a backup account

and that will be linked to the variables in setup.yaml file.

### Execute the script

With the files:

- setup.yaml
- orgData.yaml

present at the root of the projet, you should be able to launch the script:

```bash
./init.py
```

in an environmnent where Google SDK is installed and you have authenticated.
You can rely on Google Cloud Shell for simplicity.

---
