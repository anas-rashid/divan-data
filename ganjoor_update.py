#!/usr/bin/env python3
"""Take Ganjoor's newer data for the poets Divan tracks (ganjoor.json): run monthly on the server (divan-ganjoor.timer).

Fetches ganjoor-data's latest main, compares it with the pinned commit for our poets' folders only, and when any of
them changed, moves the pin to the new commit with a summary of the changes per poet. With --commit it also commits and
pushes that to divan-data; the next nightly sync then rebuilds the Persian works from it. Without --commit it only
reports (a dry run).
    python3 ganjoor_update.py [--commit]"""
import collections, json, os, subprocess, sys
import ganjoor

D = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(D, "ganjoor.json")


def git(*a, cwd=ganjoor.REPO):
    return subprocess.run(["git", "-C", cwd, *a], check=True, capture_output=True, text=True).stdout.strip()


def main(commit):
    ganjoor.checkout()  # the pinned commit, our poets' folders only
    git("fetch", "-q", "--filter=blob:none", "origin", "main")
    pinned, latest = ganjoor.CFG["commit"], git("rev-parse", "FETCH_HEAD")
    if latest == pinned:
        print(f"Ganjoor: no new commit (still {pinned[:9]})")
        return
    paths = [f"poets/{s}" for s in ganjoor.slugs()]
    changes = git("diff", "--name-status", pinned, latest, "--", *paths).splitlines()
    if not changes:
        print(f"Ganjoor: {latest[:9]} changes none of our {len(paths)} poets; keeping {pinned[:9]}")
        return
    per = collections.defaultdict(collections.Counter)
    for line in changes:
        status, path = line.split("\t")[0][0], line.split("\t")[-1]
        per[path.split("/")[1]][{"A": "new", "D": "removed"}.get(status, "changed")] += 1
    summary = "\n".join(f"- {slug}: " + ", ".join(f"{n} {k}" for k, n in sorted(c.items())) for slug, c in sorted(per.items()))
    date = git("show", "-s", "--format=%cs", latest)
    print(f"Ganjoor: {pinned[:9]} -> {latest[:9]} ({date}), {len(changes)} files for {len(per)} poets\n{summary}")
    cfg = json.load(open(CFG_PATH, encoding="utf-8"))
    cfg["commit"] = latest
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2); f.write("\n")
    if commit:
        msg = (f"Ganjoor update to {latest[:9]} ({date}): {len(changes)} files for {len(per)} poets\n\n{summary}\n\n"
               "Ganjoor's files, which also hold their summaries and HTML (not used by Divan); the poems' own changes show in the\n"
               "next nightly sync's commit.\n")
        git("add", "ganjoor.json", cwd=D)
        git("-c", "user.name=Divan server", "-c", "user.email=divan-server@users.noreply.divan", "commit", "-q", "-m", msg, cwd=D)
        git("push", "-q", "origin", "HEAD", cwd=D)
        print("committed and pushed; the nightly sync rebuilds the Persian works from it")


if __name__ == "__main__":
    main("--commit" in sys.argv)
