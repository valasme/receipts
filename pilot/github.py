"""Opt-in GitHub adapter for the Receipts public demo repository."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote

MARKER = "<!-- receipts:public-demo:v1 -->"
CONSENT = "receipts:publish"
STALE = MARKER + "\nPreviously checked input changed. The previous receipt is stale."
DEMO = "valasme/receipts"

class ApiFailure(Exception):
    pass

class GitHub:
    def __init__(self, repository):
        if repository != DEMO:
            raise ValueError("pilot restricted to the public demo")
        self.base = "repos/" + repository

    def request(self, method, path, payload=None):
        args = ["gh","api","-X",method,self.base+path]
        data = None
        if payload is not None:
            args += ["--input","-"]
            data = json.dumps(payload).encode()
        try:
            result = subprocess.run(args,input=data,capture_output=True,timeout=20)
        except (OSError,subprocess.TimeoutExpired) as err:
            raise ApiFailure("GitHub API unavailable") from err
        if result.returncode:
            raise ApiFailure("GitHub API request failed")
        return json.loads(result.stdout) if result.stdout.strip() else None

def source(api, number):
    issue = api.request("GET",f"/issues/{number}")
    head = None
    if "pull_request" in issue:
        head = api.request("GET",f"/pulls/{number}")["head"]["sha"]
    body = issue.get("body") or ""
    digest = hashlib.sha256(json.dumps([number,body,head,issue["state"]]).encode()).hexdigest()
    consent = CONSENT in {label["name"] for label in issue["labels"]}
    if len(body.encode()) > 65536 or issue["state"] != "open":
        return digest, None, consent
    blocks = re.findall(r"^```receipts\r?\n(.*?)\r?\n```[ \t]*\r?$",body,re.MULTILINE|re.DOTALL)
    if len(blocks)!=1:
        return digest,None,consent
    try:
        claim = json.loads(blocks[0])
    except (ValueError,RecursionError):
        return digest,None,consent
    if not isinstance(claim,dict) or set(claim)!={"rev","path","quote"} or not all(isinstance(x,str) for x in claim.values()):
        return digest,None,consent
    if head and claim["rev"] != head:
        return digest,None,consent
    return digest,claim,consent

def existing(api, number):
    found=[]
    for page in range(1,5):
        comments=api.request("GET",f"/issues/{number}/comments?per_page=100&page={page}")
        found.extend(c for c in comments if c.get("user",{}).get("login")=="github-actions[bot]"
                     and c.get("user",{}).get("type")=="Bot" and c.get("body","").startswith(MARKER+"\n"))
        if len(comments)<100:
            if len(found)>1: raise ApiFailure("multiple publisher comments; reconcile manually")
            return found[0] if found else None
    raise ApiFailure("comment scan exceeded budget")

def render(claim, executable):
    if claim is None: return None
    try:
        text=claim["quote"].encode()
        p=subprocess.run([executable,"check","--repo",".","--rev",claim["rev"],"--path",claim["path"],
                          "--quote-file","-","--format","markdown"],input=text,capture_output=True,timeout=8,
                         env={k:os.environ[k] for k in ("PATH","SystemRoot") if k in os.environ})
    except (ValueError,UnicodeError):
        return None
    if p.returncode==2: return None
    if p.returncode!=0 or len(p.stdout)>8192: raise ApiFailure("checker failed")
    return p.stdout.decode("utf-8").replace("@","@\u200b")

def publish(api,number,check):
    digest,claim,consent=source(api,number)
    receipt=check(claim)
    old=existing(api,number)
    if not old and not (consent and receipt): return "suppressed or empty"
    desired=MARKER+"\n"+receipt+"\nInput digest: "+digest if receipt else STALE
    if old and old["body"]==desired: return "current"
    if source(api,number)[0]!=digest: return "superseded"
    if old:
        path=f"/issues/comments/{int(old['id'])}"
        api.request("PATCH",path,{"body":desired})
    else:
        # Consume the owner's one-time publish label before attempting a create.
        # A deleted comment or ambiguous timeout cannot cause an automatic repost.
        api.request("DELETE",f"/issues/{number}/labels/"+quote(CONSENT,safe=""))
        if source(api,number)[0]!=digest: return "superseded"
        try:
            created=api.request("POST",f"/issues/{number}/comments",{"body":desired})
        except ApiFailure:
            created=existing(api,number)
            if not created or created["body"]!=desired: raise
        path=f"/issues/comments/{int(created['id'])}"
    if source(api,number)[0]!=digest:
        api.request("PATCH",path,{"body":STALE})
        return "stale"
    return "updated"

def main():
    api=GitHub(os.environ["GITHUB_REPOSITORY"])
    if api.request("GET","")["private"]: raise ApiFailure("public demo required")
    number=int(os.environ["SUBMISSION"])
    if number<1: raise ValueError("invalid submission")
    exe=str(Path("receipts-pilot").resolve())
    if sys.argv[1]=="preview":
        _,claim,_=source(api,number)
        receipt=render(claim,exe)
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:
            f.write(receipt or "No supported exact-quote claim at this revision.\n")
    elif sys.argv[1]=="publish":
        print(publish(api,number,lambda claim:render(claim,exe)))
    else: raise ValueError("invalid mode")

if __name__=="__main__":
    try:
        main()
    except (ApiFailure,ValueError,OSError,subprocess.TimeoutExpired):
        sys.exit("Pilot stopped. Check the run permissions, event revision and service availability.")
