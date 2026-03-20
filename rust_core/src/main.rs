mod grpc_api;
mod error;
mod system_monitor;
mod process_manager;
mod window_manager;
mod keyboard_controller;
mod mouse_controller;
mod screen_capture;
mod audio_manager;
mod filesystem_manager;
mod clipboard_manager;
mod network_monitor;

use anyhow::Result;
use tokio::signal;
use tracing::{error, info};
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    info!("Запуск Rust ядра JARVIS...");

    let server = grpc_api::start_grpc_server("127.0.0.1:50051".parse()?)?;

    tokio::select! {
        res = server => {
            if let Err(e) = res {
                error!("gRPC сервер завершился с ошибкой: {e:?}");
            }
        }
        _ = signal::ctrl_c() => {
            info!("Получен сигнал завершения, останавливаемся...");
        }
    }

    Ok(())
}

