gcloud batch jobs submit evidence-collection-jan16-16 \
    --project=swye360-prod-01 \
    --location=us-central1 \
    --network=projects/swye360-prod-01/global/networks/swye-vpc \
    --subnetwork=projects/swye360-prod-01/regions/us-central1/subnetworks/swye-subnet-public-subnet \
    --config=- <<EOF
name: projects/swye360-prod-01/locations/us-central1/jobs/evidence-collection-jan16-16
taskGroups:
- taskSpec:
    runnables:
    - container:
        imageUri: us-central1-docker.pkg.dev/swye360-prod-01/data-sync-repo/data-sync-app:latest
        commands: ["node", "dist/index.js", "evidence-collection"]
      timeout: 91600s
    computeResource:
        cpuMilli: 16000     # Matches e2-standard-16 (16 vCPUs)
        memoryMib: 65536    # Matches e2-standard-16 (64 GiB)
        bootDiskMib: 51200
    maxRetryCount: 1
allocationPolicy:
    instances:
    - policy:
        machineType: e2-standard-16
logsPolicy:
    destination: CLOUD_LOGGING
EOF
