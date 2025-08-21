#!/bin/bash

date=$(date '+%Y-%m-%d')
mkdir $date
while IFS=, read project ; do
    gcloud projects get-iam-policy $project --format=json > $date/$project-$date.json
done <<EOF
oat-dev-eu
oat-staging-eu
oat-prod-eu
oat-prod-jp
oat-prod-us
tao-artefacts
cmdb-api
tao-vpn
EOF