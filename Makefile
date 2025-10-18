K8S_IP=bruce-mint
STORAGE_IP=bruce@bruce-mint

#AWS_ID=$(AWS_ID) # your AWS account ID here, if using AWS. Using an ENV variable
#AWS_REGION=$(AWS_REGION) # your preferred AWS region here, if using AWS. Using an ENV variable
#GAR_REPO_PREFIX=$(GAR_REPO_PREFIX) # e.g. us-west2-docker.pkg.dev. Using an ENV variable
#GAR_PROJECT_ID=$(GAR_PROJECT_ID) # your Google Cloud Project ID, if using. An ENV variable
#ECR_REPO_ID=$(DEPLOYMENT_ID)
#ECR_REPO_URL=$(AWS_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

# post a job
post-job:
	python3 kueue_pub.py -work_item Site00001 -storage-type network-rsync -storage-container bruce@bruce-mint -kueue_queue cloudburst -container_name la-haz -image bhdockr/la-haz -save

monitor-jobs:
	kubectl logs -l app=la-haz --follow --max-log-requests 40

clear-jobs:
	kubectl delete job --field-selector=status.successful=1
	kubectl delete job --field-selector=status.successful=0

clear-rs:
	kubectl get rs -o jsonpath='{range .items[?(@.status.replicas==0)]}{.metadata.name}{"\n"}{end}' \
	| xargs -r -I{} kubectl delete rs {}

setup: update-configmaps init-kueue init-prometheus

remove-all: delete-keueue delete-prometheus

update-configmaps: delete-configmaps create-configmaps

create-configmaps:
	# the following secrets are used by the cloudburst job template
	kubectl create secret generic ssh-key --from-file=id_ed25519=$(HOME)/.ssh/id_ed25519

	# these configmaps are used to reduce the number of docker rebuilds
	kubectl create configmap task-config --from-file=../ucerf3-hazard/tasks.json
	kubectl create configmap job-template --from-file=cloudburst-job-template.yaml

delete-configmaps:
	# the following secrets are used by the cloudburst job template
	-kubectl delete secret ssh-key

	# these configmaps are used to reduce the number of docker rebuilds
	-kubectl delete configmap task-config
	-kubectl delete configmap job-template

k3s-init:
	# was: kind create cluster --config deployment/kind-ports.yaml
	# now: install k3s
	curl -sfL https://get.k3s.io | sudo sh -

k3s-delete:
	sudo /usr/local/bin/k3s-uninstall.sh

init-kueue:
	kubectl apply --server-side -k deployment/kueue-install/ --force-conflicts
	kubectl apply -f deployment/kueue-queues.yaml

delete-kueue:
	kubectl delete -f deployment/kueue-queues.yaml
	kubectl delete -f deployment/kueue-install/

init-prometheus:
	kubectl apply -f deployment/prometheus-configmap.yaml
	kubectl apply -f deployment/prometheus-rules-configmap.yaml
	envsubst < deployment/alertmanager-configmap.yaml | kubectl apply -f -
	kubectl apply -f deployment/alertmanager-deployment.yaml
	kubectl apply -f deployment/kube-state-metrics.yaml
	kubectl apply -f deployment/prometheus-deployment.yaml

delete-prometheus:
	-kubectl delete -f deployment/prometheus-deployment.yaml
	-kubectl delete -f deployment/kube-state-metrics.yaml
	-kubectl delete -f deployment/alertmanager-deployment.yaml
	-kubectl delete -f deployment/alertmanager-configmap.yaml
	-kubectl delete -f deployment/prometheus-rules-configmap.yaml
	-kubectl delete -f deployment/prometheus-configmap.yaml
