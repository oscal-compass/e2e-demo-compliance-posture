
all: compliance-posture

compliance-posture:
	python python/compliance_posture.py --markdown README.md --observations assessment-results/ubuntu2404/results.oscal.json --software component-definitions/Ubuntu_Linux_24.04_LTS/component-definition.json --validation component-definitions/oscap/component-definition.json
	
rule-compare:
	python python/rule_compare.py
