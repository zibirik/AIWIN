use crate::error::JarvisResult;

pub struct NetworkMonitor;

impl NetworkMonitor {
    pub fn new() -> Self {
        Self
    }

    pub fn is_online(&self) -> JarvisResult<bool> {
        // TODO: Реализация через WinAPI / попытку соединения
        Ok(true)
    }
}

