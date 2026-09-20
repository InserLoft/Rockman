# Rockman Benchmark v0.2 - Security & Sandbox Architecture

## Overview

This document describes the security architecture for code execution in Rockman, including the container-based sandbox, resource limits, and threat model.

## Threat Model

### Assumptions

1. **Submitted code is untrusted** - May be malicious, buggy, or resource-exhaustive
2. **Evaluation server is trusted** - Runs the sandbox infrastructure
3. **Network is untrusted** - No outbound connections from sandbox
4. **Host kernel is trusted** - Container escape mitigated by seccomp/apparmor

### Attack Vectors Addressed

| Vector | Mitigation |
|--------|------------|
| Infinite loops | CPU time limits, wall-clock timeout |
| Memory exhaustion | cgroup memory limit, OOM killer |
| Fork bombs | pids_limit cgroup |
| Filesystem abuse | Read-only root, tmpfs with quota |
| Network access | Network namespace disabled |
| Host escape | seccomp profile, non-root user, no privileged caps |
| Side channels | Resource isolation, no shared state |
| Crypto mining | CPU quota, execution time limit |

## Sandbox Architecture

### Container Runtime

**Default**: Docker with containerd
**Alternative**: gVisor, Kata Containers for stronger isolation

### Container Configuration

```json
{
  "image": "rockman-sandbox:latest",
  "user": "nobody (UID 65534)",
  "working_dir": "/workspace",
  "network_mode": "none",
  "read_only_rootfs": true,
  "tmpfs": {"/tmp": "size=64m"},
  "cpu_quota": 100000,
  "cpu_period": 100000,
  "mem_limit": "256m",
  "memswap_limit": "256m",
  "pids_limit": 64,
  "cap_drop": ["ALL"],
  "security_opt": ["no-new-privileges:true"]
}
```

### Security Options Explained

| Option | Purpose |
|--------|---------|
| `network_mode: none` | No network interfaces (not even loopback) |
| `read_only_rootfs` | Prevents filesystem modification |
| `tmpfs` | Writable space with strict size limit |
| `cpu_quota/period` | CFS quota: 1.0 CPU core max |
| `mem_limit/memswap` | Hard memory limit, no swap |
| `pids_limit` | Prevents fork bombs |
| `cap_drop: ALL` | Removes all Linux capabilities |
| `no-new-privileges` | Prevents privilege escalation via setuid |
| `user: nobody` | Runs as unprivileged UID 65534 |

### Seccomp Profile (Recommended)

Default Docker seccomp profile blocks:
- `clone` (with CLONE_NEWUSER/CLONE_NEWNS)
- `keyctl`, `add_key`, `request_key`
- `ptrace`
- `mount`, `umount`, `pivot_root`
- `reboot`, `kexec_load`
- `vsyscall` related syscalls

Custom profile can further restrict:
- `execve` (allow only whitelisted binaries)
- `open` (restrict paths)

### AppArmor Profile (Optional)

```apparmor
profile rockman-sandbox {
  #include <abstractions/base>
  deny network,
  deny capability,
  deny mount,
  file /workspace/** rw,
  file /tmp/** rw,
  /usr/bin/python3 ix,
  /usr/bin/g++ ix,
  /usr/bin/java ix,
  /usr/bin/node ix,
  /usr/bin/go ix,
  /usr/bin/rustc ix,
}
```

## Resource Limits

### Default Limits

| Resource | Default | Max Configurable |
|----------|---------|------------------|
| Wall-clock time | 30s | 300s |
| CPU time | 2s | 60s |
| Memory | 256 MB | 4 GB |
| Processes | 64 | 1024 |
| File descriptors | 256 | 1024 |
| Disk (tmpfs) | 64 MB | 1 GB |
| Output (stdout/stderr) | 10 MB | 100 MB |

### Per-Problem Overrides

Problems can specify custom limits:
```json
{
  "time_limit": 5.0,
  "memory_limit": 512,
  "timeout_override": 10.0,
  "memory_override": 1024
}
```

### Enforcement

- **Time**: `timeout` command + container stop timeout
- **CPU**: cgroup `cpu.cfs_quota_us`
- **Memory**: cgroup `memory.limit_in_bytes`
- **Processes**: cgroup `pids.max`
- **Output**: Streaming with size limit

## Language-Specific Security

### Python

