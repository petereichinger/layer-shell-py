use crate::config::{BlurConfig, Layer, LayerSurfaceConfig, OutlineConfig};
use gtk::glib;
use gtk::prelude::*;
use gtk4 as gtk;
use gtk4_layer_shell::{Edge, KeyboardMode, LayerShell};
use std::cell::Cell;
use std::env;
use std::fs;
use std::io::Read;
use std::os::unix::net::UnixListener;
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{self, Sender};
use std::thread;
use std::time::Duration;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum RuntimeCommand {
    Show,
    Hide,
    Toggle,
    Quit,
}

pub fn run_outline(
    config: &OutlineConfig,
    socket_path: &str,
    initial_visible: bool,
) -> Result<i32, String> {
    parse_color(&config.color)?;
    let config = config.clone();
    run_layer_surface(
        config.surface.clone(),
        socket_path,
        initial_visible,
        move |window| add_outline_child(window, &config),
    )
}

pub fn run_blur(
    config: &BlurConfig,
    socket_path: &str,
    initial_visible: bool,
) -> Result<i32, String> {
    parse_color(&config.color)?;
    let config = config.clone();
    run_layer_surface(
        config.surface.clone(),
        socket_path,
        initial_visible,
        move |window| add_blur_child(window, &config),
    )
}

fn run_layer_surface<F>(
    config: LayerSurfaceConfig,
    socket_path: &str,
    initial_visible: bool,
    add_child: F,
) -> Result<i32, String>
where
    F: Fn(&gtk::ApplicationWindow) -> Result<(), String> + Clone + 'static,
{
    if !config.allow_non_wayland && !is_wayland_session() {
        return Err("layer-shell-rs must run under Wayland.".to_string());
    }

    let application = gtk::Application::builder()
        .application_id("dev.peter.LayerShellRs")
        .flags(gtk::gio::ApplicationFlags::NON_UNIQUE)
        .build();
    let socket_path = PathBuf::from(socket_path);
    let server_stop = Arc::new(AtomicBool::new(false));

    application.connect_activate({
        let socket_path = socket_path.clone();
        let server_stop = Arc::clone(&server_stop);
        let config = config.clone();
        let add_child = add_child.clone();

        move |app| {
            let window = gtk::ApplicationWindow::builder()
                .application(app)
                .title(&config.namespace)
                .decorated(false)
                .build();
            let visible = Rc::new(Cell::new(initial_visible));

            disable_focus(&window);
            window.add_css_class("layer-shell-rs-outline-window");
            if let Some((width, height)) = default_monitor_size() {
                window.set_size_request(width, height);
                eprintln!(
                    "layer-shell-rs: requested layer window size {width}x{height} for namespace {}",
                    config.namespace
                );
            } else {
                eprintln!(
                    "layer-shell-rs: could not determine monitor size for namespace {}",
                    config.namespace
                );
            }
            make_transparent();

            window.init_layer_shell();
            window.set_namespace(Some(&config.namespace));
            window.set_layer(to_gtk_layer(config.layer));
            window.set_keyboard_mode(KeyboardMode::None);
            window.set_exclusive_zone(config.exclusive_zone());

            for edge in [Edge::Top, Edge::Right, Edge::Bottom, Edge::Left] {
                window.set_anchor(edge, true);
            }

            if let Err(error) = add_child(&window) {
                eprintln!("{error}");
                app.quit();
                return;
            }

            window.connect_realize(|window| {
                if let Some(surface) = window.surface() {
                    let region = gtk::cairo::Region::create();
                    surface.set_input_region(&region);
                }
            });

            let (sender, receiver) = mpsc::channel();
            start_command_server(socket_path.clone(), Arc::clone(&server_stop), sender);

            glib::timeout_add_local(Duration::from_millis(16), {
                let app = app.clone();
                let window = window.clone();
                let visible = Rc::clone(&visible);
                let server_stop = Arc::clone(&server_stop);

                move || {
                    while let Ok(command) = receiver.try_recv() {
                        match command {
                            RuntimeCommand::Show => {
                                visible.set(true);
                                window.present();
                            }
                            RuntimeCommand::Hide => {
                                visible.set(false);
                                window.set_visible(false);
                            }
                            RuntimeCommand::Toggle => {
                                if visible.get() {
                                    visible.set(false);
                                    window.set_visible(false);
                                } else {
                                    visible.set(true);
                                    window.present();
                                }
                            }
                            RuntimeCommand::Quit => {
                                server_stop.store(true, Ordering::Relaxed);
                                app.quit();
                                return glib::ControlFlow::Break;
                            }
                        }
                    }

                    glib::ControlFlow::Continue
                }
            });

            if initial_visible {
                window.present();
            } else {
                window.set_visible(false);
            }
        }
    });

    let exit_code = application.run_with_args(&["layer-shell-rs"]);
    server_stop.store(true, Ordering::Relaxed);
    let _ = fs::remove_file(socket_path);
    Ok(exit_code.get() as i32)
}

