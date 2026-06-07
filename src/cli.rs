use crate::config::{BlurConfig, Layer, LayerSurfaceConfig, OutlineConfig};
use crate::instance::{InstanceAction, InstanceError, manage_instance};
use crate::layer_window::{run_blur, run_outline};
use clap::{Args, Parser, Subcommand};
use std::fmt::{self, Display};

#[derive(Debug, Parser)]
#[command(
    name = "layer-shell-rs",
    version,
    about = "Wayland layer-shell utility.",
    arg_required_else_help = true
)]
pub struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Show a colored fullscreen outline.
    Outline(OutlineArgs),
    /// Show a fullscreen blur target/tint.
    Blur(BlurArgs),
}

#[derive(Debug, Args)]
struct OutlineArgs {
    #[arg(
        long,
        default_value = "#ff0000",
        help = "GTK/CSS color for the outline."
    )]
    color: String,

    #[arg(
        long,
        default_value_t = 4,
        value_parser = clap::value_parser!(u32).range(1..),
        help = "Outline thickness in physical pixels."
    )]
    thickness: u32,

    #[command(flatten)]
    surface: SurfaceArgs,

    #[command(flatten)]
    instance: InstanceArgs,
}

#[derive(Debug, Args)]
struct BlurArgs {
    #[arg(
        long,
        default_value = "#00000040",
        help = "GTK/CSS color for the blur layer tint."
    )]
    color: String,

    #[command(flatten)]
    surface: BlurSurfaceArgs,

    #[command(flatten)]
    instance: InstanceArgs,
}

#[derive(Debug, Args)]
struct SurfaceArgs {
    #[arg(
        long = "ignore-exclusive-zones",
        help = "Ignore compositor-reserved areas such as bars and panels."
    )]
    ignore_exclusive_zones: bool,

    #[arg(
        long = "respect-exclusive-zones",
        help = "Respect compositor-reserved areas such as bars and panels."
    )]
    respect_exclusive_zones: bool,

    #[arg(long, value_enum, default_value_t = Layer::Overlay, help = "Wayland layer-shell layer.")]
    layer: Layer,

    #[arg(
        long,
        default_value = "layer-shell-rs",
        help = "Layer-shell namespace."
    )]
    namespace: String,

    #[arg(long, help = "Skip the Wayland session guard for development.")]
    allow_non_wayland: bool,
}

#[derive(Debug, Args)]
struct BlurSurfaceArgs {
    #[arg(
        long = "ignore-exclusive-zones",
        help = "Ignore compositor-reserved areas such as bars and panels."
    )]
    ignore_exclusive_zones: bool,

    #[arg(
        long = "respect-exclusive-zones",
        help = "Respect compositor-reserved areas such as bars and panels."
    )]
    respect_exclusive_zones: bool,

    #[arg(long, value_enum, default_value_t = Layer::Overlay, help = "Wayland layer-shell layer.")]
    layer: Layer,

    #[arg(
        long,
        default_value = "layer-shell-rs-blur",
        help = "Layer-shell namespace for matching niri layer rules."
    )]
    namespace: String,

    #[arg(long, help = "Skip the Wayland session guard for development.")]
    allow_non_wayland: bool,
}

#[derive(Debug, Args)]
struct InstanceArgs {
    #[arg(long = "id", help = "Managed instance id for show, hide, or toggle.")]
    instance_id: Option<String>,

    #[arg(long, help = "Show this managed instance.")]
    show: bool,

    #[arg(long, help = "Hide this managed instance.")]
    hide: bool,

    #[arg(long, help = "Toggle this managed instance.")]
    toggle: bool,

    #[arg(long, help = "Start this managed instance hidden.")]
    preload: bool,

    #[arg(long = "quit", help = "Quit this managed instance.")]
    quit: bool,

    #[arg(long, hide = true)]
    resident: bool,

    #[arg(long, hide = true)]
    socket_path: Option<String>,

    #[arg(long, hide = true)]
    initial_visible: bool,
}

impl SurfaceArgs {
    fn config(&self) -> Result<LayerSurfaceConfig, CliError> {
        surface_config(
            self.ignore_exclusive_zones,
            self.respect_exclusive_zones,
            self.layer,
            &self.namespace,
            self.allow_non_wayland,
        )
    }
}

impl BlurSurfaceArgs {
    fn config(&self) -> Result<LayerSurfaceConfig, CliError> {
        surface_config(
            self.ignore_exclusive_zones,
            self.respect_exclusive_zones,
            self.layer,
            &self.namespace,
            self.allow_non_wayland,
        )
    }
}

pub fn run(cli: Cli) -> Result<i32, CliError> {
    match cli.command {
        Command::Outline(args) => run_outline_command(args),
        Command::Blur(args) => run_blur_command(args),
    }
}

fn run_outline_command(args: OutlineArgs) -> Result<i32, CliError> {
    let config = OutlineConfig::new(args.surface.config()?, args.color, args.thickness)?;
    let action = instance_action(&args.instance)?;

    if args.instance.resident {
        let socket_path = args
            .instance
            .socket_path
            .as_deref()
            .ok_or(CliError::ResidentRequiresSocketPath)?;
        return run_outline(&config, socket_path, args.instance.initial_visible)
            .map_err(CliError::Runtime);
    }

    let instance_id = args.instance.instance_id.as_deref().unwrap_or("outline");
    manage_instance(action, "outline", instance_id, &outline_child_args(&config))
        .map_err(CliError::Instance)
}

