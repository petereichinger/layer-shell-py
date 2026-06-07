use std::env;
use std::fmt::{self, Display};
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::os::unix::net::UnixStream;
use std::os::unix::process::CommandExt;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::thread::sleep;
use std::time::{Duration, Instant};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InstanceAction {
    Preload,
    Show,
    Hide,
    Toggle,
    Quit,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Instance {
    pub effect: String,
    pub instance_id: String,
}

impl Instance {
    pub fn new(effect: impl Into<String>, instance_id: impl Into<String>) -> Self {
        Self {
            effect: effect.into(),
            instance_id: instance_id.into(),
        }
    }

    pub fn pid_path(&self) -> PathBuf {
        runtime_dir().join(format!("{}-{}.pid", self.effect, self.instance_id))
    }

    pub fn log_path(&self) -> PathBuf {
        runtime_dir().join(format!("{}-{}.log", self.effect, self.instance_id))
    }

    pub fn socket_path(&self) -> PathBuf {
        runtime_dir().join(format!("{}-{}.sock", self.effect, self.instance_id))
    }
}

pub fn validate_instance_id(instance_id: &str) -> Result<(), InstanceError> {
    if instance_id.is_empty()
        || !instance_id
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '-'))
    {
        return Err(InstanceError::InvalidInstanceId);
    }

    Ok(())
}

pub fn manage_instance(
    action: InstanceAction,
    effect: &str,
    instance_id: &str,
    child_args: &[String],
) -> Result<i32, InstanceError> {
    validate_instance_id(instance_id)?;
    let instance = Instance::new(effect, instance_id);

    match action {
        InstanceAction::Preload => ensure_resident(&instance, child_args, false, None),
        InstanceAction::Show => ensure_resident(&instance, child_args, true, Some("show")),
        InstanceAction::Toggle => ensure_resident(&instance, child_args, true, Some("toggle")),
        InstanceAction::Hide => send_command(&instance, "hide", true),
        InstanceAction::Quit => quit_instance(&instance),
    }
}

pub fn ensure_resident(
    instance: &Instance,
    child_args: &[String],
    initial_visible: bool,
    command: Option<&str>,
) -> Result<i32, InstanceError> {
    if is_instance_running(instance) {
        if let Some(command) = command {
            return send_command(instance, command, false);
        }
        return Ok(0);
    }

    fs::create_dir_all(
        instance
            .pid_path()
            .parent()
            .expect("runtime paths always have parents"),
    )?;
    let _ = fs::remove_file(instance.socket_path());

    let log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(instance.log_path())?;

    let current_exe = env::current_exe()?;
    let mut resident_args = child_args.to_vec();
    resident_args.extend([
        "--resident".to_string(),
        "--socket-path".to_string(),
        instance.socket_path().display().to_string(),
    ]);
    if initial_visible {
        resident_args.push("--initial-visible".to_string());
    }

    let mut child_command = Command::new(current_exe);
    child_command
        .args(resident_args)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::from(log_file));

    // Match Python's start_new_session=True so resident instances survive
    // short-lived CLI invocations cleanly.
    unsafe {
        child_command.pre_exec(|| {
            if libc::setsid() == -1 {
                return Err(io::Error::last_os_error());
            }
            Ok(())
        });
    }

    let child = child_command.spawn()?;
    fs::write(instance.pid_path(), format!("{}\n", child.id()))?;
    eprintln!(
        "Started {effect} instance {instance_id} as PID {pid}. Log: {log}. Socket: {socket}",
        effect = instance.effect,
        instance_id = instance.instance_id,
        pid = child.id(),
        log = instance.log_path().display(),
        socket = instance.socket_path().display(),
    );
    Ok(0)
}

pub fn quit_instance(instance: &Instance) -> Result<i32, InstanceError> {
    if !is_instance_running(instance) {
        remove_stale_pid(instance);
        return Ok(0);
    }

    if try_send_command(instance, "quit") {
        remove_stale_pid(instance);
        return Ok(0);
    }

    if let Some(pid) = read_active_pid(instance) {
        unsafe {
            libc::kill(pid, libc::SIGTERM);
        }
    }
    remove_stale_pid(instance);
    Ok(0)
}

