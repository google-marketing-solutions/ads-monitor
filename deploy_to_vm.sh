#!/bin/bash
#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

SCRIPT_PATH=$(readlink -f "$0" | xargs dirname)

# # Set variables
CONFIGS_YAML="${SCRIPT_PATH}/infra-config.yaml"
PROJECT_ID=$(gcloud config get-value project 2> /dev/null)
ZONE=$(sed -n 's/^ZONE: \([-a-zA-Z0-9]*\)$/\1/p' $CONFIGS_YAML)
INSTANCE_NAME="ads-monitor-vm"
MACHINE_TYPE=$(sed -n 's/^MACHINE_TYPE: \([-a-zA-Z0-9]*\)$/\1/p' $CONFIGS_YAML)
IMAGE_PROJECT=cos-cloud
IMAGE_FAMILY=cos-stable
USERNAME=$(pwd | sed -n 's/\/home\/\([^/]*\).*/\1/p')
SSH_KEY_NAME="ads_monitor"

PRIVATE_KEY_PATH="/home/$USERNAME/.ssh/$SSH_KEY_NAME"
PUBLIC_KEY_PATH="$PRIVATE_KEY_PATH.pub"
GOOGLE_ADS_YAML=/home/$USERNAME/google-ads.yaml
GAARF_EXPORTER_ACCOUNT_ID=$(sed -n 's/^login_customer_id: \([-a-zA-Z0-9]*\)$/\1/p' $GOOGLE_ADS_YAML)

create_ssh_key() {
    echo "Checking for ssh keys..."
    # Check if the key exists
    if [ ! -f "$PRIVATE_KEY_PATH" ]
    then

        # If the key doesn't exist, create it
        echo "Key not found, creating now"
        ssh-keygen -t rsa -f $PRIVATE_KEY_PATH -C $USERNAME -N "" -b 2048
        chmod 600 $PUBLIC_KEY_PATH
    else
        # If the key exists, print a message and exit
        echo "Key already exists, no action taken"
    fi
}

create_compute_instance() {
    # Check if VM exists
    VM_EXISTS=$(gcloud compute instances list --project="$PROJECT_ID" --filter="name=($INSTANCE_NAME)" --format="value(name)")

    # Create the VM if it doesn't exist
    if [ -z "$VM_EXISTS" ]; then
        echo "VM does not exist. Creating..."
        # Create a new VM
        gcloud compute instances create $INSTANCE_NAME \
            --project=$PROJECT_ID \
            --zone=$ZONE \
            --machine-type=$MACHINE_TYPE \
            --image-family=$IMAGE_FAMILY \
            --image-project=$IMAGE_PROJECT \
            --metadata=ssh-keys="$USERNAME:$(cat $PUBLIC_KEY_PATH)"
    else
        echo "VM ${INSTANCE_NAME} already exists."
    fi

    echo "Getting new VM IP..."

    # Get the external IP of the VM
    VM_IP=$(gcloud compute instances describe $INSTANCE_NAME \
        --project=$PROJECT_ID \
        --zone=$ZONE \
        --format='get(networkInterfaces[0].accessConfigs[0].natIP)')


    echo $VM_IP
}

create_env_file() {
    echo "Creating env file..."
    echo GOOGLE_ADS_YAML=$GOOGLE_ADS_YAML >> .env
    echo GAARF_EXPORTER_ACCOUNT_ID=$GAARF_EXPORTER_ACCOUNT_ID >> .env
}

copy_files_to_vm() {
    echo "Copying files to remote..."
    gcloud compute scp --recurse "${SCRIPT_PATH}" $USERNAME@$INSTANCE_NAME:/home/$USERNAME/ --zone=$ZONE --project=$PROJECT_ID
    gcloud compute scp --recurse "$GOOGLE_ADS_YAML" $USERNAME@$INSTANCE_NAME:/home/$USERNAME/ --zone=$ZONE --project=$PROJECT_ID
    gcloud compute scp --recurse "${SCRIPT_PATH}/.env" $USERNAME@$INSTANCE_NAME:/home/$USERNAME/ --zone=$ZONE --project=$PROJECT_ID

    # Check the command's exit status and exit if it failed
    if [ $? -ne 0 ]; then
        echo "Failed to copy the files. Exiting..."
        exit 1
    else
        echo "Files successfully copied!"
    fi
}

ssh_to_vm_and_run_docker() {
    echo "Connecting by SSH..."
    ssh -i "$PRIVATE_KEY_PATH" -o UserKnownHostsFile=/dev/null \
        -o CheckHostIP=no -o StrictHostKeyChecking=no \
        $USERNAME@$VM_IP << EOF
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD:$PWD" -w "$PWD" docker/compose docker-compose --env-file .env -f "docker-compose.yaml" up
EOF
}

deploy_all(){
    create_ssh_key
    create_compute_instance
    create_env_file
    copy_files_to_vm
    ssh_to_vm_and_run_docker
}

deploy_all

echo "Connected"
