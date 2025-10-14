import argparse
import os
import time
import traceback
from string import Template

import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException


def parse_kv_pair(pair):
    if "=" not in pair:
        raise argparse.ArgumentTypeError(f"Expected KEY=VALUE format, got {pair}")
    key, value = pair.split("=", 1)
    return key.strip(), value.strip()


parser = argparse.ArgumentParser(
    description="Submit Kubernetes Jobs directly, optionally targeting Kueue")
parser.add_argument(
    "-work_item",
    dest="work_item",
    help="The work item to process",
    required=True)
parser.add_argument(
    "-mode",
    dest="mode",
    help="The mode to run in",
    default="full")
parser.add_argument(
    "-count",
    dest="count",
    type=int,
    help="The number of Jobs to submit",
    default=1)
parser.add_argument(
    "-namespace",
    dest="namespace",
    help="The Job namespace to run in",
    default="default")
parser.add_argument(
    "-container_name",
    dest="container_name",
    help="The container name to run",
    default="cloudburst")
parser.add_argument(
    "-image",
    dest="image",
    help="The container image to run",
    default="bhdockr/cloudburst:latest")
parser.add_argument(
    "-storage-type",
    dest="storage_type",
    required=True,
    help="The storage container/host type",
    default=os.getenv("STORAGE_TYPE"))
parser.add_argument(
    "-storage-container",
    dest="storage_container",
    required=True,
    help="The storage container/host",
    default=os.getenv("STORAGE_CONTAINER"))
parser.add_argument(
    "-kueue_queue",
    dest="kueue_queue",
    help="Optional Kueue LocalQueue name; when set the Job is annotated for Kueue admission",
    default=os.getenv("KUEUE_QUEUE"))
parser.add_argument(
    "-job-template",
    dest="job_template",
    help="Path to the Job template used for substitution",
    default="template/cloudburst-job-template.yaml")
parser.add_argument(
    "-param",
    dest="extra_params",
    metavar="KEY=VALUE",
    action="append",
    type=parse_kv_pair,
    help="Additional template parameter to include (can be repeated)")
parser.add_argument(
    "-save",
    dest="save_jobs",
    action="store_true",
    help="Save rendered Job manifests under ./tmp/saves without skipping submission")
parser.add_argument(
    "-debug",
    dest="debug",
    action="store_true",
    help="Print debug information")


def load_template(template_file):
    with open(template_file, "r") as file:
        return Template(file.read())


def substitute_template(template, variables):
    substituted_content = template.substitute(variables)
    return yaml.safe_load(substituted_content)


def load_kubernetes_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.BatchV1Api()


def build_message(args):
    message = {
        "WORK_ITEM": args.work_item,
        "MODE_STR": args.mode,
        "JOB_NAMESPACE": args.namespace,
        "CONTAINER_NAME": args.container_name,
        "CONTAINER_IMAGE": args.image,
        "STORAGE_TYPE": args.storage_type,
        "STORAGE_CONTAINER": args.storage_container,
    }
    if args.extra_params:
        for key, value in args.extra_params:
            message[key] = value
    if args.kueue_queue:
        message["KUEUE_QUEUE"] = args.kueue_queue
    return message


def save_job_manifest(job_manifest, job_name):
    save_dir = os.path.join("tmp", "saves")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{job_name}.yaml")
    with open(save_path, "w") as file_handle:
        yaml.safe_dump(job_manifest, file_handle)
    print(f"Saved Job manifest to {save_path}")


def create_kubernetes_job(batch_v1, template, message, save_jobs=False, debug=False):
    my_vars = {}
    b_named = False
    job_name = "job-cb"
    job_namespace = "default"
    kueue_queue = None

    for name1, value1 in message.items():
        my_vars[name1.upper()] = value1

        if name1 == "WORK_ITEM":
            job_name = f"job-cb-{value1}-{int(time.time_ns()/1000)}".lower()
            my_vars["JOB_NAME"] = job_name
            b_named = True
            if debug:
                print(f"naming job {job_name} based on {name1}")
        elif name1 == "JOB_NAMESPACE":
            job_namespace = value1
        elif name1.upper() == "KUEUE_QUEUE":
            kueue_queue = value1

    if not b_named:
        for name1, value1 in message.items():
            job_name = f"job-cb-{value1}-{int(time.time_ns()/1000)}".lower()
            my_vars["JOB_NAME"] = job_name
            if debug:
                print(f"naming job {job_name} based on {name1}")
            break

    if kueue_queue:
        my_vars["KUEUE_QUEUE"] = kueue_queue

    job_manifest = substitute_template(template, my_vars)

    if kueue_queue:
        metadata = job_manifest.setdefault("metadata", {})
        annotations = metadata.setdefault("annotations", {})
        annotations["kueue.x-k8s.io/queue-name"] = kueue_queue
        spec = job_manifest.setdefault("spec", {})
        spec["suspend"] = True
        if debug:
            print(f"Annotating Job {job_name} for Kueue queue {kueue_queue}")

    if debug:
        print(f"Submitting Job manifest: {job_manifest}")

    if save_jobs:
        save_job_manifest(job_manifest, job_name)

    try:
        batch_v1.create_namespaced_job(body=job_manifest, namespace=job_namespace)
        print(f"Job {job_name} created successfully in namespace {job_namespace}")
    except ApiException as exc:
        print(f"Exception when creating job: {exc}")
        traceback.print_exc()


def main(parsed_args):
    template = load_template(parsed_args.job_template)
    batch_v1 = load_kubernetes_client()

    for _ in range(parsed_args.count):
        message = build_message(parsed_args)
        create_kubernetes_job(
            batch_v1,
            template,
            message,
            save_jobs=parsed_args.save_jobs,
            debug=parsed_args.debug)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
