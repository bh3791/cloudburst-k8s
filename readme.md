# Cloudburst on Kubernetes
The repo is used to store artifacts related to running cloudburst-style containers in kubernetes, using Kueue to manage job requests.

The `Makefile` contains instructions to set up a test cluster, using the artifacts in the `deployment` directory.
The script `kueue_pub.py` is used to submit jobs to kubernetes. It takes a few options and fills out a customizable job template (in templates) 

## Using Kueue for Scheduling

The script passes Jobs to [Kueue](https://kubernetes.io/docs/concepts/workloads/controllers/job/#kueue-integration) instead of enforcing concurrency limits inside the controller. Set the `KUEUE_QUEUE` environment variable (or pass `-kueue_queue`) to the script and the generated Job will be annotated for that LocalQueue. When targeting Kueue, the controller lets Kueue manage admission instead of polling the API server, and Jobs are created with `spec.suspend=true` so that Kueue can unsuspend them once capacity is available. Submit the Job spec through the Kubernetes API (e.g. `kubectl apply`) as usual; no additional service endpoint is exposed.

To bootstrap Kueue on a cluster, apply the manifests in the `deployment` directory using the makefile:

```
# installs the upstream controller
kubectl apply --server-side -k deployment/kueue-install --force-conflicts

# creates a ResourceFlavor, ClusterQueue, and LocalQueue for Cloudburst
kubectl apply -f deployment/kueue-queues.yaml
```
