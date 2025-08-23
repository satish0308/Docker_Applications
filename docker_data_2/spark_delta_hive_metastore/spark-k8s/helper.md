# use the below code to do port forward and access the jhub from local lan other laptops


kubectl port-forward svc/proxy-public -n default --address 0.0.0.0 8081:80

also run the minikube tunnel


