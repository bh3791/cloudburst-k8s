# Cloudburst on Kubernetes

This repository packages Kubernetes deployment assets for running Cloudburst workloads with [Kueue](https://kubernetes.io/docs/concepts/workloads/controllers/job/#kueue-integration) based admission control. It complements the container images, tasks, and CLI workflows maintained in the companion [`cloudburst`](https://github.com/bh3791/cloudburst) repository.

## Repository Highlights

- `Makefile` — reproducible workflows for bootstrapping a local cluster, applying supporting manifests, and managing Jobs.
- `deployment/` — upstream and project-specific manifests for Kueue, Prometheus, and supporting configuration.
- `template/cloudburst-job-template.yaml` — parameterized Job manifest consumed by the submission script.
- `kueue_pub.py` — Python utility that renders the Job template, applies optional Kueue annotations, and submits Jobs through the Kubernetes API.

## Make Targets at a Glance

The Makefile groups frequent cluster administration and Job management tasks:

| Target | Description |
| --- | --- |
| `post-job` | Render and submit a Job via `kueue_pub.py` using example parameters (customize before use). |
| `monitor-jobs` | Stream logs for Pods labeled `app=la-haz`, useful for observing running Cloudburst Jobs. |
| `clear-jobs` | Remove completed and failed Jobs to keep the namespace tidy. |
| `update-configmaps` | Recreate ConfigMaps and the `ssh-key` Secret that back the Job template volumes. |
| `create-configmaps` / `delete-configmaps` | Manage the ConfigMaps and Secret individually when iterating on configuration. |
| `setup` | Convenience target that invokes ConfigMap refresh and monitoring prerequisites (combine with `install-kueue`). |
| `remove-all` | Wrapper to clean up both Kueue and Prometheus artifacts from the cluster. |
| `install-kueue` / `delete-kueue` | Apply or remove the upstream Kueue controller and sample queues. |
| `init-prometheus` / `delete-prometheus` | Deploy or tear down Prometheus, kube-state-metrics, and related resources. |
| `k3s-init` / `k3s-delete` | Install or uninstall a local single-node [k3s](https://k3s.io) cluster for testing. |

Targets assume you have a working `kubectl` context pointing at the desired cluster. Edit the sample variables (`K8S_IP`, `STORAGE_IP`, container image, etc.) to match your environment before running the recipes.

## Submitting Jobs with `kueue_pub.py`

Run the submission helper directly or through `make post-job` to generate and apply Kubernetes Jobs programmatically. The script loads in-cluster credentials when running inside Kubernetes and falls back to your local kubeconfig otherwise.

Annotated Jobs target Kueue admission by setting `spec.suspend=true` and including the `kueue.x-k8s.io/queue-name` annotation. You can set `KUEUE_QUEUE` as an environment variable or pass the `-kueue_queue` flag explicitly to control which LocalQueue handles admission.

### Argument Reference

| Flag | Description |
| --- | --- |
| `-work_item` *(required)* | Logical work item identifier included in the Job name and exposed to the container as `WORK_ITEM`. |
| `-mode` | High-level execution mode passed through as `MODE_STR`; defaults to `full`. |
| `-count` | Submit the rendered Job multiple times in sequence (default `1`). |
| `-namespace` | Namespace for the Jobs; default `default`. |
| `-container_name` | Container name used in the Pod spec and selector labels (default `cloudburst`). |
| `-image` | Container image reference to run (default `bhdockr/cloudburst:latest`). |
| `-storage-type` *(required)* | Storage backend identifier (e.g., `network-rsync`); also available via `STORAGE_TYPE`. |
| `-storage-container` *(required)* | Storage endpoint or bucket name; defaults from `STORAGE_CONTAINER`. |
| `-kueue_queue` | Optional LocalQueue name used to annotate the Job for Kueue. |
| `-job-template` | Path to the template consumed by `string.Template` (default `cloudburst-job-template.yaml`). |
| `-param KEY=VALUE` | Repeatable extra template substitutions (e.g., supply custom environment variables or labels). |
| `-save` | Persist each rendered manifest under `./tmp/saves` in addition to submitting it. |
| `-debug` | Verbose logging, including the generated manifest before submission. |

Parameters populate placeholders in `template/cloudburst-job-template.yaml`. Extend the template with additional `${PLACEHOLDER}` fields, then provide values via `-param` or environment defaults.

## Template Reference

See `template/README.md` for a walkthrough of the Job template structure, mounted volumes, and expected variables.

## Observability and Cleanup

Use `make monitor-jobs` to tail application logs while Jobs are running. When finished, `make clear-jobs` removes successful and failed Jobs, and `make remove-all` disassembles optional monitoring and Kueue components.

`make init-prometheus` now provisions Prometheus, Alertmanager, and alerting rules for Cloudburst Jobs and cluster nodes. Before applying, edit `deployment/alertmanager-smtp-secret.yaml` with valid SMTP credentials so Alertmanager can send email notifications.
