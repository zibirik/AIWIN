use crate::error::JarvisResult;
use std::path::Path;

pub struct FilesystemManager;

impl FilesystemManager {
    pub fn new() -> Self {
        Self
    }

    pub fn write_file(&self, path: &str, content: &[u8]) -> JarvisResult<()> {
        let p = Path::new(path);
        if let Some(parent) = p.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(p, content)?;
        Ok(())
    }
}

