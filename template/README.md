# Cloudburst Job Template

The file `cloudburst-job-template.yaml` is rendered by `kueue_pub.py` using Python's `string.Template`. Each `${PLACEHOLDER}` token is substituted with command-line arguments or environment variables before the manifest is submitted to Kubernetes.

## Required Substitutions

- `${JOB_NAME}` — generated automatically from the work item unless you override it.
- `${CONTAINER_NAME}` — controls the Pod name, selector labels, and container identifier.
- `${CONTAINER_IMAGE}` — container image reference to pull for the Job.
- `${WORK_ITEM}` — logical unit of work, injected as the `WORK_ITEM` environment variable.
- `${STORAGE_TYPE}` / `${STORAGE_CONTAINER}` — passed to the container to locate input and output data.
- `${MODE_STR}` — optional execution mode string, useful for toggling behavior inside the container.

Use the `-param KEY=VALUE` flag with `kueue_pub.py` to add additional placeholders to the template.

## Kueue Integration

When a `-kueue_queue` is supplied, the submission script adds `${KUEUE_QUEUE}` to the template variables. It also applies the `kueue.x-k8s.io/queue-name` annotation and sets `spec.suspend=true` so that Kueue can manage admission.

## Volumes and Secrets

Two volumes are mounted into the Pod:

- `task-config` — ConfigMap expected to contain `tasks.json`, mounted at `/work/tasks.json` to describe available Cloudburst tasks.
- `ssh-key` — Secret containing a private key used by the container to reach external storage endpoints.

The `create-configmaps` Make target provisions both resources from local files under the repository root. Regenerate them whenever `tasks.json` or your SSH key changes.

## Resource Requests

By default, the Job requests 2 vCPUs and 2 GiB of memory. Adjust the `resources.requests` and `resources.limits` sections to match workload needs. Any additional environment variables, volume mounts, or tolerations can be added directly to the template once you introduce matching substitutions or static values.
