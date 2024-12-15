#!/bin/bash

# Exit on any error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Configuration variables (matching deploy.sh)
PROJECT_ID=""
REGION="us-central1"
ZONE="${REGION}-a"
INSTANCE_NAME="ads-monitoring-instance"
DISK_NAME="${INSTANCE_NAME}-data"

# Function to print step description
print_step() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

# Function to print error and exit
error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

# Split each cleanup task into separate functions
cleanup_mig() {
    print_step "Deleting Managed Instance Group"
    if gcloud compute instance-groups managed describe "$INSTANCE_NAME-group" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
        gcloud compute instance-groups managed delete "$INSTANCE_NAME-group" \
            --zone="$ZONE" \
            --project="$PROJECT_ID" \
            --quiet
        echo "Managed Instance Group deleted"
    else
        echo "Managed Instance Group not found, skipping"
    fi
}

cleanup_template() {
    print_step "Deleting Instance Template"
    if gcloud compute instance-templates describe "$INSTANCE_NAME-template" --project="$PROJECT_ID" &>/dev/null; then
        gcloud compute instance-templates delete "$INSTANCE_NAME-template" \
            --project="$PROJECT_ID" \
            --quiet
        echo "Instance Template deleted"
    else
        echo "Instance Template not found, skipping"
    fi
}

cleanup_firewall() {
    print_step "Deleting Firewall Rules"
    if gcloud compute firewall-rules describe "allow-monitoring-ports" --project="$PROJECT_ID" &>/dev/null; then
        gcloud compute firewall-rules delete "allow-monitoring-ports" \
            --project="$PROJECT_ID" \
            --quiet
        echo "Firewall rules deleted"
    else
        echo "Firewall rules not found, skipping"
    fi
}

cleanup_disk() {
    print_step "Deleting Persistent Disk"
    if gcloud compute disks describe "$DISK_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
        gcloud compute disks delete "$DISK_NAME" \
            --zone="$ZONE" \
            --project="$PROJECT_ID" \
            --quiet
        echo "Persistent disk deleted"
    else
        echo "Persistent disk not found, skipping"
    fi
}

cleanup() {
    print_step "Starting cleanup of Ads Monitor resources"

    # Get project ID from gcloud config
    PROJECT_ID=$(gcloud config get-value project 2> /dev/null)
    echo "Using project: $PROJECT_ID"

    case "${1:-all}" in  # Use first argument, default to 'all' if none provided
        "mig")
            cleanup_mig
            ;;
        "template")
            cleanup_template
            ;;
        "firewall")
            cleanup_firewall
            ;;
        "disk")
            cleanup_disk
            ;;
        "all" | "")
            cleanup_mig
            cleanup_template
            cleanup_firewall
            cleanup_disk
            ;;
        *)
            error_exit "Invalid component. Available components: mig, template, firewall, disk, all"
            ;;
    esac

    print_step "Cleanup complete!"
}

# Run the cleanup function with first argument
cleanup "$1"
