from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from os import environ, getuid, kill
from pathlib import Path
from re import fullmatch
from signal import SIGTERM
from subprocess import DEVNULL, Popen
from sys import argv


class InstanceAction(StrEnum):
    FOREGROUND = "foreground"
    START = "start"
    STOP = "stop"
    TOGGLE = "toggle"


class InstanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Instance:
    effect: str
    instance_id: str

    @property
    def pid_path(self) -> Path:
        return _runtime_dir() / f"{self.effect}-{self.instance_id}.pid"

    @property
    def log_path(self) -> Path:
        return _runtime_dir() / f"{self.effect}-{self.instance_id}.log"


def validate_instance_id(instance_id: str) -> str:
    if fullmatch(r"[A-Za-z0-9_.-]+", instance_id) is None:
        msg = (
            "Instance id may only contain letters, numbers, dots, underscores, "
            "and hyphens."
        )
        raise InstanceError(msg)
    return instance_id


def manage_instance(
    *,
    action: InstanceAction,
    effect: str,
    instance_id: str,
    child_args: list[str],
) -> int | None:
    if action is InstanceAction.FOREGROUND:
        return None

    instance = Instance(effect=effect, instance_id=validate_instance_id(instance_id))

    if action is InstanceAction.START:
        return start_instance(instance, child_args)

    if action is InstanceAction.STOP:
        return stop_instance(instance)

    if is_instance_running(instance):
        return stop_instance(instance)

    return start_instance(instance, child_args)


def start_instance(instance: Instance, child_args: list[str]) -> int:
    if is_instance_running(instance):
        return 0

    instance.pid_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = instance.log_path.open("ab")
    process = Popen(
        [argv[0], *child_args],
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=log_file,
        start_new_session=True,
    )
    log_file.close()
    instance.pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    return 0


def stop_instance(instance: Instance) -> int:
    pid = _read_active_pid(instance)
    if pid is None:
        _remove_stale_pid(instance)
        return 0

    kill(pid, SIGTERM)
    instance.pid_path.unlink(missing_ok=True)
    return 0


def is_instance_running(instance: Instance) -> bool:
    return _read_active_pid(instance) is not None


def _read_active_pid(instance: Instance) -> int | None:
    try:
        pid = int(instance.pid_path.read_text(encoding="utf-8").strip())
    except FileNotFoundError, ValueError:
        return None

    if pid <= 0 or not _pid_exists(pid) or not _pid_looks_managed(pid, instance.effect):
        return None

    return pid


def _pid_exists(pid: int) -> bool:
    try:
        kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid_looks_managed(pid: int, effect: str) -> bool:
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    if not cmdline_path.exists():
        return True

    try:
        cmdline = cmdline_path.read_bytes().decode(errors="replace")
    except OSError:
        return False

    return "layer-shell-py" in cmdline and effect in cmdline


def _remove_stale_pid(instance: Instance) -> None:
    instance.pid_path.unlink(missing_ok=True)


def _runtime_dir() -> Path:
    if xdg_runtime_dir := environ.get("XDG_RUNTIME_DIR"):
        return Path(xdg_runtime_dir) / "layer-shell-py"

    return Path("/tmp") / f"layer-shell-py-{getuid()}"
