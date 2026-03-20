use crate::error::JarvisResult;

pub struct WindowManager;

impl WindowManager {
    pub fn new() -> Self {
        Self
    }

    pub fn focus_active_window(&self) -> JarvisResult<()> {
        // TODO: Реализация через GetForegroundWindow/SetForegroundWindow
        Ok(())
    }
}

