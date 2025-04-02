import yaml
import json

with open('3.6.6 Lab/myfile.yaml', 'r') as yaml_file:
    ouryaml = yaml.safe_load(yaml_file)

print(ouryaml)
print("The access token is {}".format(ouryaml['access_token']))
print("The token expires in {} seconds.".format(ouryaml['expires_in']))

print("\n\n")
print(json.dumps(ouryaml, indent=4))