pub fn send_command(
    instance: &Instance,
    command: &str,
    missing_ok: bool,
) -> Result<i32, InstanceError> {
    if !is_instance_running(instance) {
        if missing_ok {
            remove_stale_pid(instance);
            return Ok(0);
        }
        return Err(InstanceError::NoRunningInstance {
            effect: instance.effect.clone(),
            instance_id: instance.instance_id.clone(),
        });
    }

    if try_send_command(instance, command) {
        return Ok(0);
    }

    let _ = fs::remove_file(instance.socket_path());
    if !is_instance_running(instance) {
        remove_stale_pid(instance);
    }
    if missing_ok {
        return Ok(0);
    }

    Err(InstanceError::CouldNotReachInstance {
        effect: instance.effect.clone(),
        instance_id: instance.instance_id.clone(),
    })
}

pub fn try_send_command(instance: &Instance, command: &str) -> bool {
    let deadline = Instant::now() + Duration::from_secs(1);

    loop {
        match UnixStream::connect(instance.socket_path()) {
            Ok(mut stream) => {
                let _ = writeln!(stream, "{command}");
                return true;
            }
            Err(_) if Instant::now() < deadline => sleep(Duration::from_millis(10)),
            Err(_) => return false,
        }
    }
}

pub fn is_instance_running(instance: &Instance) -> bool {
    read_active_pid(instance).is_some()
}

fn read_active_pid(instance: &Instance) -> Option<i32> {
    let pid_text = fs::read_to_string(instance.pid_path()).ok()?;
    let pid: i32 = pid_text.trim().parse().ok()?;

    if pid <= 0 || !pid_exists(pid) || !pid_looks_managed(pid, &instance.effect) {
        return None;
    }

    Some(pid)
}

fn pid_exists(pid: i32) -> bool {
    match unsafe { libc::kill(pid, 0) } {
        0 => true,
        _ => io::Error::last_os_error().raw_os_error() == Some(libc::EPERM),
    }
}

fn pid_looks_managed(pid: i32, effect: &str) -> bool {
    let cmdline_path = PathBuf::from(format!("/proc/{pid}/cmdline"));
    if !cmdline_path.exists() {
        return true;
    }

    let Ok(cmdline) = fs::read_to_string(cmdline_path) else {
        return false;
    };

    cmdline.contains("layer-shell-rs") && cmdline.contains(effect)
}

fn remove_stale_pid(instance: &Instance) {
    let _ = fs::remove_file(instance.pid_path());
    let _ = fs::remove_file(instance.socket_path());
}

pub fn runtime_dir() -> PathBuf {
    if let Some(xdg_runtime_dir) = env::var_os("XDG_RUNTIME_DIR") {
        return PathBuf::from(xdg_runtime_dir).join("layer-shell-rs");
    }

    PathBuf::from("/tmp").join(format!("layer-shell-rs-{}", unsafe { libc::getuid() }))
}

#[derive(Debug)]
pub enum InstanceError {
    InvalidInstanceId,
    NoRunningInstance { effect: String, instance_id: String },
    CouldNotReachInstance { effect: String, instance_id: String },
    Io(io::Error),
}

impl Display for InstanceError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidInstanceId => formatter.write_str(
                "Instance id may only contain letters, numbers, dots, underscores, and hyphens.",
            ),
            Self::NoRunningInstance {
                effect,
                instance_id,
            } => {
                write!(formatter, "No running {effect} instance: {instance_id}")
            }
            Self::CouldNotReachInstance {
                effect,
                instance_id,
            } => {
                write!(
                    formatter,
                    "Could not reach {effect} instance: {instance_id}"
                )
            }
            Self::Io(error) => Display::fmt(error, formatter),
        }
    }
}

impl std::error::Error for InstanceError {}

impl From<io::Error> for InstanceError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_instance_id_accepts_safe_ids() {
        validate_instance_id("fuzzel_1.2-3").unwrap();
    }

    #[test]
    fn validate_instance_id_rejects_paths() {
        assert_eq!(
            validate_instance_id("bad/id").unwrap_err().to_string(),
            "Instance id may only contain letters, numbers, dots, underscores, and hyphens."
        );
    }
}
