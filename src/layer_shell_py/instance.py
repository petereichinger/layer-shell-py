from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from os import environ, getuid, kill
from pathlib import Path
from re import fullmatch
from signal import SIGTERM
from socket import AF_UNIX, SOCK_STREAM, socket
from subprocess import DEVNULL, Popen
from sys import argv
from time import monotonic, sleep


class InstanceAction(StrEnum):
    PRELOAD = "preload"
    START = "start"
    STOP = "stop"
    TOGGLE = "toggle"
    QUIT = "quit"


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

    @property
    def socket_path(self) -> Path:
        return _runtime_dir() / f"{self.effect}-{self.instance_id}.sock"


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
) -> int:
    instance = Instance(effect=effect, instance_id=validate_instance_id(instance_id))

    if action is InstanceAction.PRELOAD:
        return ensure_resident(
            instance,
            child_args,
            initial_visible=False,
            command=None,
        )

    if action is InstanceAction.START:
        return ensure_resident(
            instance,
            child_args,
            initial_visible=True,
            command="show",
        )

    if action is InstanceAction.TOGGLE:
        return ensure_resident(
            instance,
            child_args,
            initial_visible=True,
            command="toggle",
        )

    if action is InstanceAction.STOP:
        return send_command(instance, "hide", missing_ok=True)

    if action is InstanceAction.QUIT:
        return quit_instance(instance)

    msg = f"Unsupported instance action: {action}"
    raise InstanceError(msg)


def ensure_resident(
    instance: Instance,
    child_args: list[str],
    *,
    initial_visible: bool,
    command: str | None,
) -> int:
    if is_instance_running(instance):
        if command is not None:
            return send_command(instance, command, missing_ok=False)
        return 0

    instance.pid_path.parent.mkdir(parents=True, exist_ok=True)
    instance.socket_path.unlink(missing_ok=True)
    log_file = instance.log_path.open("ab")
    resident_args = [
        *child_args,
        "--resident",
        "--socket-path",
        str(instance.socket_path),
    ]
    if initial_visible:
        resident_args.append("--initial-visible")
    process = Popen(
        [argv[0], *resident_args],
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=log_file,
        start_new_session=True,
    )
    log_file.close()
    instance.pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    return 0


def quit_instance(instance: Instance) -> int:
    if not is_instance_running(instance):
        _remove_stale_pid(instance)
        return 0

    if _try_send_command(instance, "quit"):
        instance.pid_path.unlink(missing_ok=True)
        instance.socket_path.unlink(missing_ok=True)
        return 0

    pid = _read_active_pid(instance)
    if pid is None:
        _remove_stale_pid(instance)
        return 0

    kill(pid, SIGTERM)
    instance.pid_path.unlink(missing_ok=True)
    instance.socket_path.unlink(missing_ok=True)
    return 0


def send_command(instance: Instance, command: str, *, missing_ok: bool) -> int:
    if not is_instance_running(instance):
        if missing_ok:
            _remove_stale_pid(instance)
            return 0
        msg = f"No running {instance.effect} instance: {instance.instance_id}"
        raise InstanceError(msg)

    if _try_send_command(instance, command):
        return 0

    instance.socket_path.unlink(missing_ok=True)
    if not is_instance_running(instance):
        _remove_stale_pid(instance)
    if missing_ok:
        return 0

    msg = f"Could not reach {instance.effect} instance: {instance.instance_id}"
    raise InstanceError(msg)


def _try_send_command(instance: Instance, command: str) -> bool:
    deadline = monotonic() + 1.0
    while True:
        try:
            with socket(AF_UNIX, SOCK_STREAM) as client:
                client.connect(str(instance.socket_path))
                client.sendall(f"{command}\n".encode())
            return True
        except OSError:
            if monotonic() >= deadline:
                return False
            sleep(0.01)


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
    instance.socket_path.unlink(missing_ok=True)


def _runtime_dir() -> Path:
    if xdg_runtime_dir := environ.get("XDG_RUNTIME_DIR"):
        return Path(xdg_runtime_dir) / "layer-shell-py"

    return Path("/tmp") / f"layer-shell-py-{getuid()}"
