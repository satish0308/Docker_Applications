#use below to access the jhub from another laptop and run minikube tunnel to assign external ip

kubectl port-forward svc/proxy-public -n default --address 0.0.0.0 8081:80

