#!/usr/bin/python

from google.auth import default
from googleapiclient.discovery import build
from yaml import safe_load
from os.path import basename
from os import environ
from jinja2 import Environment, select_autoescape, FileSystemLoader
from schema import Schema, SchemaError

# set global variables
## the schema for the setup file in YAML
config_schema = Schema({
    "google": {
        "organization": str,
        "billing_account": str,
        "ext_admin_user": str,
        "groups": {
            "finops_group": str,
            "admins_group": str,
            "policy_group": str,
            "executive_group": str
        }
    },
    "terraform": {
        "organization": str,
        "workspace_project": str
    }
})
## the scopes for all google API calls
scopes = ['https://www.googleapis.com/auth/cloud-platform']
## the path of the file with full template for the organization
data_file = 'orgData.yaml.j2'

# set the clients for google API role and IAM policy
# WARNING: the quota_project_id can not be set when calling the credentials
# default() method and has to be explicitly overidden with
# the with_quota_project(None) method.
cred = default(scopes=scopes)[0].with_quota_project(None)
role_api = build('iam', 'v1', credentials=cred).organizations().roles()
org_api = build('cloudresourcemanager', 'v3', credentials=cred).organizations()

def create_role(parent, body):
    """
    Create an organization role with google API call.

    Args:
        parent: string, the organization ID.
        body: dict, the role to be created.

    Returns:
        dict, the role created.

    Raises:
        Exception: Raises an exception if the API call fails.
    """
    request = role_api.create(parent=parent, body=body)
    try:
        response = request.execute()
    except Exception as err:
        raise err('Creation request failed.')
    return response

def update_role(role_id, body, mask):
    """
    Update an organization role with google API call.

    Args:
        role_id: string, the name of the role.
        body: dict, the role to be updated.
        mask: string, a comma-separated list with entries that will be updated.

    Returns:
        dict, the role updated.

    Raises:
        Exception: Raises an exception if the API call fails.
    """
    request = role_api.patch(name=role_id, body=body, updateMask=mask)
    try:
        response = request.execute()
    except Exception as err:
        raise err('Update request failed.')
    return response

def update_org_policy(parent, body):
    """
    Update an organization IAM policy with google API call.

    Args:
        parent: string, the organization ID.
        body: dict, the policy to be updated.

    Returns:
        dict, the policy updated.

    Raises:
        Exception: Raises an exception if the API call fails.
    """
    request = org_api.setIamPolicy(resource=parent, body=body)
    try:
        response = request.execute()
    except Exception as err:
        raise err('Update request failed.')
    return response

def set_role(role_id, role_data):
    """
    Set a role according to the role_data. Can either be create, update
    or leave it as it is.

    Args:
        role_id: string, the name of the role in 
            the form organizations/{orgId}/roles/{roleName}
        role_data: dict, the role to be set.

    Returns:
        dict, the result role.
    """
    role_name = basename(role_id)
    # the role_id is of the form organizations/{org_id}/roles/{role_name}
    parent = role_id.split("/roles")[0]
    print(
        '[{role}] setting up... '.format(role=role_id.replace('/',':')),
        end=''
    )

    request = role_api.get(name=role_id)
    try:
        result_role = request.execute()
    except:
        print('the role will be created... ', end='')
        body = { "role": role_data, "roleId": role_name }
        result_role = create_role(parent=parent, body=body)
        if result_role is None:
            print('[ERROR] role creation failed')
            return None
        print('role successfully created.')
        return result_role
    # role_data is the declared data with extended entries
    role_data.update({ "name" : role_id, "etag": result_role['etag'] })
    # when the new role has differences, they will be applied.
    if not role_data == result_role:
        print('the role will be updated... ', end='')
        mask = ''
        for key in role_data.keys():
            if not role_data[key] == result_role[key]:
                mask += ',{key}'.format(key=key)
        mask = mask.replace(',','',1)
        print('[mask:{mask}]'.format(mask=mask), end='')
        result_role = update_role(role_id=role_id, body=role_data, mask=mask)
        if result_role is None:
            print('[ERROR] role update failed')
            return None
        print('role succesfully updated.')
        return result_role
    # if the role exists and is already up-to-date, nothing is done.
    print('the role is already up-to-date.')
    return result_role

# define the function to update the organization policy.
def set_org_policy(parent, policy_data):
    """
    Set the organization IAM policy according to the policy_data. Can either be
    create, update or leave it as it is.

    Args:
        parent: string, the organization name as 'organizations/{org_id}'.
        policy_data: list, the policy bindings to be set.

    Returns:
        dict, the result policy.
    """
    print(
        '[{org}] setting up... '.format(org=parent.replace('/',':',1)),
        end=''
    )

    result_policy = org_api.getIamPolicy(resource=parent).execute()
    policy = {
        "policy": {
            "bindings": policy_data,
            "etag": result_policy['etag'],
            "version": 1,
         }
    }
    # if the new policy has differences, thy will be applied.
    if not result_policy['bindings'] == policy['policy']['bindings']:
        print('the org policy will be updated... ', end='')
        result_policy = update_org_policy(parent=parent, body=policy)
        if result_policy is None:
            print('[ERROR] org policy update failed')
            return None
        print('org policy succesfully updated.')
        return result_policy
    # when the policy is already up-to-date, nothing is done.
    print('the org policy is already up-to-date.')
    return result_policy

# load the environment from setup.yaml
with open('setup.yaml', 'r') as f:
    setup = safe_load(f)
# validate the setup YAML against the schema
try:
    config_schema.validate(setup)
except SchemaError as se:
    raise se

# the organization number
org_id = setup['google']['organization']
## the organization name as string 'organizations/{org_id}'
parent = 'organizations/{org_id}'.format(org_id=org_id)
## global organization setup data from the jinja template.
env = Environment(
    loader=FileSystemLoader(searchpath='.'),
    autoescape=select_autoescape()
)
bindings = safe_load(
    env.get_template(data_file).render(
        parent=parent,
        finops_group=setup['google']['groups']['finops_group'],
        admins_group=setup['google']['groups']['admins_group'],
        policy_group=setup['google']['groups']['policy_group'],
        executive_group=setup['google']['groups']['executive_group'],
        ext_adm_user=setup['google']['ext_admin_user']
    )
)
# Create or modify the roles according to the organization setup data.
for binding in bindings['bindings']:
    if binding['role'].startswith(parent):
        role_data = {
            "description": binding['description'],
            "includedPermissions": binding['includedPermissions'],
            "stage": binding['stage'],
            "title": binding['title'],
        }
        set_role(role_id=binding['role'] ,role_data=role_data)
# Modify the organization policy, if necessary.
policy_data = [
    { 'role': binding['role'], 'members': binding['members'] }
    for binding in bindings['bindings'] if not binding['members'] == []
]
set_org_policy(parent=parent, policy_data=policy_data)