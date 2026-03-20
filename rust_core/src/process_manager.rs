use crate::error::JarvisResult;
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct ProcessInfo {
    pub pid: u32,
    pub name: String,
}

#[derive(Clone)]
pub struct ProcessManager;

impl ProcessManager {
    pub fn new() -> Self {
        Self
    }

    pub fn list_processes(&self) -> JarvisResult<Vec<ProcessInfo>> {
        // TODO: Реализация через Toolhelp32Snapshot
        Ok(Vec::new())
    }

    pub fn launch(&self, path: &str, args: &[String], working_dir: Option<&str>) -> JarvisResult<()> {
        let mut cmd = std::process::Command::new(path);
        cmd.args(args);
        if let Some(dir) = working_dir.filter(|s| !s.is_empty()) {
            cmd.current_dir(dir);
        }
        cmd.spawn()
            .map_err(|e| crate::error::JarvisError::Internal(e.to_string()))?;
        Ok(())
    }
}

