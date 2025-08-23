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