fn add_outline_child(
    window: &gtk::ApplicationWindow,
    config: &OutlineConfig,
) -> Result<(), String> {
    let color = parse_color(&config.color)?;
    let thickness_px = config.thickness;
    let drawing_area = gtk::DrawingArea::new();
    disable_focus(&drawing_area);
    drawing_area.set_content_width((thickness_px * 2) as i32);
    drawing_area.set_content_height((thickness_px * 2) as i32);
    if let Some((width, height)) = default_monitor_size() {
        drawing_area.set_size_request(width, height);
        eprintln!("layer-shell-rs: outline drawing area requested {width}x{height}");
    }
    drawing_area.set_hexpand(true);
    drawing_area.set_vexpand(true);
    drawing_area.set_draw_func(move |_area, context, width, height| {
        context.set_source_rgba(
            color.red() as f64,
            color.green() as f64,
            color.blue() as f64,
            color.alpha() as f64,
        );
        let thickness = thickness_px as f64;
        let width = width as f64;
        let height = height as f64;
        context.rectangle(0.0, 0.0, width, thickness);
        context.rectangle(0.0, (height - thickness).max(0.0), width, thickness);
        context.rectangle(0.0, 0.0, thickness, height);
        context.rectangle((width - thickness).max(0.0), 0.0, thickness, height);
        let _ = context.fill();
    });
    window.set_child(Some(&drawing_area));
    Ok(())
}

fn add_blur_child(window: &gtk::ApplicationWindow, config: &BlurConfig) -> Result<(), String> {
    let color = parse_color(&config.color)?;
    let drawing_area = gtk::DrawingArea::new();
    disable_focus(&drawing_area);
    if let Some((width, height)) = default_monitor_size() {
        drawing_area.set_size_request(width, height);
        eprintln!("layer-shell-rs: blur drawing area requested {width}x{height}");
    }
    drawing_area.set_hexpand(true);
    drawing_area.set_vexpand(true);
    drawing_area.set_draw_func(move |_area, context, width, height| {
        context.set_source_rgba(
            color.red() as f64,
            color.green() as f64,
            color.blue() as f64,
            color.alpha() as f64,
        );
        context.rectangle(0.0, 0.0, width as f64, height as f64);
        let _ = context.fill();
    });
    window.set_child(Some(&drawing_area));
    Ok(())
}

fn is_wayland_session() -> bool {
    env::var("XDG_SESSION_TYPE").is_ok_and(|session_type| session_type == "wayland")
        || env::var_os("WAYLAND_DISPLAY").is_some()
}

fn to_gtk_layer(layer: Layer) -> gtk4_layer_shell::Layer {
    match layer {
        Layer::Background => gtk4_layer_shell::Layer::Background,
        Layer::Bottom => gtk4_layer_shell::Layer::Bottom,
        Layer::Top => gtk4_layer_shell::Layer::Top,
        Layer::Overlay => gtk4_layer_shell::Layer::Overlay,
    }
}

fn disable_focus(widget: &impl IsA<gtk::Widget>) {
    widget.set_can_focus(false);
    widget.set_focusable(false);
}

fn default_monitor_size() -> Option<(i32, i32)> {
    let display = gtk::gdk::Display::default()?;
    let monitors = display.monitors();
    let monitor = monitors.item(0)?.downcast::<gtk::gdk::Monitor>().ok()?;
    let geometry = monitor.geometry();
    Some((geometry.width(), geometry.height()))
}

fn make_transparent() {
    let Some(display) = gtk::gdk::Display::default() else {
        return;
    };

    let provider = gtk::CssProvider::new();
    provider.load_from_string(
        "window.layer-shell-rs-outline-window { background-color: transparent; }",
    );
    gtk::style_context_add_provider_for_display(
        &display,
        &provider,
        gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
    );
}

fn parse_color(color: &str) -> Result<gtk::gdk::RGBA, String> {
    gtk::gdk::RGBA::parse(color).map_err(|_| format!("Invalid color: {color}"))
}

fn start_command_server(path: PathBuf, stop: Arc<AtomicBool>, sender: Sender<RuntimeCommand>) {
    thread::spawn(move || serve_commands(&path, &stop, sender));
}

fn serve_commands(path: &Path, stop: &AtomicBool, sender: Sender<RuntimeCommand>) {
    if let Some(parent) = path.parent()
        && let Err(error) = fs::create_dir_all(parent)
    {
        eprintln!(
            "Could not create runtime directory {}: {error}",
            parent.display()
        );
        return;
    }
    let _ = fs::remove_file(path);

    let listener = match UnixListener::bind(path) {
        Ok(listener) => listener,
        Err(error) => {
            eprintln!("Could not bind command socket {}: {error}", path.display());
            return;
        }
    };
    if let Err(error) = listener.set_nonblocking(true) {
        eprintln!(
            "Could not configure command socket {}: {error}",
            path.display()
        );
        return;
    }

    while !stop.load(Ordering::Relaxed) {
        match listener.accept() {
            Ok((mut connection, _addr)) => {
                let mut buffer = String::new();
                let _ = connection.by_ref().take(128).read_to_string(&mut buffer);
                if let Some(command) = parse_command(buffer.trim()) {
                    let _ = sender.send(command);
                }
            }
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                thread::sleep(Duration::from_millis(50));
            }
            Err(_) => return,
        }
    }
}

fn parse_command(command: &str) -> Option<RuntimeCommand> {
    match command {
        "show" => Some(RuntimeCommand::Show),
        "hide" => Some(RuntimeCommand::Hide),
        "toggle" => Some(RuntimeCommand::Toggle),
        "quit" => Some(RuntimeCommand::Quit),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn command_parser_accepts_known_commands() {
        assert_eq!(parse_command("show"), Some(RuntimeCommand::Show));
        assert_eq!(parse_command("quit"), Some(RuntimeCommand::Quit));
    }

    #[test]
    fn command_parser_rejects_unknown_commands() {
        assert_eq!(parse_command("noop"), None);
    }
}
