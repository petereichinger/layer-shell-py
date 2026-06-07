use clap::ValueEnum;
use std::fmt::{self, Display};

#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
pub enum Layer {
    Background,
    Bottom,
    Top,
    Overlay,
}

impl Layer {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Background => "background",
            Self::Bottom => "bottom",
            Self::Top => "top",
            Self::Overlay => "overlay",
        }
    }
}

impl Display for Layer {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LayerSurfaceConfig {
    pub ignore_exclusive_zones: bool,
    pub layer: Layer,
    pub namespace: String,
    pub allow_non_wayland: bool,
}

impl LayerSurfaceConfig {
    pub fn new(
        ignore_exclusive_zones: bool,
        layer: Layer,
        namespace: String,
        allow_non_wayland: bool,
    ) -> Result<Self, ConfigError> {
        if namespace.is_empty() {
            return Err(ConfigError::EmptyNamespace);
        }

        Ok(Self {
            ignore_exclusive_zones,
            layer,
            namespace,
            allow_non_wayland,
        })
    }

    pub const fn exclusive_zone(&self) -> i32 {
        if self.ignore_exclusive_zones { -1 } else { 0 }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OutlineConfig {
    pub surface: LayerSurfaceConfig,
    pub color: String,
    pub thickness: u32,
}

impl OutlineConfig {
    pub fn new(
        surface: LayerSurfaceConfig,
        color: String,
        thickness: u32,
    ) -> Result<Self, ConfigError> {
        if color.is_empty() {
            return Err(ConfigError::EmptyColor);
        }
        if thickness == 0 {
            return Err(ConfigError::NonPositiveThickness);
        }

        Ok(Self {
            surface,
            color,
            thickness,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BlurConfig {
    pub surface: LayerSurfaceConfig,
    pub color: String,
}

impl BlurConfig {
    pub fn new(surface: LayerSurfaceConfig, color: String) -> Result<Self, ConfigError> {
        if color.is_empty() {
            return Err(ConfigError::EmptyColor);
        }

        Ok(Self { surface, color })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ConfigError {
    EmptyNamespace,
    EmptyColor,
    NonPositiveThickness,
}

impl Display for ConfigError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyNamespace => formatter.write_str("Namespace may not be empty."),
            Self::EmptyColor => formatter.write_str("Color may not be empty."),
            Self::NonPositiveThickness => formatter.write_str("Thickness must be greater than 0."),
        }
    }
}

impl std::error::Error for ConfigError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exclusive_zone_defaults_to_ignored() {
        let config = LayerSurfaceConfig::new(true, Layer::Overlay, "test".into(), false).unwrap();

        assert_eq!(config.exclusive_zone(), -1);
    }

    #[test]
    fn exclusive_zone_can_be_respected() {
        let config = LayerSurfaceConfig::new(false, Layer::Overlay, "test".into(), false).unwrap();

        assert_eq!(config.exclusive_zone(), 0);
    }

    #[test]
    fn outline_rejects_zero_thickness() {
        let surface = LayerSurfaceConfig::new(true, Layer::Overlay, "test".into(), false).unwrap();

        assert_eq!(
            OutlineConfig::new(surface, "#ff0000".into(), 0).unwrap_err(),
            ConfigError::NonPositiveThickness
        );
    }

    #[test]
    fn config_rejects_empty_namespace() {
        assert_eq!(
            LayerSurfaceConfig::new(true, Layer::Overlay, String::new(), false).unwrap_err(),
            ConfigError::EmptyNamespace
        );
    }
}
