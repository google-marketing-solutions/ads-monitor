#!/bin/bash

# Exit on any error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration variables
GAARF_EXPORTER_ACCOUNT_ID=""
PROJECT_ID=""
REGION="us-central1"
ZONE="${REGION}-a"
INSTANCE_NAME="ads-monitoring-instance"
MACHINE_TYPE="e2-medium"
DISK_NAME="${INSTANCE_NAME}-data"
EXPOSE_PROMETHEUS=false
GOOGLE_ADS_YAML_PATH="google-ads.yaml"  # Default path

# Function to print step description
_print_step() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

# Function to print error and exit
_error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

validate_inputs() {
    _print_step "Validating inputs"

    if [ -z "$GAARF_EXPORTER_ACCOUNT_ID" ]; then
        _error_exit "Please enter a Google Ads account id to work on."
    fi

    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2> /dev/null)
        echo -e "Using default project: $PROJECT_ID"
    fi

    if [ ! -f "$GOOGLE_ADS_YAML_PATH" ]; then
        _error_exit "Google Ads YAML file not found at: $GOOGLE_ADS_YAML_PATH"
    fi

}

check_permissions() {
    _print_step "Checking permissions"

    # Check if authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
        _error_exit "Not authenticated with gcloud. Please run 'gcloud auth login' first."
    fi

    # Check if user has necessary permissions
    if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
        _error_exit "Insufficient permissions or invalid project ID: $PROJECT_ID"
    fi

    echo -e "Permissions check passed"
}

enable_apis() {
    _print_step "Enabling necessary APIs"

    apis=(
        "compute.googleapis.com"
    )

    for api in "${apis[@]}"; do
        echo "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID" || \
            _error_exit "Failed to enable $api"
    done
}

create_persistent_disk() {
  _print_step "Creating persistent disk..."

  if gcloud compute disks describe "$DISK_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
    echo "Persistent disk already exists, skipping"
  else
    gcloud compute disks create $DISK_NAME \
      --project="$PROJECT_ID" \
      --zone="$ZONE" \
      --size=200GB \
      --type=pd-standard
  fi
}

process_config_files() {
  _print_step "Processing config files..."

  cp cloud-init.yaml cloud-init-parsed.yaml

  # Perform substitutions on the new file
  sed -i "s#DISK_NAME#${DISK_NAME}#g" cloud-init-parsed.yaml
  sed -i "s#GAARF_EXPORTER_ACCOUNT_ID_VAR#${GAARF_EXPORTER_ACCOUNT_ID}#g" cloud-init-parsed.yaml

  # Define file mappings (marker -> file path)
  declare -A file_mappings=(
    ["DOCKER COMPOSE CONTENT"]="docker-compose.yaml"
    ["GOOGLE ADS YAML CONTENT"]="$GOOGLE_ADS_YAML_PATH"
    ["PROMETHEUS CONFIG"]="prometheus/prometheus.yml"
    ["PROMETHEUS ALERTS"]="prometheus/alerts.yml"
    ["ALERTMANAGER CONFIG"]="alertmanager/alertmanager.yml"
  )

  # Process each file
  for marker in "${!file_mappings[@]}"; do
    sed -i \
      -e "/# ${marker}/r /dev/stdin" \
      -e "/# ${marker}/d" \
      cloud-init-parsed.yaml < <(sed 's/^/    /' "${file_mappings[$marker]}")
  done
}

create_instance_template() {
  _print_step "Creating instance template..."

  if gcloud compute instance-templates describe "$INSTANCE_NAME-template" --project="$PROJECT_ID" &>/dev/null; then
    echo "Instance template already exists, skipping"
  else
    gcloud compute instance-templates create $INSTANCE_NAME-template \
      --project="$PROJECT_ID" \
      --machine-type=$MACHINE_TYPE \
      --boot-disk-size=200GB \
      --image-project=ubuntu-os-cloud \
      --image-family=ubuntu-minimal-2204-lts \
      --disk="name=${DISK_NAME},device-name=${DISK_NAME},mode=rw,boot=no" \
      --tags=http-server,https-server \
      --metadata-from-file=user-data=cloud-init-parsed.yaml \
      --scopes=cloud-platform \
      --service-account=default
  fi
}

create_managed_instance_group() {
  _print_step "Creating managed instance group..."

  if gcloud compute instance-groups managed describe "$INSTANCE_NAME-group" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
    echo "Managed instance group already exists, skipping"
  else
    gcloud compute instance-groups managed create $INSTANCE_NAME-group \
      --project="$PROJECT_ID" \
      --base-instance-name=$INSTANCE_NAME \
      --size=1 \
      --template=$INSTANCE_NAME-template \
      --zone="$ZONE" \
      --update-policy-max-surge=0 \
      --update-policy-max-unavailable=1
  fi
}


