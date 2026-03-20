use crate::error::{JarvisError, JarvisResult};
use clipboard_win::{get_clipboard_string, set_clipboard_string};

#[derive(Clone)]
pub struct ClipboardManager;

impl ClipboardManager {
    pub fn new() -> Self {
        Self
    }

    pub fn get_text(&self) -> JarvisResult<Option<String>> {
        Ok(get_clipboard_string().ok())
    }

    pub fn set_text(&self, text: &str) -> JarvisResult<()> {
        set_clipboard_string(text).map_err(|e| JarvisError::WinApi(format!("{:?}", e)))
    }
}
