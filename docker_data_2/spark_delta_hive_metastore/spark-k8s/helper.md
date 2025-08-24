# use the below code to do port forward and access the jhub from local lan other laptops


kubectl port-forward svc/proxy-public -n default --address 0.0.0.0 8081:80

also run the minikube tunnel


import pyspark
from pyspark.sql import SparkSession
import socket


driver_host_ip = socket.gethostbyname(socket.gethostname())
driver_host_ip

spark = SparkSession.builder \
    .appName("JupyterHub on K8s") \
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
    .config("spark.executor.extraJavaOptions", "-Dlog4j.debug -Dlog4j.configuration=file:/home/spark/conf/log4j.properties") \
    .getOrCreate()



df = spark.range(5)
df.show()


import boto3
import os

# MinIO connection info (internal pod-to-pod communication)
s3 = boto3.client(
    "s3",
    endpoint_url="http://minio:9000",  # use Kubernetes service name of MinIO
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123",
    region_name="us-east-1"
)

bucket_name = "spark-data"
local_folder = "/home/jovyan/files"  # path inside JupyterHub pod
s3_prefix = ""  # put inside bucket root, change if you want subfolder

# Create bucket if missing
try:
    s3.head_bucket(Bucket=bucket_name)
    print(f"Bucket '{bucket_name}' already exists.")
except:
    s3.create_bucket(Bucket=bucket_name)
    print(f"Bucket '{bucket_name}' created.")

# Upload files from JHub to MinIO

for root, dirs, files in os.walk(local_folder):
    for file in files:
        local_path = os.path.join(root, file)
        relative_path = os.path.relpath(local_path, local_folder)
        s3_key = os.path.join(s3_prefix, relative_path)

        s3.upload_file(local_path, bucket_name, s3_key)
        print(f"✅ Uploaded {local_path} → s3://{bucket_name}/{s3_key}")



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