create_firewall_rules(){
  _print_step "Creating firewall rules..."

  PORTS="tcp:3000"

  # Will be used mostly for debugging purposes
  if [ "$EXPOSE_PROMETHEUS" ]; then
    PORTS="$PORTS,tcp:9090,tcp:9093"
  fi

  if gcloud compute firewall-rules describe "allow-monitoring-ports" --project="$PROJECT_ID" &>/dev/null; then
    echo "Firewall rule already exists, skipping"
  else
    gcloud compute firewall-rules create allow-monitoring-ports \
      --project="$PROJECT_ID" \
      --direction=INGRESS \
      --priority=1000 \
      --network=default \
      --action=ALLOW \
      --rules=$PORTS \
      --source-ranges=0.0.0.0/0 \
      --target-tags=http-server
  fi
}

wait_for_ip() {
  _print_step "Waiting for instance IP..."

  local attempts=0
  local max_attempts=6
  local wait_time=10

  while [ $attempts -lt $max_attempts ]; do
    EXTERNAL_IP=$(gcloud compute instances list \
      --project="$PROJECT_ID" \
      --filter="name ~ ^${INSTANCE_NAME}" \
      --format="get(networkInterfaces[0].accessConfigs[0].natIP)")

  if [ -n "$EXTERNAL_IP" ]; then
    echo -e "\n${GREEN}Instance IP is ready!${NC}"
    echo "Instance External IP: ${EXTERNAL_IP}"
    return 0
  fi

  echo "Waiting for IP address... (attempt $((attempts + 1))/$max_attempts)"
  sleep $wait_time
  attempts=$((attempts + 1))
  done

  _error_exit "Timeout waiting for instance IP. Please check the Google Cloud Console for status."
}

wait_for_services() {
  # Waiting for cloud-init to finish (which means that services are ready)
  _print_step "Waiting for Grafana to be available..."

  local attempts=0
  local max_attempts=12
  local wait_time=15

  while [ $attempts -lt $max_attempts ]; do
    if curl -s --head "http://${EXTERNAL_IP}:3000" > /dev/null; then
      echo -e "\n${GREEN}Setup complete! Services are ready.${NC}"
      echo "You can access:"
      echo "- Grafana at: http://${EXTERNAL_IP}:3000"
      if [ "$EXPOSE_PROMETHEUS" = true ]; then
        echo "- Prometheus at: http://${EXTERNAL_IP}:9090"
        echo "- Alertmanager at: http://${EXTERNAL_IP}:9093"
      fi
      return 0
    fi

    echo "Waiting for services to start... (attempt $((attempts + 1))/$max_attempts)"
    sleep $wait_time
    attempts=$((attempts + 1))
  done

  _error_exit "Timeout waiting for services to start. Please check the instance logs."
}

deploy_all() {
  _print_step "Starting setup for Ads Monitor on Compute Engine"

  check_permissions
  enable_apis
  process_config_files
  create_persistent_disk
  create_firewall_rules
  create_instance_template
  create_managed_instance_group
  wait_for_ip
  wait_for_services
}


# Get all functions, remove the "declare -f" prefix, and filter out internal functions
AVAILABLE_FUNCTIONS=$(declare -F | cut -d' ' -f3 | grep -v '^_')

# Array to store functions to execute
FUNCTIONS=()

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --account-id)
            GAARF_EXPORTER_ACCOUNT_ID="$2"
            shift 2
            ;;
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --zone)
            ZONE="$2"
            shift 2
            ;;
        --expose-prometheus)
            EXPOSE_PROMETHEUS=true
            shift
            ;;
        --google-ads-yaml)
            GOOGLE_ADS_YAML_PATH="$2"
            shift 2
            ;;
        -*)
            _error_exit "Unknown parameter: $1"
            ;;
        *)
            # If it's not a flag, add it to functions array
            FUNCTIONS+=("$1")
            shift
            ;;
    esac
done

# --- Main ---

# Validate inputs first
validate_inputs

# If no functions specified, show available functions
if [ ${#FUNCTIONS[@]} -eq 0 ]; then
    echo "Available functions:"
    echo "${AVAILABLE_FUNCTIONS//$'\n'/$'\n  '}"  # indent the list
    exit 1
fi

# Validate functions
for func in "${FUNCTIONS[@]}"; do
    if ! echo "$AVAILABLE_FUNCTIONS" | grep -q "^${func}$"; then
        _error_exit "Unknown function: $func"
    fi
done

# Execute functions
for func in "${FUNCTIONS[@]}"; do
    echo -e "\n${YELLOW}Executing $func${NC}"
    "$func"
done
