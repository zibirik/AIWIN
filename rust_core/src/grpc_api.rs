use anyhow::Result;
use tonic::transport::Server;
use tonic::{Request, Response, Status};
use tracing::info;

pub mod proto {
    tonic::include_proto!("jarvis.system.v1");
}

use proto::system_control_service_server::{SystemControlService, SystemControlServiceServer};
use proto::{
    CaptureScreenRequest, CaptureScreenResponse, ClickMouseRequest, CommandResult,
    GetSystemStatusRequest, LaunchApplicationRequest, MoveMouseRequest, ReadClipboardRequest,
    ReadClipboardResponse, SetClipboardRequest, SimulateKeyRequest, SystemStatus,
};

use crate::clipboard_manager::ClipboardManager;
use crate::keyboard_controller::KeyboardController;
use crate::mouse_controller::MouseController;
use crate::process_manager::ProcessManager;
use crate::screen_capture::ScreenCapture;
use crate::system_monitor::SystemMonitor;

#[derive(Clone)]
struct SystemControlServiceImpl {
    system_monitor: SystemMonitor,
    screen_capture: ScreenCapture,
    process_manager: ProcessManager,
    keyboard: KeyboardController,
    mouse: MouseController,
    clipboard: ClipboardManager,
}

#[tonic::async_trait]
impl SystemControlService for SystemControlServiceImpl {
    async fn get_system_status(
        &self,
        _request: Request<GetSystemStatusRequest>,
    ) -> Result<Response<SystemStatus>, Status> {
        let metrics = self
            .system_monitor
            .get_metrics()
            .map_err(|e| Status::internal(format!("system metrics error: {e}")))?;
        let status = SystemStatus {
            cpu_usage: metrics.cpu_usage,
            memory_usage: metrics.memory_usage,
            battery_level: metrics.battery_level,
        };
        Ok(Response::new(status))
    }

    async fn launch_application(
        &self,
        request: Request<LaunchApplicationRequest>,
    ) -> Result<Response<CommandResult>, Status> {
        let inner = request.into_inner();
        let path = inner.path;
        let args = inner.args;
        let working_dir = if inner.working_dir.is_empty() { None } else { Some(inner.working_dir.as_str()) };

        let res = self.process_manager.launch(&path, &args, working_dir);
        match res {
            Ok(()) => Ok(Response::new(CommandResult {
                success: true,
                error_message: String::new(),
            })),
            Err(e) => Ok(Response::new(CommandResult {
                success: false,
                error_message: e.to_string(),
            })),
        }
    }

    async fn capture_screen(
        &self,
        _request: Request<CaptureScreenRequest>,
    ) -> Result<Response<CaptureScreenResponse>, Status> {
        let img = self
            .screen_capture
            .capture_fullscreen_png()
            .map_err(|e| Status::internal(format!("screen capture error: {e}")))?;
        let resp = CaptureScreenResponse { image_png: img };
        Ok(Response::new(resp))
    }

    async fn simulate_key(
        &self,
        request: Request<SimulateKeyRequest>,
    ) -> Result<Response<CommandResult>, Status> {
        let text = request.into_inner().text;
        match self.keyboard.send_text(&text) {
            Ok(()) => Ok(Response::new(CommandResult { success: true, error_message: String::new() })),
            Err(e) => Ok(Response::new(CommandResult { success: false, error_message: e.to_string() })),
        }
    }

    async fn move_mouse(
        &self,
        request: Request<MoveMouseRequest>,
    ) -> Result<Response<CommandResult>, Status> {
        let inner = request.into_inner();
        match self.mouse.move_to(inner.x, inner.y) {
            Ok(()) => Ok(Response::new(CommandResult { success: true, error_message: String::new() })),
            Err(e) => Ok(Response::new(CommandResult { success: false, error_message: e.to_string() })),
        }
    }

    async fn click_mouse(
        &self,
        request: Request<ClickMouseRequest>,
    ) -> Result<Response<CommandResult>, Status> {
        let inner = request.into_inner();
        let res = if inner.x != 0 || inner.y != 0 {
            self.mouse.move_to(inner.x, inner.y).and_then(|_| self.mouse.left_click())
        } else {
            self.mouse.left_click()
        };
        match res {
            Ok(()) => Ok(Response::new(CommandResult { success: true, error_message: String::new() })),
            Err(e) => Ok(Response::new(CommandResult { success: false, error_message: e.to_string() })),
        }
    }

    async fn read_clipboard(
        &self,
        _request: Request<ReadClipboardRequest>,
    ) -> Result<Response<ReadClipboardResponse>, Status> {
        match self.clipboard.get_text() {
            Ok(Some(t)) => Ok(Response::new(ReadClipboardResponse { text: t })),
            Ok(None) => Ok(Response::new(ReadClipboardResponse { text: String::new() })),
            Err(e) => Err(Status::internal(e.to_string())),
        }
    }

    async fn set_clipboard(
        &self,
        request: Request<SetClipboardRequest>,
    ) -> Result<Response<CommandResult>, Status> {
        let text = request.into_inner().text;
        match self.clipboard.set_text(&text) {
            Ok(()) => Ok(Response::new(CommandResult { success: true, error_message: String::new() })),
            Err(e) => Ok(Response::new(CommandResult { success: false, error_message: e.to_string() })),
        }
    }
}

pub fn start_grpc_server(addr: std::net::SocketAddr) -> Result<impl std::future::Future<Output = Result<(), tonic::transport::Error>>> {
    let svc = SystemControlServiceImpl {
        system_monitor: SystemMonitor::new(),
        screen_capture: ScreenCapture::new(),
        process_manager: ProcessManager::new(),
        keyboard: KeyboardController::new(),
        mouse: MouseController::new(),
        clipboard: ClipboardManager::new(),
    };
    info!("gRPC сервер JARVIS слушает на {}", addr);

    Ok(Server::builder().add_service(SystemControlServiceServer::new(svc)).serve(addr))
}