- No `import os`, `subprocess`, `sys`, `builtins` manipulation
- Restricted builtins via `__builtins__ = {}`
- `resource.setrlimit` for additional limits

### C/C++

- Static linking (`-static`) prevents library injection
- `-fstack-protector-strong`, `-D_FORTIFY_SOURCE=2`
- No inline assembly in user code (validated)

### Java

- SecurityManager (legacy) or `--add-opens` restrictions
- `-XX:+UseSerialGC` to limit GC threads
- Classpath isolation

### JavaScript/Node.js

- `--no-warnings`, `--disallow-code-generation-from-strings`
- `vm2` sandbox for additional isolation
- Resource limits via `--max-old-space-size`

### Rust

- No `unsafe` in user code (linted)
- Static linking preferred
- Panic=abort to prevent unwinding attacks

### Go

- `-ldflags="-s -w"` strips debug info
- No cgo (`CGO_ENABLED=0`)
- Build tags to exclude dangerous packages

## Execution Flow

```
1. Receive source code + problem metadata
2. Validate language, create temp directory
3. Write source to /workspace/main.{ext}
4. Create container with security config
5. Start container with compile+run command
6. Stream stdout/stderr with size limits
7. Monitor for timeout/OOM/crash
8. Collect exit code, logs, stats
9. Clean up container (force remove)
10. Return ExecutionResult
```

## Image Management

### Base Image

```dockerfile
FROM ubuntu:22.04

# Install languages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    openjdk-17-jdk-headless \
    nodejs npm \
    golang-go \
    rustc cargo \
    g++ make \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash nobody

WORKDIR /workspace
USER nobody
```

### Image Security

- Pinned base image digest: `ubuntu@sha256:...`
- No package managers in final image
- Minimal attack surface
- Regular rebuild for security updates
- Signed images with cosign/notary

### Pre-built Images

| Image | Size | Languages |
|-------|------|-----------|
| `rockman-sandbox:minimal` | ~1.2GB | Python only |
| `rockman-sandbox:standard` | ~2.5GB | Python, C++, Java, Node.js |
| `rockman-sandbox:full` | ~4.1GB | All 6 languages |

## Monitoring & Logging

### Metrics Collected

- Execution time (wall-clock, CPU)
- Peak memory usage
- Exit code, signals
- OOM killed flag
- Container start/stop latency

### Audit Logging

All executions logged:
```json
{
  "timestamp": "2024-09-19T...",
  "task_id": "Rockman/DP_041",
  "language": "python",
  "user": "api-key-hash",
  "result": "success",
  "execution_time_ms": 45,
  "memory_mb": 12,
  "exit_code": 0
}
```

### Alerting

- OOM kills > 1% rate
- Timeouts > 5% rate
- Container crashes
- Image pull failures

## Alternative Runtimes

### gVisor (runsc)

```bash
docker run --runtime=runsc ...
```

- User-space kernel, stronger isolation
- ~10-20% performance overhead
- Limited syscall support (some languages affected)

### Kata Containers

```bash
docker run --runtime=kata ...
```

- Lightweight VM per container
- Hardware virtualization isolation
- Higher overhead, best for multi-tenant

### Firecracker

- MicroVM per execution
- Used by AWS Lambda
- Fast startup (~125ms), strong isolation

## Deployment Checklist

### Host Hardening

- [ ] Kernel: `kernel.unprivileged_userns_clone=0`
- [ ] Kernel: `kernel.yama.ptrace_scope=1`
- [ ] AppArmor/SELinux enforcing
- [ ] Docker daemon: `no-new-privileges`, `live-restore`
- [ ] Log rotation for container logs
- [ ] Disk quotas on `/var/lib/docker`

### Network

- [ ] Docker bridge isolated from host network
- [ ] No exposed ports on sandbox containers
- [ ] Egress firewall rules (deny all by default)

### Monitoring

- [ ] Prometheus metrics for container resources
- [ ] Alert on OOM/timeout rates
- [ ] Audit log aggregation
- [ ] Image vulnerability scanning (trivy, grype)

### Incident Response

- [ ] Container escape playbook
- [ ] Image rollback procedure
- [ ] Compromise indicators
- [ ] Forensic image capture

## References

- Docker Security: https://docs.docker.com/engine/security/
- Cgroups v2: https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html
- Seccomp: https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html
- gVisor: https://gvisor.dev/
- Kata Containers: https://katacontainers.io/