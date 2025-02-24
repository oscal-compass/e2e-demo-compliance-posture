
echo "Regenerating assessment results" 

python python/compliance_posture.py --markdown README.md --observations assessment-results/cis_rhel9_scan.oscal.json --software component-definitions/RHEL9-1_0_0/component-definition.json --validation component-definitions/oscap/component-definition.json
