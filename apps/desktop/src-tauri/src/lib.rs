use std::net::TcpListener;
use std::sync::Mutex;

use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

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

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .expect("no free port available")
        .local_addr()
        .expect("no local address on the bound socket")
        .port()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
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

            let binary = if cfg!(windows) {
                "resources/backend/otklik-backend.exe"
            } else {
                "resources/backend/otklik-backend"
            };
            let exe = app
                .path()
                .resolve(binary, tauri::path::BaseDirectory::Resource)?;
            let (_rx, child) = app
                .shell()
                .command(exe)
                .args(["--port", &port.to_string()])
                .spawn()?;
            app.manage(BackendProcess(Mutex::new(Some(child))));
            tauri_plugin_log::log::info!("backend sidecar spawned on port {port}");
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::Destroyed) {
                if let Some(backend) = window.app_handle().try_state::<BackendProcess>() {
                    backend.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
