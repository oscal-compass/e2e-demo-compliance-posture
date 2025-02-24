#!/bin/bash

CHANGES=`git diff-tree --no-commit-id --name-only -r HEAD`

ar_changed=false

ar1=$"^assessment-results/"
ar2=$"\.json$"

for val in ${CHANGES[@]} ; do
  if [[ $val =~ $ar1 && $val =~ $ar2 ]]; then
    ar_changed=true
  fi
done

if [[ $ar_changed = true ]]; then
    echo "assessment results changed, regenerating compliance posture..."
    ./scripts/automation/regenerate_compliance_posture.sh
fi

echo "$ar_changed"
