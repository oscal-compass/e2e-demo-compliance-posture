## Prerequisite
- `Python => 3.11`
- `pip install -r ./python/requirements.txt`

## Compliance to Policy
```
python ./python/compliance_to_policy.py \
  --config ./python/c2p_plugin/config.yaml \
  --component_definition component-definitions/oscap/component-definition.json \
  --out assessment-results/ubuntu2404/results.json
```

## COmpliance Posture
```
python python/compliance_posture.py \
  --markdown README.md \
  --observations assessment-results/ubuntu2404/results.json \
  --software component-definitions/Ubuntu_Linux_24.04_LTS/component-definition.json \
  --validation component-definitions/oscap/component-definition.json
```