#!/bin/bash
# minikube_monitor.sh
# Satish's Minikube automation script with self-healing port-forward

LOG_DIR="minikube_monitor"
STATS_FILE="$LOG_DIR/docker_stats.csv"
mkdir -p "$LOG_DIR"

# Logger
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" | tee -a "$LOG_DIR/minikube.log"
}

# Cleanup on exit
cleanup() {
    log "🧹 Cleaning up background processes..."
    pkill -P $$ || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Ensure Minikube is running (robust check)
ensure_minikube() {
    host=$(minikube status --format '{{.Host}}' 2>/dev/null)
    kubelet=$(minikube status --format '{{.Kubelet}}' 2>/dev/null)
    apiserver=$(minikube status --format '{{.APIServer}}' 2>/dev/null)
    kubeconfig=$(minikube status --format '{{.Kubeconfig}}' 2>/dev/null)

    if [[ "$host" == "Running" && "$kubelet" == "Running" && "$apiserver" == "Running" && "$kubeconfig" == "Configured" ]]; then
        log "✅ Minikube is already running."
    else
        log "🚀 Minikube is not fully running. Starting..."
        minikube start --driver=docker
    fi
}

# Wait for all pods to be ready (with 15 min timeout)
wait_for_pods() {
    log "⏳ Waiting for all pods to be ready..."
    local timeout=$((15 * 60)) # 15 minutes in seconds
    local start_time=$(date +%s)

    while true; do
        # Get pods not in Running/Completed
        not_ready=$(minikube kubectl -- get pods --all-namespaces --no-headers \
            | awk '$4 != "Running" && $4 != "Completed"')

        if [[ -z "$not_ready" ]]; then
            log "✅ All pods are running or completed."
            break
        fi

        # Timeout check
        now=$(date +%s)
        elapsed=$((now - start_time))
        if [[ $elapsed -ge $timeout ]]; then
            log "⏱ Timeout (15m) waiting for pods. Restarting Minikube..."
            minikube stop
            minikube start --driver=docker
            start_time=$(date +%s) # reset timer
        fi

        log "⚠️ Pods not ready yet:"
        echo "$not_ready" | tee -a "$LOG_DIR/minikube.log"
        log "⏳ Retrying in 10s..."
        sleep 10
    done
}

port_forward() {
    local namespace=$1
    local svc=$2
    local local_port=$3
    local remote_port=$4
    local name="$svc-$local_port"

    while true; do
        log "🔗 Starting port-forward: $name"
        log "➡️ Executing: minikube kubectl -- -n $namespace port-forward --address 0.0.0.0 svc/$svc $local_port:$remote_port"

        # Run port-forward in background and capture PID
        minikube kubectl -- -n "$namespace" port-forward --address 0.0.0.0 svc/"$svc" "$local_port:$remote_port" \
            >>"$LOG_DIR/$name.log" 2>&1 &
        pf_pid=$!

        # Wait for process to exit
        wait $pf_pid
        exit_code=$?

        log "❌ Port-forward $name exited (code=$exit_code). Retrying in 30s..."
        sleep 30

        ensure_minikube
        wait_for_pods
    done
}

# Track Docker stats in CSV
track_docker_stats() {
    log "📊 Tracking Docker stats into $STATS_FILE"
    (
        echo "timestamp,container_id,cpu_perc,mem_usage,mem_perc,net_io,block_io,pids"
        while true; do
            docker stats --no-stream --format \
                "{{.Container}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}" \
                | awk -v d="$(date '+%Y-%m-%d %H:%M:%S')" '{print d","$0}' >>"$STATS_FILE"
            sleep 30
        done
    ) &
}

### Main workflow ###
log "===== 🚀 Starting Minikube Monitor Script ====="

ensure_minikube
wait_for_pods
track_docker_stats

# Start Minikube Dashboard
log "📺 Starting Minikube Dashboard..."
minikube dashboard --url >> "$LOG_DIR/dashboard.log" 2>&1 &

# Start port-forwarding in background
port_forward default proxy-public 8081 80 &
port_forward kubernetes-dashboard kubernetes-dashboard 8080 80 &
port_forward default spark-master 8082 8080 &

wait
