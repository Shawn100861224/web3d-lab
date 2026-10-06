#!/usr/bin/env python3
"""AutoDL 云主机的非交互 SSH/SFTP 小工具（密码经环境变量传入，避免在日志里出现）。

用法:
    CLOUD_PW=xxx python cloud_ssh.py info
    CLOUD_PW=xxx python cloud_ssh.py run "nvidia-smi"
    CLOUD_PW=xxx python cloud_ssh.py put <本地路径> <远端路径>
    CLOUD_PW=xxx python cloud_ssh.py get <远端路径> <本地路径>
    CLOUD_PW=xxx python cloud_ssh.py tail <远端日志> [行数]
"""
from __future__ import annotations

import os
import sys
import time

import paramiko

HOST = os.environ.get("CLOUD_HOST", "connect.westc.seetacloud.com")
PORT = int(os.environ.get("CLOUD_PORT", "11065"))
USER = os.environ.get("CLOUD_USER", "root")
PW = os.environ.get("CLOUD_PW")


def connect() -> paramiko.SSHClient:
    if not PW:
        sys.exit("缺少 CLOUD_PW 环境变量")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PW,
              timeout=25, banner_timeout=25, auth_timeout=25,
              look_for_keys=False, allow_agent=False)
    return c


def run(c, cmd: str, timeout: int = 300):
    _in, out, err = c.exec_command(cmd, timeout=timeout)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    rc = out.channel.recv_exit_status()
    return rc, o, e


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    action = sys.argv[1]
    c = connect()
    try:
        if action == "info":
            for cmd in [
                "hostname; nproc; free -g | head -2",
                "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader",
                "python -V; python -c 'import torch;print(\"torch\",torch.__version__,\"cuda\",torch.version.cuda,\"avail\",torch.cuda.is_available())' 2>&1 | tail -2",
                "which nvcc; nvcc --version 2>/dev/null | tail -2",
                "python -c 'import gsplat;print(\"gsplat ok\",gsplat.__version__)' 2>&1 | tail -1",
                "df -h /root | tail -1",
            ]:
                rc, o, e = run(c, cmd)
                print(f"$ {cmd}\n{o.rstrip()}\n{e.rstrip()}\n")
        elif action == "run":
            rc, o, e = run(c, sys.argv[2], timeout=int(os.environ.get("CLOUD_TIMEOUT", "300")))
            print(o)
            if e.strip():
                print("[stderr]", e[-2000:], file=sys.stderr)
            print("[exit]", rc)
        elif action == "put":
            local, remote = sys.argv[2], sys.argv[3]
            sf = c.open_sftp()
            t0 = time.time()
            if os.path.isdir(local):
                # 递归上传
                for root, _dirs, files in os.walk(local):
                    rel = os.path.relpath(root, local)
                    rdir = remote if rel == "." else remote + "/" + rel.replace("\\", "/")
                    run(c, f"mkdir -p {rdir!r}")
                    for f in files:
                        sf.put(os.path.join(root, f), rdir + "/" + f)
                        print("  ↑", rdir + "/" + f)
            else:
                sf.put(local, remote)
                print("  ↑", local, "->", remote)
            sf.close()
            print("上传完成 %.1fs" % (time.time() - t0))
        elif action == "get":
            remote, local = sys.argv[2], sys.argv[3]
            sf = c.open_sftp()
            sf.get(remote, local)
            sf.close()
            print("  ↓", remote, "->", local, os.path.getsize(local), "bytes")
        elif action == "tail":
            path = sys.argv[2]
            n = sys.argv[3] if len(sys.argv) > 3 else "20"
            rc, o, e = run(c, f"tail -n {n} {path!r} 2>&1; echo '---- uptime:'; uptime")
            print(o)
        else:
            print("未知动作", action)
            return 2
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
