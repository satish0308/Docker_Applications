
# 🚀 JupyterHub + Spark + MinIO on Kubernetes

This project provides a **Kubernetes-based data science environment** with:

- **JupyterHub** (single-user pods on K8s, accessible from LAN)
- **Apache Spark** (master + workers for distributed big-data processing)
- **MinIO** (S3-compatible object store for large data)

It enables large-scale data processing directly from JupyterHub notebooks, backed by Spark and MinIO.

---

## 📦 Components

- **JupyterHub** – interactive notebooks with Spark integration.
- **Spark Master + Workers** – scalable compute for large datasets.
- **MinIO** – S3 storage backend for persisting datasets and results.
- **Kubernetes Dashboard** – monitor cluster resources.
- **Proxy Service** – allows external access from local LAN.

---

## ⚙️ Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- [Helm](https://helm.sh/docs/intro/install/)
- At least **4 CPUs** and **8GB RAM** allocated to Minikube.

---

## 🚀 Setup

### 1. Start Minikube
```bash
minikube start --driver=docker --cpus=4 --memory=8192


### 2. after Minilube Start (navigate to docker_data_files/docker_data_2/spark_delta_hive_metastore/spark-k8s)

kubectl apply -f spark-k8s/


# JupyterHub
kubectl -n default port-forward svc/proxy-public --address 0.0.0.0 8081:80

# Kubernetes Dashboard
kubectl -n kubernetes-dashboard port-forward --address 0.0.0.0 svc/kubernetes-dashboard 8080:80

# Run tunnel for LoadBalancer services (optional)
minikube tunnel



### 3. Connect to spark from jhub
=======
# use the below code to do port forward and access the jhub from local lan other laptops


kubectl port-forward svc/proxy-public -n default --address 0.0.0.0 8081:80

also run the minikube tunnel


### 4. if wants to connect to miniO (s3)

minio_access_key="minioadmin"
minio_secret_key="minioadmin123"

#if s3 needs to be used as file source
spark = SparkSession.builder \
    .appName("JupyterHub on K8s with MinIO") \
    .master("spark://spark-master.default.svc.cluster.local:7077") \
    .config("spark.executor.memory", "2g") \
    .config("spark.executor.memoryOverhead", "512m") \
    .config("spark.driver.memory", "2g") \
    .config("spark.driver.memoryOverhead", "512m") \
    .config("spark.executor.cores", "1") \
    .config("spark.driver.cores", "1") \
    .config("spark.driver.host", driver_host_ip) \
    .config("spark.driver.port", "4040") \
    .config("spark.blockManager.port", "7078") \
    .config("spark.driver.bindAddress", "0.0.0.0") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio.default.svc.cluster.local:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
    .config("spark.hadoop.fs.s3a.signing-algorithm", "S3SignerType") \
    .getOrCreate()



### 5. Sample to insert file into S3 :



df = spark.range(5)
df.show()






#option to insert file into s3 bucket

aws_access_key_id="minioadmin",
aws_secret_access_key="minioadmin123"

#if s3 needs to be used as file source
minio_access_key="minioadmin"
minio_secret_key="minioadmin123"

#if s3 needs to be used as file source
spark = SparkSession.builder \
    .appName("JupyterHub on K8s with MinIO") \
    .master("spark://spark-master.default.svc.cluster.local:7077") \
    .config("spark.executor.memory", "2g") \
    .config("spark.executor.memoryOverhead", "512m") \
    .config("spark.driver.memory", "2g") \
    .config("spark.driver.memoryOverhead", "512m") \
    .config("spark.executor.cores", "1") \
    .config("spark.driver.cores", "1") \
    .config("spark.driver.host", driver_host_ip) \
    .config("spark.driver.port", "4040") \
    .config("spark.blockManager.port", "7078") \
    .config("spark.driver.bindAddress", "0.0.0.0") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio.default.svc.cluster.local:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
    .config("spark.hadoop.fs.s3a.signing-algorithm", "S3SignerType") \
    .getOrCreate()


