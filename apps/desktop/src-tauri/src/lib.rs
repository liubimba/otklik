use std::net::TcpListener;
use std::sync::Mutex;

use tauri::{Emitter, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_EXIT_EVENT: &str = "backend://exited";
const BACKEND_STDERR_CAP: usize = 4000;

#[derive(Clone, serde::Serialize)]
struct BackendExit {
    code: Option<i32>,
    stderr: String,
}

fn tail_on_char_boundary(text: &str, max: usize) -> String {
    if text.len() <= max {
        return text.to_string();
    }
    let mut start = text.len() - max;
    while start < text.len() && !text.is_char_boundary(start) {
        start += 1;
    }
    text[start..].to_string()
}

struct BackendPort(u16);

struct BackendProcess(Mutex<Option<CommandChild>>);

impl BackendProcess {
    fn kill(&self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
}

#[tauri::command]
fn get_backend_port(port: tauri::State<BackendPort>) -> u16 {
    port.0
}

#[tauri::command]
fn shutdown_backend(backend: tauri::State<BackendProcess>) {
    backend.kill();
}

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .expect("no free port available")
        .local_addr()
        .expect("no local address on the bound socket")
        .port()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    #[cfg(target_os = "linux")]
    std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
    tauri::Builder::default()
        .plugin(
            tauri_plugin_log::Builder::new()
                .level(tauri_plugin_log::log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            let port = free_port();
            app.manage(BackendPort(port));

            let (mut rx, child) = if tauri::is_dev() {
                let backend_dir = concat!(env!("CARGO_MANIFEST_DIR"), "/../../../services/backend");
                let backend_bin = if cfg!(windows) {
                    format!("{backend_dir}/.venv/Scripts/otklik-backend.exe")
                } else {
                    format!("{backend_dir}/.venv/bin/otklik-backend")
                };
                app.shell()
                    .command(backend_bin)
                    .args(["--port", &port.to_string()])
                    .current_dir(backend_dir)
                    .spawn()?
            } else {
                let binary = if cfg!(windows) {
                    "resources/backend/otklik-backend.exe"
                } else {
                    "resources/backend/otklik-backend"
                };
                let exe = app
                    .path()
                    .resolve(binary, tauri::path::BaseDirectory::Resource)?;
                app.shell()
                    .command(exe)
                    .args(["--port", &port.to_string()])
                    .spawn()?
            };
            app.manage(BackendProcess(Mutex::new(Some(child))));
            tauri_plugin_log::log::info!("backend spawned on port {port}");

            let exit_emitter = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let mut stderr = String::new();
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stderr(bytes) => {
                            stderr.push_str(&String::from_utf8_lossy(&bytes));
                            stderr = tail_on_char_boundary(&stderr, BACKEND_STDERR_CAP);
                        }
                        CommandEvent::Error(err) => {
                            stderr.push_str(&err);
                            stderr = tail_on_char_boundary(&stderr, BACKEND_STDERR_CAP);
                        }
                        CommandEvent::Terminated(payload) => {
                            tauri_plugin_log::log::error!(
                                "backend exited (code={:?})",
                                payload.code
                            );
                            let _ = exit_emitter.emit(
                                BACKEND_EXIT_EVENT,
                                BackendExit {
                                    code: payload.code,
                                    stderr: stderr.trim().to_string(),
                                },
                            );
                            break;
                        }
                        _ => {}
                    }
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::Destroyed) {
                if let Some(backend) = window.app_handle().try_state::<BackendProcess>() {
                    backend.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![get_backend_port, shutdown_backend])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