fn run_blur_command(args: BlurArgs) -> Result<i32, CliError> {
    let config = BlurConfig::new(args.surface.config()?, args.color)?;
    let action = instance_action(&args.instance)?;

    if args.instance.resident {
        let socket_path = args
            .instance
            .socket_path
            .as_deref()
            .ok_or(CliError::ResidentRequiresSocketPath)?;
        return run_blur(&config, socket_path, args.instance.initial_visible)
            .map_err(CliError::Runtime);
    }

    let instance_id = args.instance.instance_id.as_deref().unwrap_or("blur");
    manage_instance(action, "blur", instance_id, &blur_child_args(&config))
        .map_err(CliError::Instance)
}

fn surface_config(
    ignore_exclusive_zones: bool,
    respect_exclusive_zones: bool,
    layer: Layer,
    namespace: &str,
    allow_non_wayland: bool,
) -> Result<LayerSurfaceConfig, CliError> {
    if ignore_exclusive_zones && respect_exclusive_zones {
        return Err(CliError::ExclusiveZoneConflict);
    }

    LayerSurfaceConfig::new(
        !respect_exclusive_zones,
        layer,
        namespace.to_string(),
        allow_non_wayland,
    )
    .map_err(CliError::Config)
}

fn instance_action(args: &InstanceArgs) -> Result<InstanceAction, CliError> {
    if args.resident {
        return Ok(InstanceAction::Preload);
    }

    let action_count = [args.show, args.hide, args.toggle, args.preload, args.quit]
        .into_iter()
        .filter(|enabled| *enabled)
        .count();

    if action_count > 1 {
        return Err(CliError::MultipleLifecycleActions);
    }
    if action_count == 0 {
        return Err(CliError::MissingLifecycleAction);
    }

    if args.preload {
        Ok(InstanceAction::Preload)
    } else if args.show {
        Ok(InstanceAction::Show)
    } else if args.hide {
        Ok(InstanceAction::Hide)
    } else if args.toggle {
        Ok(InstanceAction::Toggle)
    } else {
        Ok(InstanceAction::Quit)
    }
}

fn outline_child_args(config: &OutlineConfig) -> Vec<String> {
    let mut args = vec![
        "outline".to_string(),
        "--color".to_string(),
        config.color.clone(),
        "--thickness".to_string(),
        config.thickness.to_string(),
        "--layer".to_string(),
        config.surface.layer.to_string(),
        "--namespace".to_string(),
        config.surface.namespace.clone(),
        exclusive_zone_arg(config.surface.ignore_exclusive_zones).to_string(),
    ];

    if config.surface.allow_non_wayland {
        args.push("--allow-non-wayland".to_string());
    }

    args
}

fn blur_child_args(config: &BlurConfig) -> Vec<String> {
    let mut args = vec![
        "blur".to_string(),
        "--color".to_string(),
        config.color.clone(),
        "--layer".to_string(),
        config.surface.layer.to_string(),
        "--namespace".to_string(),
        config.surface.namespace.clone(),
        exclusive_zone_arg(config.surface.ignore_exclusive_zones).to_string(),
    ];

    if config.surface.allow_non_wayland {
        args.push("--allow-non-wayland".to_string());
    }

    args
}

fn exclusive_zone_arg(ignore_exclusive_zones: bool) -> &'static str {
    if ignore_exclusive_zones {
        "--ignore-exclusive-zones"
    } else {
        "--respect-exclusive-zones"
    }
}

#[derive(Debug)]
pub enum CliError {
    Config(crate::config::ConfigError),
    Instance(InstanceError),
    Runtime(String),
    ExclusiveZoneConflict,
    MissingLifecycleAction,
    MultipleLifecycleActions,
    ResidentRequiresSocketPath,
}

impl Display for CliError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Config(error) => Display::fmt(error, formatter),
            Self::Instance(error) => Display::fmt(error, formatter),
            Self::Runtime(error) => formatter.write_str(error),
            Self::ExclusiveZoneConflict => formatter.write_str(
                "Use only one of --ignore-exclusive-zones or --respect-exclusive-zones.",
            ),
            Self::MissingLifecycleAction => {
                formatter.write_str("Use one of --preload, --show, --hide, --toggle, or --quit.")
            }
            Self::MultipleLifecycleActions => formatter
                .write_str("Use only one of --preload, --show, --hide, --toggle, or --quit."),
            Self::ResidentRequiresSocketPath => {
                formatter.write_str("Resident mode requires --socket-path.")
            }
        }
    }
}

impl std::error::Error for CliError {}

impl From<crate::config::ConfigError> for CliError {
    fn from(error: crate::config::ConfigError) -> Self {
        Self::Config(error)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;

    #[test]
    fn clap_definition_is_valid() {
        Cli::command().debug_assert();
    }

    #[test]
    fn missing_lifecycle_action_errors_before_runtime() {
        let cli = Cli::parse_from(["layer-shell-rs", "blur"]);

        assert_eq!(
            run(cli).unwrap_err().to_string(),
            "Use one of --preload, --show, --hide, --toggle, or --quit."
        );
    }

    #[test]
    fn multiple_lifecycle_actions_error_before_runtime() {
        let cli = Cli::parse_from(["layer-shell-rs", "blur", "--show", "--hide"]);

        assert_eq!(
            run(cli).unwrap_err().to_string(),
            "Use only one of --preload, --show, --hide, --toggle, or --quit."
        );
    }

    #[test]
    fn unknown_layer_is_rejected_by_clap() {
        assert!(Cli::try_parse_from(["layer-shell-rs", "blur", "--layer", "dock"]).is_err());
    }
}
