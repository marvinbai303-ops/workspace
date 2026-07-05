#!/usr/bin/env python3
"""Parallel chunked downloader for the turbo model.bin via hf-mirror (stdlib
only), with sha256 verification and HF cache symlink creation."""
import os, sys, time, hashlib, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

MIRROR = ("https://hf-mirror.com/mobiuslabsgmbh/faster-whisper-large-v3-turbo"
          "/resolve/main/model.bin")
BLOB_DIR = os.path.expanduser(
    "~/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/blobs")
SNAP = os.path.expanduser(
    "~/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo"
    "/snapshots/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf")
SHA = "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da"
BLOB = os.path.join(BLOB_DIR, SHA)
NCHUNK = 16
UA = {"User-Agent": "curl/8.0"}

def _open(url, rng=None, timeout=60):
    h = dict(UA)
    if rng:
        h["Range"] = f"bytes={rng[0]}-{rng[1]}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)

def resolve_url():
    r = _open(MIRROR, rng=(0, 0), timeout=30)
    size = None
    cr = r.headers.get("Content-Range")
    if cr and "/" in cr:
        size = int(cr.split("/")[-1])
    final = r.geturl()
    r.read(); r.close()
    return final, size

def dl_chunk(url, idx, start, end, buf, progress):
    for attempt in range(6):
        try:
            r = _open(url, rng=(start, end))
            pos = start
            while True:
                blk = r.read(1 << 20)
                if not blk:
                    break
                buf[pos:pos+len(blk)] = blk
                pos += len(blk)
                progress[idx] = pos - start
            r.close()
            if progress[idx] >= (end - start + 1):
                return
        except Exception as e:
            print(f"  chunk {idx} retry {attempt}: {e}", flush=True)
            time.sleep(2)
    raise RuntimeError(f"chunk {idx} incomplete")

def main():
    final, size = resolve_url()
    if not size:
        size = 1617884929
    print(f"resolved -> {final[:80]}...\nsize={size} ({size/1e9:.2f}GB), "
          f"{NCHUNK} parallel chunks", flush=True)
    buf = bytearray(size)
    chunk = (size + NCHUNK - 1) // NCHUNK
    ranges = [(i, i*chunk, min(i*chunk+chunk-1, size-1))
              for i in range(NCHUNK) if i*chunk <= size-1]
    progress = [0]*len(ranges)
    t0 = time.time(); stop = threading.Event()
    def reporter():
        while not stop.is_set():
            done = sum(progress); el = time.time()-t0
            print(f"  {done/1e6:7.1f}/{size/1e6:.1f} MB ({100*done/size:5.1f}%) "
                  f"{done/1e6/max(el,1e-9):5.2f} MB/s {el:5.0f}s", flush=True)
            stop.wait(10)
    threading.Thread(target=reporter, daemon=True).start()
    with ThreadPoolExecutor(max_workers=NCHUNK) as ex:
        futs = [ex.submit(dl_chunk, final, i, s, e, buf, progress)
                for (i, s, e) in ranges]
        for f in as_completed(futs):
            f.result()
    stop.set(); el = time.time()-t0
    print(f"downloaded in {el:.0f}s ({size/1e6/el:.2f} MB/s avg)", flush=True)
    print("verifying sha256...", flush=True)
    got = hashlib.sha256(buf).hexdigest()
    if got != SHA:
        print(f"SHA MISMATCH got {got}", flush=True); sys.exit(1)
    print("sha256 OK", flush=True)
    with open(BLOB, "wb") as f:
        f.write(buf)
    link = os.path.join(SNAP, "model.bin")
    if os.path.islink(link) or os.path.exists(link):
        os.remove(link)
    os.symlink(os.path.relpath(BLOB, SNAP), link)
    for fn in os.listdir(BLOB_DIR):
        if fn.endswith(".incomplete"):
            os.remove(os.path.join(BLOB_DIR, fn))
    print(f"DONE -> {link}", flush=True)

if __name__ == "__main__":
    main()
