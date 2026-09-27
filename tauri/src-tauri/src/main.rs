#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::sync::Arc;
use std::time::Duration;
use tauri::{Emitter, Manager, WebviewWindowBuilder, WindowEvent, menu::{Menu, MenuItem}};
use tauri::tray::{TrayIconBuilder, TrayIconEvent};

mod bridge;
use bridge::{BridgeManager, BridgeStatus};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let bridge = Arc::new(BridgeManager::new());

    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .manage(Arc::new(BridgeManager::new()))
        .setup(move |app| {
            let bridge = app.state::<Arc<BridgeManager>>().inner().clone();
            let app_handle = app.handle().clone();

            // Start Python bridge
            let bridge_clone = bridge.clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = bridge_clone.start().await {
                    eprintln!("Failed to start bridge: {}", e);
                }
            });

            // Create main chat window (hidden initially)
            let main_window = WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::App("ashu_prototype.html".into()),
            )
            .title("Ashu")
            .inner_size(420.0, 680.0)
            .min_inner_size(360.0, 600.0)
            .resizable(true)
            .decorations(false)
            .transparent(true)
            .visible(false)
            .center()
            .always_on_top(true)
            .skip_taskbar(true)
            .build()?;

            // Create persistent floating companion window (always visible on desktop)
            let companion_window = WebviewWindowBuilder::new(
                app,
                "companion",
                tauri::WebviewUrl::App("ashu_companion.html".into()),
            )
            .title("Ashu Companion")
            .inner_size(140.0, 140.0)
            .min_inner_size(100.0, 100.0)
            .max_inner_size(200.0, 200.0)
            .resizable(true)
            .decorations(false)
            .transparent(true)
            .visible(true)
            .center()
            .always_on_top(true)
            .skip_taskbar(true)
            .focused(false)
            .build()?;

            // System tray
            let quit_item = MenuItem::new(app, "Quit", true, None::<&str>)?;
            let show_item = MenuItem::new(app, "Show Chat", true, None::<&str>)?;
            let hide_companion_item = MenuItem::new(app, "Hide Companion", true, None::<&str>)?;
            let show_companion_item = MenuItem::new(app, "Show Companion", true, None::<&str>)?;
            let status_item = MenuItem::new(app, "Bridge Status", true, None::<&str>)?;
            let menu = Menu::new(app)?;

            let tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&Menu::new(app)?)
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click { .. } = event {
                        if let Some(window) = tray.app_handle().get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            // Tray event handler for menu items
            let app_handle = app.handle().clone();
            let main_window_clone = main_window.clone();
            let companion_window_clone = companion_window.clone();
            
            app.on_menu_event(move |app, event| {
                match event.id().0.as_str() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "hide_companion" => {
                        if let Some(window) = app.get_webview_window("companion") {
                            let _ = window.hide();
                        }
                    }
                    "show_companion" => {
                        if let Some(window) = app.get_webview_window("companion") {
                            let _ = window.show();
                        }
                    }
                    "status" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.emit("request-bridge-status", ());
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                }
            });

            // Also handle tray click to show main window
            app.on_tray_icon_event(move |_tray, event| {
                if let tauri::tray::TrayIconEvent::Click { .. } = event {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
            });

            // Window event: hide instead of close for main window
            let main_window_clone = main_window.clone();
            main_window.on_window_event(move |event| {
                if let WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let _ = main_window_clone.hide();
                }
            });

            // Companion window: hide instead of close
            let companion_window_clone = companion_window.clone();
            companion_window.on_window_event(move |event| {
                if let WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let _ = companion_window_clone.hide();
                }
            });

            // Auto-show on startup
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(Duration::from_millis(500)).await;
                let _ = main_window.show();
                let _ = companion_window.show();
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            crate::bridge::get_bridge_status,
            crate::bridge::restart_bridge,
            crate::bridge::set_bridge_url,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn main() {
    run();
}