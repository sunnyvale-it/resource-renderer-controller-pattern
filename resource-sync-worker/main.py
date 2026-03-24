import os
import json
import shutil
from pathlib import Path
from fastapi import FastAPI, Request
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import git

CRD_GROUP = "poc.gitrenderer.com"
CRD_VERSION = "v1alpha1"
CRD_PLURAL = "appconfigs"
NAMESPACE = os.getenv("NAMESPACE", "default")
RENDER_TARGET = os.getenv("RENDER_TARGET", "git").lower()

# Git Config
GIT_TARGET_REPO = os.getenv("GIT_TARGET_REPO", "https://github.com/example/target-repo.git")
GIT_TARGET_BRANCH = os.getenv("GIT_TARGET_BRANCH", "main")
GIT_CLONE_DIR = os.getenv("GIT_CLONE_DIR", "/var/lib/sync-worker/repo")
GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "Sync Worker")
GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "sync-worker@poc.com")

def init_k8s_client():
    try:
        config.load_incluster_config()
        print("Loaded within-cluster config.")
    except config.ConfigException:
        print("Loaded local kubeconfig.")
        config.load_kube_config()
    
    return client.CustomObjectsApi()

def sync_git_repo():
    print(f"Ensuring Git repository is present and up-to-date at {GIT_CLONE_DIR}...")
    if not os.path.exists(GIT_CLONE_DIR):
        os.makedirs(GIT_CLONE_DIR, exist_ok=True)
        
    try:
        repo = git.Repo(GIT_CLONE_DIR)
        remote_url = next(repo.remote('origin').urls)
        if remote_url != GIT_TARGET_REPO:
            raise Exception("Remote URL mismatch")
    except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError, Exception) as e:
        print(f"Repository not valid or mismatch ({e}). Removing and re-cloning...")
        if os.path.exists(GIT_CLONE_DIR):
            shutil.rmtree(GIT_CLONE_DIR)
        repo = git.Repo.clone_from(GIT_TARGET_REPO, GIT_CLONE_DIR, branch=GIT_TARGET_BRANCH)

    # Bulletproof state: discard any crashed local changes and pull latest
    try:
        repo.remote('origin').fetch()
        repo.git.reset('--hard', f'origin/{GIT_TARGET_BRANCH}')
        repo.git.clean('-fd')
    except Exception as e:
        print(f"Failed to reset repository state: {e}. Attempting re-clone as fallback.")
        shutil.rmtree(GIT_CLONE_DIR)
        repo = git.Repo.clone_from(GIT_TARGET_REPO, GIT_CLONE_DIR, branch=GIT_TARGET_BRANCH)
    
    with repo.config_writer() as git_config:
        git_config.set_value('user', 'email', GIT_AUTHOR_EMAIL)
        git_config.set_value('user', 'name', GIT_AUTHOR_NAME)
        
    return repo

def process_cdc_event(api_instance, message_value):
    if not message_value:
        return
        
    payload = message_value.get("payload")
    if not payload:
        return
        
    op = payload.get("op")
    if not op:
        return
        
    if op in ("c", "r", "u"):
        after = payload.get("after")
        if not after:
            return
        
        if RENDER_TARGET == "git":
            apply_git_resource(after)
        else:
            apply_custom_resource(api_instance, after)
            
    elif op == "d":
        before = payload.get("before")
        if not before:
            return
            
        if RENDER_TARGET == "git":
            delete_git_resource(before.get("name"))
        else:
            delete_custom_resource(api_instance, before.get("name"))

def apply_git_resource(data):
    repo = sync_git_repo()
    name = data.get("name")
    if not name:
        return
        
    k8s_name = str(name).lower().replace("_", "-").replace(" ", "-")
    resources_dir = Path(GIT_CLONE_DIR) / "resources" / "appconfigs"
    resources_dir.mkdir(parents=True, exist_ok=True)
    file_path = resources_dir / f"{k8s_name}.json"
    
    print(f"[GIT RENDERER] Writing AppConfig '{k8s_name}' to {file_path}")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
        
    repo.index.add([str(file_path.absolute())])
    if repo.is_dirty(untracked_files=True):
        repo.index.commit(f"Auto-update AppConfig: {k8s_name}")
        repo.remote(name='origin').push()
        print(f"[GIT RENDERER] Successfully committed and pushed '{k8s_name}' to Git.")
    else:
        print(f"[GIT RENDERER] No changes detected for '{k8s_name}', skipping commit.")

def delete_git_resource(name):
    if not name:
        return
        
    repo = sync_git_repo()
    k8s_name = str(name).lower().replace("_", "-").replace(" ", "-")
    file_path = Path(GIT_CLONE_DIR) / "resources" / "appconfigs" / f"{k8s_name}.json"
    
    if file_path.exists():
        print(f"[GIT RENDERER] Removing AppConfig '{k8s_name}' from {file_path}")
        repo.index.remove([str(file_path.absolute())], working_tree=True)
        repo.index.commit(f"Auto-delete AppConfig: {k8s_name}")
        repo.remote(name='origin').push()
        print(f"[GIT RENDERER] Successfully removed and pushed '{k8s_name}' to Git.")
    else:
        print(f"[GIT RENDERER] File for '{k8s_name}' does not exist. Skipping delete.")

def apply_custom_resource(api_instance, data):
    name = data.get("name")
    k8s_name = str(name).lower().replace("_", "-").replace(" ", "-")
    
    cr = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "AppConfig",
        "metadata": {
            "name": k8s_name,
            "namespace": NAMESPACE
        },
        "spec": {
            "id": data.get("id"),
            "name": name,
            "repository_url": data.get("repository_url"),
            "branch": data.get("branch"),
            "environment": data.get("environment")
        }
    }
    
    try:
        api_instance.get_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL,
            name=k8s_name
        )
        cr["metadata"]["resourceVersion"] = "" # Allow patch
        api_instance.patch_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL,
            name=k8s_name,
            body=cr
        )
        print(f"Updated CR: {k8s_name}")
    except ApiException as e:
        if e.status == 404:
            api_instance.create_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL,
                body=cr
            )
            print(f"Created CR: {k8s_name}")
        else:
            print(f"Error checking/updating CR: {e}")

def delete_custom_resource(api_instance, name):
    k8s_name = str(name).lower().replace("_", "-").replace(" ", "-")
    
    try:
        api_instance.delete_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL,
            name=k8s_name
        )
        print(f"Deleted CR: {k8s_name}")
    except ApiException as e:
        if e.status == 404:
            print(f"CR already deleted: {k8s_name}")
        else:
            print(f"Error deleting CR: {e}")

app = FastAPI()
api_instance = None

@app.on_event("startup")
def startup_event():
    global api_instance
    api_instance = init_k8s_client()
    print("FastAPI server started. K8s client initialized.")

@app.post("/sync")
async def sync_endpoint(request: Request):
    """
    Receives events from Kafka Connect HTTP Sink POST.
    Payload will be the actual Debezium event (a list of them or a single object).
    """
    try:
        body = await request.json()
        
        # Confluent HTTP Sink Connector by default sends a JSON array of Kafka values
        if isinstance(body, list):
            for event in body:
                process_cdc_event(api_instance, event)
        else:
            process_cdc_event(api_instance, body)
            
        return {"status": "ok"}
    except Exception as e:
        print(f"Error processing HTTP payload: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
