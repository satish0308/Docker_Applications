from pyspark.sql import SparkSession
import pyspark.pandas as pdf
from pyspark import SparkConf,SparkContext
import sys


def call_main():
    spark=SparkSession.builder.master("local").appName("demo").getOrCreate()
    df=spark.read.json(sys.argv[1])
    df2=df.select('user_id','friends')
    print(sys.argv[2])
    print('satish')
    df3=df2.repartition(5)
    df3.write.option("header","true").mode('overwrite').csv(sys.argv[2])

    

if __name__=="__main__":
    call_main()